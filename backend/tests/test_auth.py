"""UC: login, self-registration, and forgot/reset password."""
from tests.conftest import auth_header


def test_login_succeeds_for_each_demo_role(client, seeded_users):
    for username, password in seeded_users.items():
        resp = client.post("/api/auth/login", json={"username": username, "password": password})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["username"] == username
        assert body["access_token"]
        assert body["token_type"] == "bearer"


def test_login_fails_with_wrong_password(client, seeded_users):
    resp = client.post("/api/auth/login", json={"username": "fisherman1", "password": "wrong-password"})
    assert resp.status_code == 401


def test_login_fails_for_unknown_user(client):
    resp = client.post("/api/auth/login", json={"username": "nobody", "password": "whatever"})
    assert resp.status_code == 401


def test_protected_endpoint_rejects_missing_token(client):
    resp = client.get("/api/meta/regions")
    assert resp.status_code == 401


def test_protected_endpoint_rejects_garbage_token(client):
    resp = client.get("/api/meta/regions", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


# --- Registration -----------------------------------------------------------------


def test_register_creates_a_fisherman_account_and_logs_in(client):
    resp = client.post("/api/auth/register", json={"username": "newuser1", "password": "StrongPass1!"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["username"] == "newuser1"
    assert body["role"] == "fisherman"  # self-registration is always fisherman, never officer/admin
    assert body["access_token"]

    # The new account can immediately log back in with the same credentials.
    login_resp = client.post("/api/auth/login", json={"username": "newuser1", "password": "StrongPass1!"})
    assert login_resp.status_code == 200


def test_register_rejects_duplicate_username(client, seeded_users):
    resp = client.post("/api/auth/register", json={"username": "fisherman1", "password": "StrongPass1!"})
    assert resp.status_code == 409


def test_register_rejects_short_password(client):
    resp = client.post("/api/auth/register", json={"username": "someoneelse", "password": "short"})
    assert resp.status_code == 400


def test_register_rejects_short_username(client):
    resp = client.post("/api/auth/register", json={"username": "ab", "password": "StrongPass1!"})
    assert resp.status_code == 400


# --- Forgot / reset password --------------------------------------------------------


def _register(client, username: str, password: str = "StrongPass1!") -> None:
    resp = client.post("/api/auth/register", json={"username": username, "password": password})
    assert resp.status_code == 201, resp.text


def test_forgot_password_returns_generic_message_for_unknown_user(client):
    resp = client.post("/api/auth/forgot-password", json={"username": "nobody-here"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reset_token"] is None
    assert body["reset_url"] is None


def test_forgot_password_issues_a_usable_token_for_a_real_user(client):
    # Uses a throwaway registered user rather than one of the shared seeded demo
    # accounts, so this test can't leave fisherman1/officer1/admin1 in a different
    # password state for other tests in the session.
    _register(client, "forgot_pw_user", "OriginalPass1!")

    resp = client.post("/api/auth/forgot-password", json={"username": "forgot_pw_user"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["reset_token"]
    assert "reset-password?token=" in body["reset_url"]

    reset_resp = client.post(
        "/api/auth/reset-password", json={"token": body["reset_token"], "new_password": "BrandNewPass1!"}
    )
    assert reset_resp.status_code == 200

    # Old password no longer works; new one does.
    assert client.post("/api/auth/login", json={"username": "forgot_pw_user", "password": "OriginalPass1!"}).status_code == 401
    assert client.post("/api/auth/login", json={"username": "forgot_pw_user", "password": "BrandNewPass1!"}).status_code == 200


def test_reset_password_token_is_single_use(client):
    _register(client, "single_use_token_user")
    token = client.post("/api/auth/forgot-password", json={"username": "single_use_token_user"}).json()["reset_token"]

    first = client.post("/api/auth/reset-password", json={"token": token, "new_password": "FirstUse123!"})
    assert first.status_code == 200

    second = client.post("/api/auth/reset-password", json={"token": token, "new_password": "SecondUse123!"})
    assert second.status_code == 400


def test_reset_password_rejects_unknown_token(client):
    resp = client.post("/api/auth/reset-password", json={"token": "not-a-real-token", "new_password": "WhateverPass1!"})
    assert resp.status_code == 400


def test_reset_password_rejects_short_password(client):
    _register(client, "short_pw_reset_user")
    token = client.post("/api/auth/forgot-password", json={"username": "short_pw_reset_user"}).json()["reset_token"]
    reset_resp = client.post("/api/auth/reset-password", json={"token": token, "new_password": "short"})
    assert reset_resp.status_code == 400
    # The token must still be unused -- validation failed before the token was looked
    # up/consumed, so it should still be valid for a real attempt.
    assert client.post("/api/auth/reset-password", json={"token": token, "new_password": "LongEnoughPass1!"}).status_code == 200
