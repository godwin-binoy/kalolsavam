"""Minimal smoke tests for the whole app."""
from __future__ import annotations


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_readyz(client):
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_public_status_empty(client):
    r = client.get("/api/v1/public/status")
    assert r.status_code == 200
    assert "venues" in r.json()


def test_public_schedule_empty(client):
    r = client.get("/api/v1/public/schedule")
    assert r.status_code == 200
    assert r.json()["events"] == []


def test_login_no_user(client):
    r = client.post("/api/v1/auth/login",
                    json={"username": "ghost", "password": "wrong"})
    assert r.status_code == 401


def test_board_requires_auth(client):
    r = client.get("/api/v1/live/board")
    assert r.status_code == 401


def test_admin_requires_auth(client):
    r = client.get("/api/v1/admin/venues")
    assert r.status_code == 401


def test_advance_requires_auth(client):
    r = client.post("/api/v1/live/advance",
                    json={"venue_id": 1, "action": "START_NEXT"},
                    headers={"Idempotency-Key": "test-key-1"})
    assert r.status_code == 401


def test_admin_first_login_triggers_totp_setup(client):
    from server.security import hash_password
    db = client.app.state.db
    salt, phash = hash_password("strong-test-password-1234")
    db.ex(
        "INSERT INTO users(username, role, pwd_salt, pwd_hash, totp_required, "
        " stages, created_at, updated_at) VALUES (?, 'admin', ?, ?, 1, '[]', ?, ?)",
        ("admin", salt, phash, db.now(), db.now()),
    )
    r = client.post("/api/v1/auth/login",
                    json={"username": "admin", "password": "strong-test-password-1234"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("error") == "totp_setup_required"
    assert "uri" in body
