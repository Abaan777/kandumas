# User Manual

A plain-language guide to using Kandumas, the Maldives tuna catch forecasting
dashboard, for the three actor roles defined in Chapter 5 (Use Case Analysis) of the
proposal: Fisherman, Fisheries Officer, and System Administrator. The same guidance is
also available inside the app itself, on the **Help** page in the navigation bar.

## 1. Signing in

Open the app and you'll land on the login screen. Enter your username and password, or
use **Create one** to self-register a new Fisherman account. If you've forgotten your
password, use **Forgot password?** -- see Chapter 5's note on self-registration and
password reset for how that flow works. Each role sees a different set of navigation
links:

| Role | Can see |
|---|---|
| Fisherman | Dashboard, Historical Data & Trends, Reports, Help |
| Fisheries Officer | Dashboard, Historical Data & Trends, Reports, Help |
| System Administrator | All of the above, plus Admin |

## 2. Dashboard (UC1, UC3, UC4)

This is the main forecast screen.

1. Choose a **Region** and a **Species** in the filter bar (only Skipjack tuna and
   Yellowfin tuna are tracked -- see `docs/DATA_SOURCES.md`).
2. Set **Months ahead** (1-12).
3. Click **Generate Prediction**. The chart shows the predicted catch on top of the
   most recent historical catch, and the model used (LSTM or Prophet) plus its RMSE
   and MAPE accuracy figures are shown underneath.
4. The **Today / Next 2 Days** card shows a live weather-adjusted daily estimate --
   see the disclaimer on that card for exactly what it is (and isn't).
5. The **Region Map** colors every region on a gradient by forecast accuracy for the
   currently selected species -- red is most accurate, fading through orange and
   yellow down to blue for least accurate. Hover/click a marker for
   details.

If a combination hasn't been trained yet, the Dashboard shows a clear message instead
of failing silently.

## 3. Historical Data & Trends (UC2)

Filter by region/species to see:
- A catch-volume chart (last 3 years)
- Sea surface temperature, wind speed, and salinity trend charts
- A data table of the most recent 24 months, for anything the charts don't make
  obvious at a glance.

## 4. Reports (UC5)

Choose a region, species, forecast horizon, and file format (CSV or PDF), then click
**Download Report**. The file contains the forecast plus recent historical and
environmental data, so it can be reviewed offline or shared with someone who doesn't
have dashboard access.

## 5. Admin (UC6, UC7, UC8 -- admin role only)

- **Refresh Datasets**: re-fetches the latest IOTC catch data and NOAA environmental
  data, and rebuilds the processed feature table. Runs in the background.
- **Retrain Model**: re-trains the LSTM and Prophet models on the current data and
  re-evaluates which one is best per region/species. Also runs in the background.
- **Model Performance table**: shows RMSE/MAPE for every trained model, and which one
  is currently marked best for each region/species combination.

Both actions are asynchronous -- use **Refresh Metrics Table** a little afterwards to
see the results once the background job finishes (check the backend logs for
completion if it's taking a while; a full retrain involves 2 LSTM models and 6 Prophet
models).

## 6. Help

The in-app Help page (`/help`) has the same FAQ-style guidance as this document --
what RMSE/MAPE mean, what the region map colors mean, why a forecast's starting month
can lag behind the latest catch record, and what the admin actions do.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| "No trained model found for this region/species" | Nobody has run `train_lstm`/`train_prophet` (or the Admin "Retrain Model" action) yet for that combination. |
| Login fails with correct-looking credentials | Double-check the username/password, or use **Forgot password?** on the login screen. |
| Report download fails | Same root cause as the prediction failure above -- a report needs a trained model to forecast from. |
| Admin page is missing from the nav | You're signed in as `fisherman1` or `officer1`, not `admin1` -- this is role-based access control working as intended (4.3.4.2). |
