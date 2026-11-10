"""Weather-weighted daily catch estimate for a single user-chosen date, capped at 7
days ahead of today (inclusive).

This is explicitly NOT a separately trained or validated daily model. None of this
project's data sources (FAO/IOTC/NOAA) report catch at finer than monthly resolution
(IOTC's own data is monthly -- see docs/DATA_SOURCES.md), so there is no historical
"day X had Y kg" record anywhere to train or check a true daily model against. The 7-day
cap exists because that's roughly the edge of where a live weather forecast (the one
real, validated input this estimate adds beyond the historical baseline) is still
meaningfully accurate -- beyond that it degrades toward climatology anyway.

What this does instead, using only real data:
  1. A real historical seasonal baseline: the region+species' average catch for this
     calendar month across every historical year on record, turned into a daily rate.
  2. A real live weather forecast for the requested date (weather_forecast.py,
     Open-Meteo).
  3. The region+species' own trained Prophet model, asked (with the calendar date held
     fixed so trend/seasonality cancel out) how much more or less catch it predicts for
     that date's *actual* live weather versus this month's *usual* weather -- i.e. the
     model's own learned sensitivity to sst/wind_speed becomes a real, model-grounded
     favorability multiplier rather than an invented formula.

The result is presented as an estimate derived from real data, not as an independently
validated prediction, because -- again -- it cannot be validated without daily ground
truth. Both the API response and the UI say so explicitly.
"""
from __future__ import annotations

import logging
from datetime import date as date_type
from datetime import timedelta

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import DATA_PROCESSED_DIR, ML_ARTIFACTS_DIR
from app.ml.ingestion.weather_forecast import fetch_weather_forecast
from app.models.models import ModelRun, Region, Species
from app.services.prediction_service import PredictionUnavailable, _safe

logger = logging.getLogger(__name__)

FAVORABILITY_BOUNDS = (0.5, 2.0)  # a single day's weather can't swing the estimate more than 2x either way
MAX_DAYS_AHEAD = 7  # today (day 0) through 6 days ahead -- see module docstring


def _climatological_baseline(df: pd.DataFrame, region: str, species: str, month_num: int) -> dict | None:
    sub = df[(df["region"] == region) & (df["species"] == species) & (df["month"].dt.month == month_num)]
    if sub.empty:
        return None
    return {
        "mean_monthly_catch_kg": float(sub["catch_kg"].mean()),
        "mean_sst": float(sub["sst"].mean()) if sub["sst"].notna().any() else None,
        "mean_wind_speed": float(sub["wind_speed"].mean()) if sub["wind_speed"].notna().any() else None,
    }


def _prophet_target_transform(db: Session, region: str, species: str) -> str:
    species_row = db.query(Species).filter_by(name=species).first()
    if species_row is None:
        return "none"
    run = (
        db.query(ModelRun)
        .filter_by(model_name="prophet", species_id=species_row.id)
        .order_by(ModelRun.trained_at.desc())
        .all()
    )
    for r in run:
        if (r.params_json or {}).get("region") == region:
            return (r.params_json or {}).get("target_transform", "none")
    return "none"


