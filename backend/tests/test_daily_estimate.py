"""GET /api/predict/daily -- single-date, weather-adjusted catch estimate, capped at
7 days ahead of today. The real Open-Meteo call is mocked out (network-dependent and
not the thing under test); the real trained Prophet artifact for North Maldives/
Skipjack tuna *is* exercised, same as the real end-to-end test in test_predict.py."""
from datetime import date, timedelta

from tests.conftest import auth_header


def _fake_weather(lat, lon, days=7):
    today = date.today()
    return [{"date": (today + timedelta(days=i)).isoformat(), "wind_speed": 5.0, "sst": 28.5} for i in range(days)]


def test_daily_estimate_defaults_to_today(client, fisherman_token, monkeypatch):
    monkeypatch.setattr("app.services.daily_forecast_service.fetch_weather_forecast", _fake_weather)
    resp = client.get(
        "/api/predict/daily",
        params={"region": "North Maldives", "species": "Skipjack tuna"},
        headers=auth_header(fisherman_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["days"]) == 1
    assert body["days"][0]["date"] == date.today().isoformat()


def test_daily_estimate_accepts_a_date_within_the_7_day_window(client, fisherman_token, monkeypatch):
    monkeypatch.setattr("app.services.daily_forecast_service.fetch_weather_forecast", _fake_weather)
    target = date.today() + timedelta(days=5)
    resp = client.get(
        "/api/predict/daily",
        params={"region": "North Maldives", "species": "Skipjack tuna", "date": target.isoformat()},
        headers=auth_header(fisherman_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["days"][0]["date"] == target.isoformat()


def test_daily_estimate_rejects_a_date_in_the_past(client, fisherman_token, monkeypatch):
    monkeypatch.setattr("app.services.daily_forecast_service.fetch_weather_forecast", _fake_weather)
    target = date.today() - timedelta(days=1)
    resp = client.get(
        "/api/predict/daily",
        params={"region": "North Maldives", "species": "Skipjack tuna", "date": target.isoformat()},
        headers=auth_header(fisherman_token),
    )
    assert resp.status_code == 400


def test_daily_estimate_rejects_a_date_more_than_7_days_ahead(client, fisherman_token, monkeypatch):
    monkeypatch.setattr("app.services.daily_forecast_service.fetch_weather_forecast", _fake_weather)
    target = date.today() + timedelta(days=7)  # valid range is day 0 (today) through day 6
    resp = client.get(
        "/api/predict/daily",
        params={"region": "North Maldives", "species": "Skipjack tuna", "date": target.isoformat()},
        headers=auth_header(fisherman_token),
    )
    assert resp.status_code == 400


def test_daily_estimate_404_for_unknown_region(client, fisherman_token, monkeypatch):
    monkeypatch.setattr("app.services.daily_forecast_service.fetch_weather_forecast", _fake_weather)
    resp = client.get(
        "/api/predict/daily",
        params={"region": "Atlantis", "species": "Skipjack tuna"},
        headers=auth_header(fisherman_token),
    )
    assert resp.status_code == 404
