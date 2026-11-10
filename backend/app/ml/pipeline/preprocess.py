"""CRISP-DM 'Data Preparation' step.

Reads the real raw data written by app/ml/ingestion/{iotc,noaa}.py, cleans it, merges
catch data with environmental data on (region, month), handles missing values, and
writes data/processed/monthly_features.csv -- the single table the training scripts
consume.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from app.core.config import DATA_PROCESSED_DIR, DATA_RAW_DIR

logger = logging.getLogger(__name__)

# The forecasting target is scoped to the Maldives' two main commercial tuna species
# (pole-and-line/handline skipjack and yellowfin are what the fishery -- and this
# dashboard -- is actually built around). Every other species reported in the raw IOTC
# file (bycatch, bigeye, kawakawa, frigate tuna, billfish, sharks, etc.) is excluded
# from the processed table, the DB, and the trained models.
TARGET_SPECIES = ["Skipjack tuna", "Yellowfin tuna"]


def _load_catch() -> pd.DataFrame:
    path = DATA_RAW_DIR / "iotc_maldives_catch.csv"
    df = pd.read_csv(path)

    # Only keep rows reported in metric tons (MT). A minority of rows are reported as a
    # count of individual fish ("NO", mostly incidental billfish bycatch) which cannot
    # be summed together with a weight -- mixing the two units would silently corrupt
    # the catch volume, so they are excluded from the weight-based series.
    before = len(df)
    df = df[df["CATCH_UNIT_CODE"] == "MT"].copy()
    logger.info("Kept %s/%s catch rows reported in metric tons (MT)", len(df), before)

    df = df.dropna(subset=["region", "CATCH"])
    df["catch_month"] = pd.to_datetime(
        dict(year=df["YEAR"], month=df["MONTH_START"], day=1), errors="coerce"
    )
    df = df.dropna(subset=["catch_month"])
    df["catch_kg"] = df["CATCH"] * 1000.0  # metric tons -> kg

    monthly = (
        df.groupby(["region", "SPECIES", "catch_month"], as_index=False)["catch_kg"].sum()
    )
    monthly = monthly.rename(columns={"SPECIES": "species"})
    return monthly


def _select_target_species(monthly_catch: pd.DataFrame) -> list[str]:
    present = set(monthly_catch["species"])
    missing = [s for s in TARGET_SPECIES if s not in present]
    if missing:
        logger.warning("Target species missing from raw catch data: %s", missing)
    selected = [s for s in TARGET_SPECIES if s in present]
    logger.info("Target species: %s", selected)
    return selected


def _load_environmental() -> pd.DataFrame:
    path = DATA_RAW_DIR / "noaa_environmental.csv"
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df["obs_month"] = df["timestamp"].dt.to_period("M").dt.to_timestamp()
    monthly = (
        df.groupby(["region", "obs_month", "variable"], as_index=False)["value"].mean()
    )
    wide = monthly.pivot_table(
        index=["region", "obs_month"], columns="variable", values="value"
    ).reset_index()
    wide.columns.name = None
    return wide


def _ffill_trailing_gap(series: pd.Series) -> pd.Series:
    """Carries the last real observation forward through a *trailing* gap only -- i.e.
    the stretch after a variable's real-world coverage ends (e.g. the wind speed
    dataset's coverage stops partway through the series, see docs/DATA_SOURCES.md).
    Without this, every model anchors its forecast to the last month with real data for
    its *least*-covered input, which can be a year or more behind the most recent real
    catch record, making "N months ahead" land on a stale historical date instead of
    close to today.

    This never backfills, and never touches a gap that isn't trailing (an interior gap,
    or a variable with no real coverage before some start date, is left exactly as
    `interpolate()` above leaves it -- real NaN, not fabricated)."""
    last_valid = series.last_valid_index()
    if last_valid is None:
        return series
    filled = series.copy()
    filled.loc[filled.index > last_valid] = filled.loc[last_valid]
    return filled


def _fill_env_gaps(env: pd.DataFrame) -> pd.DataFrame:
    """Interpolate short interior gaps per region/variable, then carry the last real
    value forward through any trailing gap. A dataset with no real coverage before some
    start date (e.g. salinity, which only starts in 2010) simply has no rows before
    that -- those stay NaN, handled explicitly by the training scripts, not invented."""
    filled_parts = []
    for region, grp in env.groupby("region"):
        grp = grp.sort_values("obs_month").set_index("obs_month")
        for col in ["sst", "wind_speed", "salinity"]:
            if col in grp.columns:
                grp[col] = grp[col].interpolate(method="linear", limit=2)
                grp[col] = _ffill_trailing_gap(grp[col])
        grp["region"] = region
        filled_parts.append(grp.reset_index())
    return pd.concat(filled_parts, ignore_index=True)


def build_monthly_features() -> pd.DataFrame:
    catch = _load_catch()
    target_species = _select_target_species(catch)
    catch = catch[catch["species"].isin(target_species)]

    env = _load_environmental()
    env = _fill_env_gaps(env)

    merged = catch.merge(
        env, left_on=["region", "catch_month"], right_on=["region", "obs_month"], how="left"
    )
    merged = merged.drop(columns=["obs_month"])
    merged = merged.rename(columns={"catch_month": "month"})
    merged = merged.sort_values(["species", "region", "month"])

    DATA_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_PROCESSED_DIR / "monthly_features.csv"
    merged.to_csv(out_path, index=False)
    logger.info("Wrote %s rows to %s", len(merged), out_path)
    return merged


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    df = build_monthly_features()
    print(df.head(10))
    print("\nRows per species:")
    print(df.groupby("species").size())
    print("\nNull counts:")
    print(df[["sst", "wind_speed", "salinity", "catch_kg"]].isna().sum())
    print("\nMonth range:", df["month"].min(), "-", df["month"].max())
