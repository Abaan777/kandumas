"""UC2: view historical data trends, with region/species/date filtering (UC4)."""
from datetime import date

from tests.conftest import auth_header
from app.models.models import CatchRecord, EnvironmentalObservation, Region, Species


def _seed_one_catch_record(db_session):
    region = db_session.query(Region).filter_by(name="North Maldives").first()
    species = db_session.query(Species).filter_by(name="Skipjack tuna").first()
    month = date(2024, 1, 1)
    if db_session.query(CatchRecord).filter_by(region_id=region.id, species_id=species.id, catch_month=month).first() is None:
        db_session.add(CatchRecord(region_id=region.id, species_id=species.id, catch_month=month, catch_kg=12345.0))
    if db_session.query(EnvironmentalObservation).filter_by(region_id=region.id, obs_month=month).first() is None:
        db_session.add(EnvironmentalObservation(region_id=region.id, obs_month=month, sst=28.5, wind_speed=4.2, salinity=34.1))
    db_session.commit()


def test_historical_filters_by_region_and_species(client, db_session, fisherman_token):
    _seed_one_catch_record(db_session)

    resp = client.get(
        "/api/historical",
        params={"region": "North Maldives", "species": "Skipjack tuna"},
        headers=auth_header(fisherman_token),
    )
    assert resp.status_code == 200
    points = resp.json()
    assert len(points) >= 1
    row = next(p for p in points if p["month"] == "2024-01-01")
    assert row["catch_kg"] == 12345.0
    assert row["sst"] == 28.5


def test_historical_empty_for_unknown_region(client, db_session, fisherman_token):
    _seed_one_catch_record(db_session)

    resp = client.get(
        "/api/historical",
        params={"region": "Atlantis", "species": "Skipjack tuna"},
        headers=auth_header(fisherman_token),
    )
    assert resp.status_code == 200
    assert resp.json() == []
