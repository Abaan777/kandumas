"""Loads trained model artifacts on demand and produces forecasts for
GET/POST /api/predict (UC3/UC4). Picks LSTM vs Prophet per (region, species) using the
`is_best` flag evaluate.py wrote to model_runs -- if evaluate.py hasn't run yet, falls
back to whichever artifact files actually exist on disk.
"""
from __future__ import annotations

from datetime import date

import joblib
import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.core.config import DATA_PROCESSED_DIR, ML_ARTIFACTS_DIR
from app.models.models import ModelRun, Region, Species


# A safety ceiling on how far generate_forecast() will push a model to "catch up" to
# the current calendar month (see _effective_months_ahead below) -- well above the
# public API's own months_ahead cap (12, see api/predict.py) since this is an internal
# floor, not something a user requests, but still bounded so a pathological data gap
# can't silently force an extreme, low-confidence multi-step rollout.
MAX_EFFECTIVE_MONTHS_AHEAD = 24


def _latest_data_month(region: str | None, species: str) -> pd.Timestamp | None:
    df = pd.read_csv(DATA_PROCESSED_DIR / "monthly_features.csv", parse_dates=["month"])
    df = df[df["species"] == species]
    if region:
        df = df[df["region"] == region]
    if df.empty:
        return None
    return df["month"].max()


# The Dashboard chart always displays the current month plus this many months beyond
# it (see ForecastChart.jsx, which slices the *last* MONTHS_BEYOND_CURRENT + 1 points
# off the returned list) -- the backend needs to actually generate that many so there's
# something there to slice.
MONTHS_BEYOND_CURRENT = 2


def _effective_months_ahead(region: str | None, species: str, requested_months_ahead: int) -> int:
    """A forecast always reaches at least MONTHS_BEYOND_CURRENT months past the current
    real calendar month, regardless of the requested months_ahead -- the model can
    still only forecast forward from its own last available data point (real or
    trailing-gap-filled, see preprocess.py), so this doesn't change what's predicted,
    only how many of the existing per-step loop's iterations run. Never shortens a
    larger explicit request."""
    latest_month = _latest_data_month(region, species)
    if latest_month is None:
        return requested_months_ahead
    today = date.today()
    months_to_reach_today = (today.year - latest_month.year) * 12 + (today.month - latest_month.month)
    floor = months_to_reach_today + MONTHS_BEYOND_CURRENT
    return max(requested_months_ahead, min(floor, MAX_EFFECTIVE_MONTHS_AHEAD))


def _safe(name: str) -> str:
    return name.replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "").lower()


class PredictionUnavailable(Exception):
    pass


def _load_history(region: str, species: str) -> pd.DataFrame:
    df = pd.read_csv(DATA_PROCESSED_DIR / "monthly_features.csv", parse_dates=["month"])
    return df[(df["region"] == region) & (df["species"] == species)].sort_values("month")


def _latest_run(db: Session, model_name: str, species_id: int, region: str | None) -> ModelRun | None:
    """Most recently trained ModelRun for this model+species, optionally restricted to
    a specific region (Prophet has one row per region; LSTM has a single national row
    with no region key in params_json, so region=None there)."""
    runs = (
        db.query(ModelRun)
        .filter_by(model_name=model_name, species_id=species_id)
        .order_by(ModelRun.trained_at.desc())
        .all()
    )
    for run in runs:
        run_region = (run.params_json or {}).get("region")
        if region is None or run_region == region:
            return run
    return None


def _metrics(run: ModelRun) -> dict:
    params = run.params_json or {}
    return {
        "rmse": run.rmse,
        "mape": run.mape,
        "mean_actual_catch": params.get("mean_actual_catch"),
        # Whichever of "log1p" / "none" won the raw-vs-log comparison at training
        # time (see train_lstm.py / train_prophet.py) -- inference must apply the
        # same transform the winning model was actually fit on.
        "target_transform": params.get("target_transform", "none"),
    }