def _favorability_ratio(
    region: str,
    species: str,
    target_transform: str,
    live_sst: float | None,
    live_wind: float | None,
    baseline_sst: float | None,
    baseline_wind: float | None,
) -> float | None:
    path = ML_ARTIFACTS_DIR / f"prophet_{_safe(region)}_{_safe(species)}.json"
    if not path.exists() or None in (live_sst, live_wind, baseline_sst, baseline_wind):
        return None

    from prophet.serialize import model_from_json

    with open(path) as f:
        model = model_from_json(f.read())

    # Anchor the comparison at the model's OWN most recent training date, not today's
    # real calendar date. Prophet's trend component is only reliable within (or just
    # past) the range it was fit on; this model's training data can end years before
    # today (see docs/DATA_SOURCES.md on environmental-data lag), and evaluating trend
    # that far past the end of training extrapolates into nonsense (observed: a
    # strongly *negative* predicted catch). Since only the *ratio* between the two
    # predictions is used, and both share this same anchor date, trend/seasonality
    # still cancel out correctly -- the anchor just needs to be a date the model's fit
    # is actually well-behaved at, which "most recent trained date" guarantees.
    anchor = model.history["ds"].max()
    rows = {
        "ds": [anchor, anchor],
        "sst": [live_sst, baseline_sst],
        "wind_speed": [live_wind, baseline_wind],
    }
    if "salinity" in model.extra_regressors:
        # No live salinity *forecast* source exists (see weather_forecast.py) -- hold
        # it at an identical, arbitrary value for both rows so its regressor term is
        # identical in both predictions and cancels out of the ratio exactly.
        rows["salinity"] = [0.0, 0.0]

    forecast = model.predict(pd.DataFrame(rows))
    live_yhat, baseline_yhat = forecast["yhat"].iloc[0], forecast["yhat"].iloc[1]

    if target_transform == "log1p":
        import numpy as np

        live_val, baseline_val = float(np.expm1(live_yhat)), float(np.expm1(baseline_yhat))
    else:
        live_val, baseline_val = float(live_yhat), float(baseline_yhat)

    if baseline_val <= 0:
        return None
    ratio = live_val / baseline_val
    return max(FAVORABILITY_BOUNDS[0], min(FAVORABILITY_BOUNDS[1], ratio))


def get_daily_estimate(db: Session, region: str, species: str, target_date: date_type | None = None) -> dict:
    region_row = db.query(Region).filter_by(name=region).first()
    if region_row is None:
        raise PredictionUnavailable(f"Unknown region '{region}'")

    df = pd.read_csv(DATA_PROCESSED_DIR / "monthly_features.csv", parse_dates=["month"])
    if not ((df["region"] == region) & (df["species"] == species)).any():
        raise PredictionUnavailable(f"No historical data for region='{region}' species='{species}'")

    today = date_type.today()
    max_date = today + timedelta(days=MAX_DAYS_AHEAD - 1)
    if target_date is None:
        target_date = today
    if target_date < today or target_date > max_date:
        raise ValueError(
            f"Date must be between {today.isoformat()} and {max_date.isoformat()} "
            f"(today through {MAX_DAYS_AHEAD - 1} days ahead)."
        )

    weather_days = fetch_weather_forecast(region_row.lat_center, region_row.lon_center, days=MAX_DAYS_AHEAD)
    w = next((d for d in weather_days if d["date"] == target_date.isoformat()), None)
    if w is None:
        raise PredictionUnavailable(f"No weather forecast available yet for {target_date.isoformat()}.")

    target_transform = _prophet_target_transform(db, region, species)
    baseline = _climatological_baseline(df, region, species, target_date.month)

    if baseline is None:
        day = {**w, "estimated_catch_kg": None, "favorability_ratio": None, "note": "no historical data for this calendar month"}
    else:
        days_in_month = pd.Period(target_date, freq="M").days_in_month
        daily_baseline_kg = baseline["mean_monthly_catch_kg"] / days_in_month

        ratio = _favorability_ratio(
            region,
            species,
            target_transform,
            w["sst"],
            w["wind_speed"],
            baseline["mean_sst"],
            baseline["mean_wind_speed"],
        )
        effective_ratio = ratio if ratio is not None else 1.0

        day = {
            "date": w["date"],
            "sst": w["sst"],
            "wind_speed": w["wind_speed"],
            "baseline_daily_catch_kg": daily_baseline_kg,
            "favorability_ratio": ratio,
            "estimated_catch_kg": max(0.0, daily_baseline_kg * effective_ratio),
        }

    return {
        "region": region,
        "species": species,
        "days": [day],
        "disclaimer": (
            "Estimated from the region's historical average catch for this calendar "
            "month, adjusted by how the requested date's real forecast weather compares "
            "to the usual conditions for this month (via the trained Prophet model's own "
            "learned weather sensitivity). This is not an independently validated "
            "daily prediction -- no data source used in this project reports catch "
            "at finer than monthly resolution, so a true daily model cannot be "
            "trained or checked against real daily outcomes."
        ),
    }
