"""Loads the processed feature table (data/processed/monthly_features.csv) and the raw
IOTC species metadata into MySQL, and creates the three demo accounts (one per actor
role in Chapter 5: fisherman, officer, admin). Safe to re-run -- it upserts by natural
key instead of duplicating rows.
"""
from __future__ import annotations

import logging
import math

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import DATA_PROCESSED_DIR, DATA_RAW_DIR, get_settings
from app.core.database import SessionLocal, engine
from app.core.database import Base
from app.core.security import hash_password
from app.ml.ingestion.regions import REGION_DEFINITIONS
from app.ml.pipeline.preprocess import TARGET_SPECIES
from app.models.models import (
    CatchRecord,
    EnvironmentalObservation,
    ModelRun,
    Prediction,
    Region,
    Species,
    User,
)

logger = logging.getLogger(__name__)
settings = get_settings()


def _float_changed(stored: float | None, new: float | None) -> bool:
    """True if `new` represents a real change from `stored`, ignoring the float
    round-trip noise MySQL's single-precision FLOAT column introduces (a value written
    as a Python double and read back loses precision -- observed empirically up to
    ~4e-6 relative error on real catch_kg values in the millions) -- a plain `!=` or an
    overly tight tolerance would report nearly every row as "updated" on every single
    reseed even when nothing meaningful changed."""
    if stored is None or new is None:
        return stored != new
    return not math.isclose(stored, new, rel_tol=1e-4, abs_tol=1e-4)


def _get_or_create_region(db: Session, name: str, lat: float, lon: float) -> Region:
    region = db.query(Region).filter_by(name=name).first()
    if region is None:
        region = Region(name=name, lat_center=lat, lon_center=lon)
        db.add(region)
        db.flush()
    return region


def _get_or_create_species(db: Session, code: str, name: str, scientific: str | None) -> Species:
    species = db.query(Species).filter_by(code=code).first()
    if species is None:
        species = Species(code=code, name=name, scientific_name=scientific)
        db.add(species)
        db.flush()
    return species


def seed_users(db: Session) -> None:
    demo_accounts = [
        ("fisherman1", settings.demo_fisherman_password, "fisherman"),
        ("officer1", settings.demo_officer_password, "officer"),
        ("admin1", settings.demo_admin_password, "admin"),
    ]
    for username, password, role in demo_accounts:
        if db.query(User).filter_by(username=username).first() is None:
            db.add(User(username=username, password_hash=hash_password(password), role=role))
    db.commit()
    logger.info("Seeded demo users: %s", [u for u, _, _ in demo_accounts])


def seed_regions(db: Session) -> dict[str, Region]:
    regions = {}
    for r in REGION_DEFINITIONS:
        regions[r["name"]] = _get_or_create_region(db, r["name"], r["lat_center"], r["lon_center"])
    db.commit()
    return regions


def prune_non_target_species(db: Session) -> None:
    """Removes any species (and the catch/model/prediction rows that reference them)
    left over from before the dashboard was scoped down to TARGET_SPECIES. Safe to
    re-run -- a no-op once the DB only has skipjack and yellowfin."""
    stale = db.query(Species).filter(~Species.name.in_(TARGET_SPECIES)).all()
    if not stale:
        return
    stale_ids = [s.id for s in stale]
    stale_names = [s.name for s in stale]
    db.query(Prediction).filter(Prediction.species_id.in_(stale_ids)).delete(synchronize_session=False)
    db.query(ModelRun).filter(ModelRun.species_id.in_(stale_ids)).delete(synchronize_session=False)
    db.query(CatchRecord).filter(CatchRecord.species_id.in_(stale_ids)).delete(synchronize_session=False)
    db.query(Species).filter(Species.id.in_(stale_ids)).delete(synchronize_session=False)
    db.commit()
    logger.info("Pruned %s non-target species: %s", len(stale_names), stale_names)


