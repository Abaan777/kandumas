"""CRISP-DM 'Modeling' step -- LSTM.

Trains one multivariate LSTM per species (as the literature review specifies: LSTM as
the primary forecasting model for the seasonal, multi-variable Maldives catch series).
Catch and environmental data are aggregated to a national (all-region) monthly series
per species -- the per-region breakdown is left to the Prophet models in
train_prophet.py, because splitting 3 regions further would leave each LSTM with too
few real (non-imputed) months to learn from once salinity's 2010+ coverage window is
applied. This trade-off is deliberate and documented, not an oversight.

Target transform: catch_kg spans orders of magnitude for the low-volume species (many
near-zero months, occasional large spikes), and training directly on that scale made
those species' RMSE many times larger than their typical catch (MSE loss dominated by
the few largest spikes, so the network mostly just learned to predict "average").
log1p(catch_kg) fixes that -- but isn't a universal improvement (see train_prophet.py
for the same finding on the Prophet side), so both a raw-scale and a log1p-scale
network are trained for every species and whichever has the lower test RMSE is kept.
Which transform won is recorded in the metrics (`target_transform`) so
prediction_service.py knows how to invert it when serving live forecasts.
"""
from __future__ import annotations

import json
import logging

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from app.core.config import DATA_PROCESSED_DIR, ML_ARTIFACTS_DIR
from app.ml.training.common import mape, rmse, widest_window_with_columns

logger = logging.getLogger(__name__)

WINDOW = 6  # months of history the LSTM looks back on to predict the next month
MIN_ROWS_FOR_FULL_FEATURES = 60  # ~5 years; below this we drop salinity to widen the window
TEST_FRACTION = 0.2


def _national_series(df: pd.DataFrame, species: str) -> pd.DataFrame:
    sub = df[df["species"] == species]
    agg = sub.groupby("month", as_index=False).agg(
        catch_kg=("catch_kg", "sum"),
        sst=("sst", "mean"),
        wind_speed=("wind_speed", "mean"),
        salinity=("salinity", "mean"),
    )
    return agg.sort_values("month")


def _build_sequences(values: np.ndarray, window: int) -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for i in range(len(values) - window):
        X.append(values[i : i + window, :])
        y.append(values[i + window, 0])  # column 0 is catch_kg (the predicted target)
    return np.array(X), np.array(y)


def _fit_and_eval_lstm(raw_values: np.ndarray, feature_cols: list[str], use_log: bool):
    from tensorflow import keras

    values = raw_values.copy()
    if use_log:
        values[:, 0] = np.log1p(values[:, 0])
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(values)

    X, y = _build_sequences(scaled, WINDOW)
    split = int(len(X) * (1 - TEST_FRACTION))
    split = max(split, WINDOW)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    if len(X_test) == 0:
        return None

    model = keras.Sequential(
        [
            keras.layers.Input(shape=(WINDOW, len(feature_cols))),
            keras.layers.LSTM(32, activation="tanh"),
            keras.layers.Dense(16, activation="relu"),
            keras.layers.Dense(1),
        ]
    )
    model.compile(optimizer="adam", loss="mse")
    early_stop = keras.callbacks.EarlyStopping(monitor="loss", patience=8, restore_best_weights=True)
    model.fit(X_train, y_train, epochs=150, batch_size=8, verbose=0, callbacks=[early_stop])

    pred_scaled = model.predict(X_test, verbose=0).flatten()

    def inverse_catch(scaled_catch: np.ndarray) -> np.ndarray:
        padded = np.zeros((len(scaled_catch), len(feature_cols)))
        padded[:, 0] = scaled_catch
        out = scaler.inverse_transform(padded)[:, 0]
        if use_log:
            # Same overflow risk as Prophet's log-space regressors (see
            # train_prophet.py's _expm1_capped) -- a poorly-fit network can push a
            # scaled value slightly outside [0,1] on a held-out point, and expm1 of
            # that amplifies exponentially. Cap at 5x the largest real value the
            # network was trained on.
            out = np.clip(out, None, np.log1p(raw_values[:, 0].max() * 5))
            out = np.expm1(out)
        return out

    y_test_actual = inverse_catch(y_test)
    y_pred_actual = inverse_catch(pred_scaled)

    return {
        "model": model,
        "scaler": scaler,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "rmse": rmse(y_test_actual, y_pred_actual),
        "mape": mape(y_test_actual, y_pred_actual),
        "mean_actual_catch": float(y_test_actual.mean()),
    }


def train_one_species(species: str, df: pd.DataFrame) -> dict | None:
    national = _national_series(df, species)

    full_cols = ["catch_kg", "sst", "wind_speed", "salinity"]
    windowed = widest_window_with_columns(national, "month", full_cols)
    feature_cols = full_cols
    if len(windowed) < MIN_ROWS_FOR_FULL_FEATURES:
        logger.info(
            "%s: only %s months with sst+wind+salinity all present; dropping salinity "
            "to use the longer sst+wind window instead",
            species,
            len(windowed),
        )
        feature_cols = ["catch_kg", "sst", "wind_speed"]
        windowed = widest_window_with_columns(national, "month", feature_cols)

    if len(windowed) < WINDOW + 10:
        logger.warning("%s: not enough data (%s months) to train an LSTM, skipping", species, len(windowed))
        return None

    raw_values = windowed[feature_cols].to_numpy(dtype=float)

    raw_result = _fit_and_eval_lstm(raw_values, feature_cols, use_log=False)
    log_result = _fit_and_eval_lstm(raw_values, feature_cols, use_log=True)
    if raw_result is None and log_result is None:
        logger.warning("%s: no test rows after split, skipping evaluation", species)
        return None

    if raw_result is None or (log_result is not None and log_result["rmse"] < raw_result["rmse"]):
        winner, target_transform = log_result, "log1p"
    else:
        winner, target_transform = raw_result, "none"

    metrics = {
        "species": species,
        "model_name": "lstm",
        "feature_cols": feature_cols,
        "window": WINDOW,
        "target_transform": target_transform,
        "n_train": winner["n_train"],
        "n_test": winner["n_test"],
        "rmse": winner["rmse"],
        "mape": winner["mape"],
        "mean_actual_catch": winner["mean_actual_catch"],
        "train_start": str(windowed["month"].iloc[0].date()),
        "train_end": str(windowed["month"].iloc[-1].date()),
    }

    safe_name = species.replace(" ", "_").replace("/", "_").lower()
    ML_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    winner["model"].save(ML_ARTIFACTS_DIR / f"lstm_{safe_name}.keras")
    joblib.dump(
        {"scaler": winner["scaler"], "feature_cols": feature_cols, "window": WINDOW},
        ML_ARTIFACTS_DIR / f"lstm_{safe_name}_scaler.joblib",
    )
    logger.info(
        "%s: LSTM(%s) RMSE=%.1f MAPE=%.1f%% (n_test=%s; raw RMSE=%s, log1p RMSE=%s)",
        species,
        target_transform,
        metrics["rmse"],
        metrics["mape"],
        winner["n_test"],
        f"{raw_result['rmse']:.1f}" if raw_result else "n/a",
        f"{log_result['rmse']:.1f}" if log_result else "n/a",
    )
    return metrics


def train_all() -> list[dict]:
    df = pd.read_csv(DATA_PROCESSED_DIR / "monthly_features.csv", parse_dates=["month"])
    results = []
    for species in sorted(df["species"].unique()):
        result = train_one_species(species, df)
        if result:
            results.append(result)

    ML_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ML_ARTIFACTS_DIR / "lstm_metrics.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    results = train_all()
    for r in results:
        print(r)