def _select_model_and_metrics(db: Session, region: str, species: str) -> tuple[str, dict | None]:
    """Decide LSTM vs. Prophet for this exact (region, species) by comparing their
    stored RMSE directly, rather than trusting a precomputed `is_best` flag.

    `is_best` (written by evaluate.py) can't correctly encode "LSTM wins for this one
    region" because LSTM is a single national model shared across all 3 regions while
    Prophet has one model per region -- a boolean on the single LSTM row can't be True
    for one region's comparison and False for another's. So `is_best` is kept as
    informational display data for the Admin metrics table, and the actual routing
    decision here is a direct, unambiguous RMSE comparison of the two specific
    candidates for this (region, species)."""
    species_row = db.query(Species).filter_by(name=species).first()
    prophet_run = None
    lstm_run = None
    if species_row is not None:
        prophet_run = _latest_run(db, "prophet", species_row.id, region)
        lstm_run = _latest_run(db, "lstm", species_row.id, None)

    if prophet_run and lstm_run:
        if prophet_run.rmse <= lstm_run.rmse:
            return "prophet", _metrics(prophet_run)
        return "lstm", _metrics(lstm_run)
    if prophet_run:
        return "prophet", _metrics(prophet_run)
    if lstm_run:
        return "lstm", _metrics(lstm_run)

    # Fallback purely on artifact presence when the DB hasn't been evaluated yet.
    if (ML_ARTIFACTS_DIR / f"prophet_{_safe(region)}_{_safe(species)}.json").exists():
        return "prophet", None
    if (ML_ARTIFACTS_DIR / f"lstm_{_safe(species)}.keras").exists():
        return "lstm", None
    raise PredictionUnavailable(f"No trained model found for region='{region}' species='{species}'")


def _select_national_lstm(db: Session, species: str) -> dict | None:
    """The "All regions" case: LSTM is the only model trained nationally (across all
    regions combined, see train_lstm.py) -- Prophet is always per-region, so there is
    no single Prophet model that represents "all regions" and it's never considered
    here."""
    species_row = db.query(Species).filter_by(name=species).first()
    lstm_run = _latest_run(db, "lstm", species_row.id, None) if species_row else None
    if lstm_run:
        return _metrics(lstm_run)
    if (ML_ARTIFACTS_DIR / f"lstm_{_safe(species)}.keras").exists():
        return None
    raise PredictionUnavailable(f"No trained national model found for species='{species}'")


def _predict_prophet(
    region: str, species: str, months_ahead: int, target_transform: str = "none"
) -> list[tuple[date, float]]:
    from prophet.serialize import model_from_json

    path = ML_ARTIFACTS_DIR / f"prophet_{_safe(region)}_{_safe(species)}.json"
    if not path.exists():
        raise PredictionUnavailable(f"Prophet artifact missing for {region}/{species}")
    with open(path) as f:
        model = model_from_json(f.read())

    history = _load_history(region, species)
    last_row = history.dropna(subset=["sst", "wind_speed"]).iloc[-1]
    future = pd.DataFrame(
        {
            "ds": [last_row["month"] + relativedelta(months=i) for i in range(1, months_ahead + 1)],
            "sst": [last_row["sst"]] * months_ahead,
            "wind_speed": [last_row["wind_speed"]] * months_ahead,
        }
    )
    if "salinity" in model.extra_regressors and pd.notna(last_row.get("salinity")):
        future["salinity"] = [last_row["salinity"]] * months_ahead
    forecast = model.predict(future)
    if target_transform == "log1p":
        # This particular model was the log1p-space winner (see train_prophet.py) --
        # expm1 back to real kg, capped at 5x the region's historical max as a safety
        # net against the same log-space extrapolation blowup train_prophet.py guards
        # against (a regressor value outside the training range can make expm1
        # explode).
        cap_kg = history["catch_kg"].max() * 5
        predicted_kg = np.expm1(forecast["yhat"]).clip(lower=0, upper=cap_kg)
    else:
        predicted_kg = forecast["yhat"].clip(lower=0)
    return list(zip(forecast["ds"].dt.date.tolist(), predicted_kg.tolist()))


