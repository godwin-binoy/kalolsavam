"""Smoke tests for the app after FullAuth migration."""
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


def test_login_endpoint_registered(client):
    r = client.post("/api/v1/auth/login",
                    json={"email": "ghost@example.com", "password": "wrong"})
    assert r.status_code in (400, 401, 403, 422)


def test_registration_blocked(client):
    r = client.post("/api/v1/auth/register",
                    json={"email": "x@y.z", "password": "shouldnotmatter1234"})
    assert r.status_code == 403
    assert r.json()["error"] == "registration_disabled"


def test_score_endpoint_unauthorized(client):
    r = client.post("/api/v1/live/score", json={"queue_item_id": 1, "judge_no": 1, "value": 85.5})
    assert r.status_code == 401


# ── /admin and /stagemaster trailing-slash routing ────────────────────────

def test_admin_bare_path_redirects(client):
    r = client.get("/admin", follow_redirects=False)
    assert r.status_code in (307, 308, 301, 302, 200)
    assert r.headers.get("location", "").endswith("/admin/")


def test_admin_trailing_slash_serves_panel(client):
    r = client.get("/admin/")
    assert r.status_code == 200
    assert "Admin Console" in r.text
    assert "/dashboard/js/admin.js" in r.text


def test_stagemaster_bare_path_redirects(client):
    r = client.get("/stagemaster", follow_redirects=False)
    assert r.status_code in (307, 308, 301, 302, 200)
    assert r.headers.get("location", "").endswith("/stagemaster/")


def test_stagemaster_trailing_slash_serves_panel(client):
    r = client.get("/stagemaster/")
    assert r.status_code == 200
    assert "Stage Control" in r.text
    assert "/dashboard/js/board.js" in r.text


def test_dashboard_assets_served(client):
    r = client.get("/dashboard/css/dashboard.css")
    assert r.status_code == 200
    assert ":root" in r.text

    r = client.get("/dashboard/js/api.js")
    assert r.status_code == 200
    assert "window.KalAPI" in r.text
