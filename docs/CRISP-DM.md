# CRISP-DM Mapping

Chapter 1 (Development Methodology) specifies CRISP-DM for the machine learning side of
this project. This document maps each phase to the actual code that implements it.

## 1. Business Understanding

Goal: forecast Maldivian tuna catch volume by region, species and month, using
environmental and historical data, to support fishing-trip planning (see Chapter 1,
Project Aim and Objectives). Success is measured by RMSE/MAPE on a chronological
hold-out split (Objective 5).

## 2. Data Understanding

`backend/app/ml/ingestion/iotc.py` and `backend/app/ml/ingestion/noaa.py` pull the real
datasets described in `DATA_SOURCES.md`: IOTC catch-by-area (Maldives fleet, monthly,
1970-2025) and NOAA ERDDAP SST/wind/salinity (per region, 2010-present).

## 3. Data Preparation

`backend/app/ml/pipeline/preprocess.py`:
- Filters IOTC rows to metric-ton-reported catch only (excludes count-based bycatch
  rows, which use a different, non-summable unit).
- Aggregates catch to monthly totals per (region, species).
- Scopes the forecasting target to the Maldives' two main commercial tuna species:
  skipjack tuna and yellowfin tuna. All other species/bycatch categories reported in
  the raw IOTC file are excluded.
- Aggregates NOAA environmental readings to monthly means per region.
- Interpolates short (<=2 month) environmental gaps; leaves longer gaps as real NaN
  values rather than fabricating data, and the training scripts handle those
  explicitly (see below).
- Merges catch and environmental data on (region, month) into
  `data/processed/monthly_features.csv`.

## 4. Modeling

Two models, matching the Literature Review's stated choice of LSTM as primary and
Prophet as secondary/seasonal-validation model:

- `backend/app/ml/training/train_lstm.py` -- one multivariate LSTM per species, trained
  on the **national** (all-region) monthly series. Deliberately not split further by
  region: with salinity's 2010+ coverage, splitting into 3 regions would leave too few
  real (non-imputed) months per series for an LSTM to learn from. This trade-off is
  documented in the module docstring, not hidden.
- `backend/app/ml/training/train_prophet.py` -- one Prophet model per (region, species)
  pair, with SST and wind speed as regressors always, and salinity added only when that
  combination's data already starts at/after the real 2010-06 salinity coverage date.
  This is what serves region-specific forecasts (UC4).

## 5. Evaluation

`backend/app/ml/training/train_lstm.py` / `train_prophet.py` compute RMSE and MAPE on a
chronological (not random) 80/20 train/test split -- the last 20% of months are always
the test set, since shuffling a time series would leak future information into
training. `backend/app/ml/training/evaluate.py` combines both sets of metrics, decides
which model serves each (region, species) pair (whichever has the lower RMSE), and
writes everything to the `model_runs` table for the Admin > Monitor System & Model
Performance page (UC7).

## 6. Deployment

`backend/app/services/prediction_service.py` loads the saved LSTM (`.keras` +
scaler) or Prophet (`.json`) artifacts on demand and serves `/api/predict`. The Admin
page's "Retrain Model" button (UC8) re-runs steps 4-5 in the background via
`/api/admin/retrain`; "Refresh Datasets" re-runs steps 2-3 via
`/api/admin/datasets/refresh`.
