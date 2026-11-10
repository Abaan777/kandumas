"""Live weather forecast (today through up to 7 days ahead -- Open-Meteo's own forecast
horizon is longer, but this project's daily catch estimate feature is deliberately
capped at 7 days, see daily_forecast_service.py), used only by the Dashboard's daily
catch estimate feature -- NOT one of this project's training data sources
(FAO/IOTC/NOAA) and not used anywhere in model training.

NOAA ERDDAP (see noaa.py) is a *retrospective* archive of satellite observations: it can
tell you what SST/wind were yesterday or last month, but it cannot answer "what will
the wind be tomorrow" -- there is no forward-looking product in that archive. Real
per-day figures for the next few days require an actual forecast service, so this
module calls Open-Meteo (https://open-meteo.com) -- free, no API key, no rate-limit
key required for this volume of use. Verified live before adopting it: both endpoints
below were queried for Male, Maldives (4.0N, 73.4E) and returned real, distinct
per-day values (e.g. wind 7.77/7.85/8.55 m/s and SST 29.8/29.8/29.8 C across three
consecutive real dates).
"""
from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"


def fetch_weather_forecast(lat: float, lon: float, days: int = 7) -> list[dict]:
    """Returns [{date, wind_speed (m/s), sst (C)}, ...] for today through `days - 1`
    days ahead, in the same units/variables the models were trained on (see noaa.py)."""
    wind_resp = requests.get(
        FORECAST_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": "wind_speed_10m_max",
            "forecast_days": days,
            "timezone": "auto",
            "wind_speed_unit": "ms",
        },
        timeout=15,
    )
    wind_resp.raise_for_status()
    wind_daily = wind_resp.json()["daily"]

    sst_resp = requests.get(
        MARINE_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "daily": "sea_surface_temperature_max",
            "forecast_days": days,
            "timezone": "auto",
        },
        timeout=15,
    )
    sst_resp.raise_for_status()
    sst_daily = sst_resp.json()["daily"]
    sst_by_date = dict(zip(sst_daily["time"], sst_daily["sea_surface_temperature_max"]))

    result = []
    for i, day in enumerate(wind_daily["time"]):
        result.append(
            {
                "date": day,
                "wind_speed": wind_daily["wind_speed_10m_max"][i],
                "sst": sst_by_date.get(day),
            }
        )
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(fetch_weather_forecast(4.0, 73.4))
