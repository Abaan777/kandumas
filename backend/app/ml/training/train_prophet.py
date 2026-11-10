"""CRISP-DM 'Modeling' step -- Prophet.

Trains one Prophet model per (region, species) combination -- this is what serves
region-level forecasts (UC4: filter by region/species/time). Prophet is used here, as
the literature review describes, as the secondary model that validates seasonal trends;
its per-series fitting cost is low enough to run one model per region, unlike the LSTM.

Regressors: sst and wind_speed (available from 1993) are used for every combo. Salinity
only exists from 2010 onward (see docs/DATA_SOURCES.md); rather than truncating every
region+species series down to 2010+, salinity is added as a regressor only when the
combo's own data already starts at/after 2010, and is otherwise left out -- documented,
not silently interpolated across a 17-year gap.

Target transform: catch_kg spans orders of magnitude for the low-volume species (many
near-zero months, occasional large spikes), and fitting Prophet directly on that scale
left those species' RMSE many times larger than their region's typical catch. Fitting
on log1p(catch_kg) instead fixes that -- but it isn't a universal improvement: for at
least one large-volume series (North Maldives/Skipjack) the raw-scale fit was
substantially better, most likely because that series is already fairly smooth and
log-space training added noise sensitivity instead of removing it. So both a raw-scale
and a log1p-scale model are fit for every (region, species), evaluated on the same held-
out months, and whichever has the lower test RMSE is kept -- the same "best result wins"
principle already used to choose between LSTM and Prophet in evaluate.py. Which
transform won is recorded in the metrics (`target_transform`) so prediction_service.py
knows how to invert it when serving live forecasts.
"""
from __future__ import annotations

import json
import logging

import numpy as np
import pandas as pd

from app.core.config import DATA_PROCESSED_DIR, ML_ARTIFACTS_DIR
from app.ml.training.common import mape, rmse

logger = logging.getLogger(__name__)

MIN_ROWS = 30
TEST_FRACTION = 0.2
SALINITY_COVERAGE_START = pd.Timestamp("2010-06-01")


def _expm1_capped(log_values: np.ndarray, cap_kg: float) -> np.ndarray:
    """expm1 back to real kg, capped at a generous multiple of the observed training
    max. Necessary because Prophet's linear regressor terms can extrapolate slightly
    out of the training range on a held-out point, and exponentiating even a modest
    log-space overshoot explodes exponentially -- observed once on a 40-month sample
    (North Maldives/Bigeye tuna), where it turned a single test month's miss into a
    765-billion-kg RMSE. The cap keeps that failure mode from corrupting RMSE/MAPE
    while leaving legitimate forecasts (which never approach 5x the historical max)
    completely unaffected."""
    return np.clip(np.expm1(log_values), 0, cap_kg)


def _fit_and_eval(train_df: pd.DataFrame, test_df: pd.DataFrame, regressors: list[str], use_log: bool):
    from prophet import Prophet

    fit_df = train_df.copy()
    if use_log:
        fit_df["y"] = np.log1p(fit_df["y"])

    model = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    for reg in regressors:
        model.add_regressor(reg)
    model.fit(fit_df[["ds", "y", *regressors]])

    forecast = model.predict(test_df[["ds", *regressors]])
    y_true = test_df["y"].to_numpy()
    if use_log:
        cap_kg = train_df["y"].max() * 5
        y_pred = _expm1_capped(forecast["yhat"].to_numpy(), cap_kg)
    else:
        y_pred = forecast["yhat"].clip(lower=0).to_numpy()

    return model, rmse(y_true, y_pred), mape(y_true, y_pred)


def train_one(region: str, species: str, df: pd.DataFrame) -> dict | None:
    sub = df[(df["region"] == region) & (df["species"] == species)].sort_values("month")
    sub = sub.dropna(subset=["catch_kg", "sst", "wind_speed"])
    if len(sub) < MIN_ROWS:
        logger.warning("%s / %s: only %s rows, skipping Prophet", region, species, len(sub))
        return None

    use_salinity = sub["month"].min() >= SALINITY_COVERAGE_START and sub["salinity"].notna().all()
    regressors = ["sst", "wind_speed"] + (["salinity"] if use_salinity else [])

    prophet_df = sub.rename(columns={"month": "ds", "catch_kg": "y"})[["ds", "y", *regressors]]

    split = int(len(prophet_df) * (1 - TEST_FRACTION))
    split = max(split, 12)
    train_df, test_df = prophet_df.iloc[:split], prophet_df.iloc[split:]
    if len(test_df) == 0:
        return None

    raw_model, raw_rmse, raw_mape = _fit_and_eval(train_df, test_df, regressors, use_log=False)
    log_model, log_rmse, log_mape = _fit_and_eval(train_df, test_df, regressors, use_log=True)

    if log_rmse < raw_rmse:
        model, target_transform, model_rmse, model_mape = log_model, "log1p", log_rmse, log_mape
    else:
        model, target_transform, model_rmse, model_mape = raw_model, "none", raw_rmse, raw_mape

    metrics = {
        "region": region,
        "species": species,
        "model_name": "prophet",
        "regressors": regressors,
        "target_transform": target_transform,
        "n_train": int(len(train_df)),
        "n_test": int(len(test_df)),
        "rmse": model_rmse,
        "mape": model_mape,
        "mean_actual_catch": float(test_df["y"].mean()),
        "train_start": str(train_df["ds"].iloc[0].date()),
        "train_end": str(train_df["ds"].iloc[-1].date()),
    }

    safe_region = region.replace(" ", "_").replace("(", "").replace(")", "").lower()
    safe_species = species.replace(" ", "_").replace("/", "_").lower()
    ML_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ML_ARTIFACTS_DIR / f"prophet_{safe_region}_{safe_species}.json", "w") as f:
        from prophet.serialize import model_to_json

        f.write(model_to_json(model))

    logger.info(
        "%s / %s: Prophet(%s) RMSE=%.1f MAPE=%.1f%% (n_test=%s, regressors=%s; raw RMSE=%.1f, log1p RMSE=%.1f)",
        region,
        species,
        target_transform,
        metrics["rmse"],
        metrics["mape"],
        len(test_df),
        regressors,
        raw_rmse,
        log_rmse,
    )
    return metrics


def train_all() -> list[dict]:
    df = pd.read_csv(DATA_PROCESSED_DIR / "monthly_features.csv", parse_dates=["month"])
    results = []
    for region in sorted(df["region"].unique()):
        for species in sorted(df["species"].unique()):
            result = train_one(region, species, df)
            if result:
                results.append(result)

    ML_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ML_ARTIFACTS_DIR / "prophet_metrics.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    results = train_all()
    for r in results:
        print(r)
