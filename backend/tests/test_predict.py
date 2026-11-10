"""UC3/UC4: generating predictions -- and the honest failure path (4.3.3.3 Error
Handling) when no model has been trained for a given region/species combination yet.

Note: prediction_service falls back to checking the real ML artifacts directory
(backend/app/ml/artifacts) on disk when a (region, species) has no model_runs row yet,
so these tests use a species that genuinely has no trained artifact anywhere, rather
than mocking the artifacts dir away.

Also note: generate_forecast() always extends far enough to reach the current real
calendar month (see prediction_service._effective_months_ahead), so a requested
months_ahead is a *minimum*, not an exact point count -- tests against the real trained
models assert `>=`, not `==`, on len(points)."""
from datetime import date

from tests.conftest import auth_header

UNTRAINED_SPECIES = "Nonexistent species"


def test_predict_returns_404_when_no_model_trained(client, fisherman_token):
    resp = client.get(
        "/api/predict",
        params={"region": "North Maldives", "species": UNTRAINED_SPECIES, "months_ahead": 3},
        headers=auth_header(fisherman_token),
    )
    # PredictionUnavailable -> 404, not a raw 500. Matches the "clear error message"
    # reliability requirement (4.3.3.3).
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_predict_succeeds_for_a_real_trained_combination(client, fisherman_token):
    """Skipjack tuna / North Maldives has a real trained Prophet model on disk (this
    is the one real end-to-end integration test in the suite -- it exercises the
    actual saved model artifact, not a mock)."""
    resp = client.get(
        "/api/predict",
        params={"region": "North Maldives", "species": "Skipjack tuna", "months_ahead": 3},
        headers=auth_header(fisherman_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["model_used"] in ("lstm", "prophet")
    assert len(body["points"]) >= 3
    assert all(p["predicted_catch_kg"] >= 0 for p in body["points"])


def _add_months(d: date, n: int) -> date:
    month_index = d.month - 1 + n
    return date(d.year + month_index // 12, month_index % 12 + 1, 1)


def test_predict_always_reaches_2_months_past_the_current_calendar_month(client, fisherman_token):
    """Even asking for just 1 month ahead should still produce a forecast whose last 3
    points are the current month plus the following two -- that's the window
    ForecastChart.jsx actually displays (it slices the *last* 3 points off the
    response), so the backend needs to generate at least that far."""
    resp = client.get(
        "/api/predict",
        params={"region": "North Maldives", "species": "Skipjack tuna", "months_ahead": 1},
        headers=auth_header(fisherman_token),
    )
    assert resp.status_code == 200, resp.text
    points = resp.json()["points"]
    target_months = [date.fromisoformat(p["target_month"]) for p in points]
    today = date.today().replace(day=1)
    last_three = target_months[-3:]
    assert last_three == [today, _add_months(today, 1), _add_months(today, 2)]


def test_predict_accuracy_handles_untrained_species_gracefully(client, fisherman_token):
    resp = client.get(
        "/api/predict/accuracy",
        params={"species": UNTRAINED_SPECIES},
        headers=auth_header(fisherman_token),
    )
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) >= 1
    # No model/artifact exists anywhere for this species, so every region comes back
    # with nulls instead of raising -- this is what makes the dashboard map safe to
    # render for a species that hasn't been trained yet.
    assert all(r["model_name"] is None for r in rows)


def test_predict_rejects_months_ahead_out_of_range(client, fisherman_token):
    resp = client.get(
        "/api/predict",
        params={"region": "North Maldives", "species": "Skipjack tuna", "months_ahead": 99},
        headers=auth_header(fisherman_token),
    )
    assert resp.status_code == 422


def test_predict_with_empty_region_uses_the_national_lstm_model(client, fisherman_token):
    """An empty region is the frontend's "All regions" option -- Prophet is always
    per-region, so this should route straight to the nationally-trained LSTM model
    rather than failing."""
    resp = client.get(
        "/api/predict",
        params={"region": "", "species": "Skipjack tuna", "months_ahead": 3},
        headers=auth_header(fisherman_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["model_used"] == "lstm"
    assert body["region"] == "All regions"
    assert len(body["points"]) >= 3


def test_predict_with_empty_region_404s_when_no_national_model_trained(client, fisherman_token):
    resp = client.get(
        "/api/predict",
        params={"region": "", "species": UNTRAINED_SPECIES, "months_ahead": 3},
        headers=auth_header(fisherman_token),
    )
    assert resp.status_code == 404