def _predict_lstm(species: str, months_ahead: int, target_transform: str = "none") -> list[tuple[date, float]]:
    from tensorflow import keras

    model_path = ML_ARTIFACTS_DIR / f"lstm_{_safe(species)}.keras"
    scaler_path = ML_ARTIFACTS_DIR / f"lstm_{_safe(species)}_scaler.joblib"
    if not model_path.exists():
        raise PredictionUnavailable(f"LSTM artifact missing for {species}")

    model = keras.models.load_model(model_path)
    bundle = joblib.load(scaler_path)
    scaler, feature_cols, window = bundle["scaler"], bundle["feature_cols"], bundle["window"]

    df = pd.read_csv(DATA_PROCESSED_DIR / "monthly_features.csv", parse_dates=["month"])
    national = (
        df[df["species"] == species]
        .groupby("month", as_index=False)
        .agg(catch_kg=("catch_kg", "sum"), sst=("sst", "mean"), wind_speed=("wind_speed", "mean"), salinity=("salinity", "mean"))
        .sort_values("month")
        .dropna(subset=feature_cols)
    )
    if len(national) < window:
        raise PredictionUnavailable(f"Not enough history to run the LSTM for {species}")

    # Matches whichever transform train_lstm.py found best for this species (see its
    # raw-vs-log1p comparison) -- the saved scaler was fit on values in that same
    # space, so inference must feed it (and invert its output) the same way.
    is_log = target_transform == "log1p"
    last_window = national[feature_cols].to_numpy(dtype=float).copy()
    if is_log:
        last_window[:, 0] = np.log1p(last_window[:, 0])
    log_cap = np.log1p(national["catch_kg"].max() * 5) if is_log else None
    last_window = last_window[-window:]
    scaled_window = scaler.transform(last_window)
    last_month = national["month"].iloc[-1]

    results = []
    current_window = scaled_window.copy()
    for i in range(1, months_ahead + 1):
        pred_scaled = model.predict(current_window[np.newaxis, ...], verbose=0)[0, 0]
        padded = np.zeros((1, len(feature_cols)))
        padded[0, 0] = pred_scaled
        inverse_value = scaler.inverse_transform(padded)[0, 0]
        if is_log:
            # Same log-space extrapolation safety net as train_lstm.py/train_prophet.py.
            pred_catch = float(np.expm1(min(inverse_value, log_cap)))
        else:
            pred_catch = float(inverse_value)
        target_month = last_month + relativedelta(months=i)
        results.append((target_month.date(), max(pred_catch, 0.0)))

        # Roll the window forward, holding environmental features at their last known
        # value (no future SST/wind forecast is available) and feeding back the
        # model's own prediction for catch_kg -- standard autoregressive multi-step
        # forecasting.
        next_row = current_window[-1].copy()
        next_row[0] = pred_scaled
        current_window = np.vstack([current_window[1:], next_row])

    return results


def generate_forecast(
    db: Session, region: str | None, species: str, months_ahead: int
) -> tuple[str, dict | None, list[tuple[date, float]]]:
    # A forecast always reaches the current real calendar month, not just whatever the
    # months_ahead dial was set to -- see _effective_months_ahead.
    months_ahead = _effective_months_ahead(region, species, months_ahead)

    # Empty/None region means "All regions" -- go straight to the national LSTM model,
    # skipping the per-region Prophet comparison entirely (see _select_national_lstm).
    if not region:
        metrics = _select_national_lstm(db, species)
        target_transform = metrics.get("target_transform", "none") if metrics else "none"
        return "lstm", metrics, _predict_lstm(species, months_ahead, target_transform)

    model_name, metrics = _select_model_and_metrics(db, region, species)
    # "none" if evaluate.py hasn't run yet (metrics is None) -- an edge case that only
    # occurs right after training before evaluation, and errs toward not applying a
    # transform the model may or may not have actually been fit with.
    target_transform = metrics.get("target_transform", "none") if metrics else "none"
    if model_name == "prophet":
        return "prophet", metrics, _predict_prophet(region, species, months_ahead, target_transform)
    return "lstm", metrics, _predict_lstm(species, months_ahead, target_transform)


def _accuracy_from_nrmse(rmse: float | None, mean_actual_catch: float | None) -> float | None:
    """"Accuracy" as shown on the map is 100% minus the *normalized* RMSE (RMSE
    relative to the typical catch size for that region/species), not 100 - MAPE.

    MAPE is the mean of *per-month* percentage errors, so a handful of very-low-catch
    test months (division by a small number) can blow the average past 100% even when
    the model's typical error is unremarkable -- e.g. North Maldives/Skipjack has
    RMSE=699,382 kg against a mean catch of ~1.4M kg (a normal ~50% relative error),
    yet its MAPE alone renders as "0% accurate". RMSE normalized by the mean actual
    value doesn't have that single-month blowup problem, so it's what drives the map's
    color/label; RMSE and MAPE themselves are unchanged and still shown in full in the
    Admin metrics table and prediction popups (Objective 5 requires reporting both)."""
    if rmse is None or not mean_actual_catch:
        return None
    nrmse = rmse / mean_actual_catch
    return max(0.0, 100.0 * (1 - nrmse))


def get_region_accuracy(db: Session, species: str) -> list[dict]:
    """For the map: the best model's accuracy for every region, for one species.
    Reuses the same region/species model-selection logic as an actual prediction, but
    only reads stored metrics -- no model artifact is loaded and no inference runs, so
    this is cheap enough to call whenever the species filter changes."""
    results = []
    for region in db.query(Region).all():
        try:
            model_name, metrics = _select_model_and_metrics(db, region.name, species)
        except PredictionUnavailable:
            model_name, metrics = None, None
        results.append(
            {
                "region": region.name,
                "model_name": model_name,
                "rmse": metrics["rmse"] if metrics else None,
                "mape": metrics["mape"] if metrics else None,
                "accuracy_pct": (
                    _accuracy_from_nrmse(metrics["rmse"], metrics.get("mean_actual_catch")) if metrics else None
                ),
            }
        )
    return results