def seed_species_metadata(db: Session) -> dict[str, Species]:
    """Species code/scientific-name metadata comes from the raw IOTC file (it carries
    SPECIES_CODE/SPECIES_SCIENTIFIC per row); the processed table only has the display
    name, so we join back to the raw file for the full metadata.

    Only TARGET_SPECIES (the species preprocess.py actually keeps) are seeded -- the
    raw file reports ~20 species/bycatch categories, but this dashboard only forecasts
    skipjack and yellowfin tuna."""
    raw = pd.read_csv(DATA_RAW_DIR / "iotc_maldives_catch.csv")
    raw = raw[raw["SPECIES"].isin(TARGET_SPECIES)]
    meta = raw[["SPECIES", "SPECIES_CODE", "SPECIES_SCIENTIFIC"]].drop_duplicates("SPECIES")
    species_map = {}
    for _, row in meta.iterrows():
        # A handful of species (e.g. "Unclassified") have no SPECIES_SCIENTIFIC in the
        # source data -- pandas represents that as NaN (a float), which SQLAlchemy
        # cannot write into a String column, so it must become a real None.
        scientific = row["SPECIES_SCIENTIFIC"]
        scientific = None if pd.isna(scientific) else scientific
        species_map[row["SPECIES"]] = _get_or_create_species(
            db, row["SPECIES_CODE"], row["SPECIES"], scientific
        )
    db.commit()
    return species_map


def seed_catch_and_environmental(db: Session, regions: dict[str, Region]) -> None:
    """Upserts by natural key -- inserts rows that don't exist yet AND updates rows
    that do, whenever monthly_features.csv's value differs from what's stored. This
    matters beyond first seed: the Admin "Refresh Datasets" action re-runs preprocess.py
    and calls this again, and the processed table's values for an existing (region,
    species, month)/(region, month) key genuinely can change (e.g. a gap-filling rule
    change, or newer raw data correcting an earlier estimate) -- a plain
    insert-if-missing would silently keep serving the old value forever."""
    df = pd.read_csv(DATA_PROCESSED_DIR / "monthly_features.csv", parse_dates=["month"])
    species_by_name = {s.name: s for s in db.query(Species).all()}

    catch_added = 0
    catch_updated = 0
    for _, row in df.iterrows():
        region = regions.get(row["region"])
        species = species_by_name.get(row["species"])
        if region is None or species is None:
            continue
        catch_kg = float(row["catch_kg"])
        record = (
            db.query(CatchRecord)
            .filter_by(region_id=region.id, species_id=species.id, catch_month=row["month"].date())
            .first()
        )
        if record is None:
            db.add(
                CatchRecord(
                    region_id=region.id,
                    species_id=species.id,
                    catch_month=row["month"].date(),
                    catch_kg=catch_kg,
                )
            )
            catch_added += 1
        elif _float_changed(record.catch_kg, catch_kg):
            record.catch_kg = catch_kg
            catch_updated += 1
    db.commit()
    logger.info("catch_records: inserted %s, updated %s", catch_added, catch_updated)

    env_added = 0
    env_updated = 0
    env_df = df.drop_duplicates(subset=["region", "month"])
    for _, row in env_df.iterrows():
        region = regions.get(row["region"])
        if region is None:
            continue
        sst = None if pd.isna(row.get("sst")) else float(row["sst"])
        wind_speed = None if pd.isna(row.get("wind_speed")) else float(row["wind_speed"])
        salinity = None if pd.isna(row.get("salinity")) else float(row["salinity"])
        record = (
            db.query(EnvironmentalObservation)
            .filter_by(region_id=region.id, obs_month=row["month"].date())
            .first()
        )
        if record is None:
            db.add(
                EnvironmentalObservation(
                    region_id=region.id,
                    obs_month=row["month"].date(),
                    sst=sst,
                    wind_speed=wind_speed,
                    salinity=salinity,
                )
            )
            env_added += 1
        elif (
            _float_changed(record.sst, sst)
            or _float_changed(record.wind_speed, wind_speed)
            or _float_changed(record.salinity, salinity)
        ):
            record.sst, record.wind_speed, record.salinity = sst, wind_speed, salinity
            env_updated += 1
    db.commit()
    logger.info("environmental_observations: inserted %s, updated %s", env_added, env_updated)


def run() -> None:
    Base.metadata.create_all(bind=engine)  # no-op if Alembic already created everything
    db = SessionLocal()
    try:
        seed_users(db)
        regions = seed_regions(db)
        prune_non_target_species(db)
        seed_species_metadata(db)
        seed_catch_and_environmental(db, regions)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
