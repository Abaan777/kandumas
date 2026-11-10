"""Shared pytest fixtures for the backend test suite.

Tests run against a throwaway SQLite file (not the real MySQL database) so they are
fast, isolated, and safe to run without a database server. The DATABASE_URL env var
must be set *before* app.core.database (and anything that imports it) is imported,
since Settings()/the SQLAlchemy engine are both constructed at import time.
"""
from __future__ import annotations

import os
from pathlib import Path

TEST_DB_PATH = Path(__file__).parent / "test_kandumas.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"

import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.main import app
from app.models.models import Region, Species, User


@pytest.fixture(scope="session", autouse=True)
def _test_database():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session", autouse=True)
def seeded_users():
    """The three demo accounts (fisherman1/officer1/admin1), matching seed.py."""
    session = SessionLocal()
    accounts = [
        ("fisherman1", "Fisherman123!", "fisherman"),
        ("officer1", "Officer123!", "officer"),
        ("admin1", "Admin123!", "admin"),
    ]
    try:
        for username, password, role in accounts:
            if session.query(User).filter_by(username=username).first() is None:
                session.add(User(username=username, password_hash=hash_password(password), role=role))
        session.commit()
    finally:
        session.close()
    return {username: password for username, password, _ in accounts}


@pytest.fixture(scope="session", autouse=True)
def seeded_regions_species():
    """A couple of regions and the two target species (see preprocess.py TARGET_SPECIES)."""
    session = SessionLocal()
    try:
        if session.query(Region).count() == 0:
            session.add_all(
                [
                    Region(name="North Maldives", lat_center=5.5, lon_center=73.0),
                    Region(name="South Maldives", lat_center=-0.5, lon_center=73.0),
                ]
            )
        if session.query(Species).count() == 0:
            session.add_all(
                [
                    Species(code="SKJ", name="Skipjack tuna", scientific_name="Katsuwonus pelamis"),
                    Species(code="YFT", name="Yellowfin tuna", scientific_name="Thunnus albacares"),
                ]
            )
        session.commit()
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


def _login(client: TestClient, username: str, password: str) -> str:
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    resp.raise_for_status()
    return resp.json()["access_token"]


@pytest.fixture
def fisherman_token(client, seeded_users):
    return _login(client, "fisherman1", seeded_users["fisherman1"])


@pytest.fixture
def officer_token(client, seeded_users):
    return _login(client, "officer1", seeded_users["officer1"])


@pytest.fixture
def admin_token(client, seeded_users):
    return _login(client, "admin1", seeded_users["admin1"])


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
