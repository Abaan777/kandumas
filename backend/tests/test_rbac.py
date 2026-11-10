"""Security requirement 4.3.4.2 (API Protection) / UC6-UC8 (admin-only): admin routes
must reject non-admin roles and accept admin."""
from tests.conftest import auth_header


def test_admin_metrics_rejects_fisherman(client, fisherman_token):
    resp = client.get("/api/admin/metrics", headers=auth_header(fisherman_token))
    assert resp.status_code == 403


def test_admin_metrics_rejects_officer(client, officer_token):
    resp = client.get("/api/admin/metrics", headers=auth_header(officer_token))
    assert resp.status_code == 403


def test_admin_metrics_allows_admin(client, admin_token):
    resp = client.get("/api/admin/metrics", headers=auth_header(admin_token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_admin_retrain_rejects_non_admin(client, fisherman_token):
    resp = client.post("/api/admin/retrain", headers=auth_header(fisherman_token))
    assert resp.status_code == 403
