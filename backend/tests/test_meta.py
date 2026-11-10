"""Lookup endpoints the frontend's FilterBar uses (region/species dropdowns)."""
from tests.conftest import auth_header


def test_list_regions(client, fisherman_token):
    resp = client.get("/api/meta/regions", headers=auth_header(fisherman_token))
    assert resp.status_code == 200
    names = {r["name"] for r in resp.json()}
    assert {"North Maldives", "South Maldives"}.issubset(names)


def test_list_species_only_contains_target_species(client, fisherman_token):
    """The species dropdown should only ever offer Skipjack/Yellowfin tuna -- see
    preprocess.py TARGET_SPECIES and seed.py's prune_non_target_species()."""
    resp = client.get("/api/meta/species", headers=auth_header(fisherman_token))
    assert resp.status_code == 200
    names = {s["name"] for s in resp.json()}
    assert names == {"Skipjack tuna", "Yellowfin tuna"}
