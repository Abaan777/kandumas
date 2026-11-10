"""UC1: view dashboard overview."""
from datetime import date

from tests.conftest import auth_header
from app.models.models import CatchRecord, Region, Species


def test_dashboard_overview_counts_match_seeded_data(client, db_session, fisherman_token):
    region = db_session.query(Region).filter_by(name="North Maldives").first()
    species = db_session.query(Species).filter_by(name="Yellowfin tuna").first()
    if db_session.query(CatchRecord).filter_by(region_id=region.id, species_id=species.id, catch_month=date(2024, 2, 1)).first() is None:
        db_session.add(CatchRecord(region_id=region.id, species_id=species.id, catch_month=date(2024, 2, 1), catch_kg=5000.0))
        db_session.commit()

    resp = client.get("/api/dashboard/overview", headers=auth_header(fisherman_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_regions"] >= 2
    assert body["total_species"] == 2
    assert body["max_forecast_catch_kg"] is not None
