"""Smoke and workflow tests for the Kalolsavam backend."""
from __future__ import annotations

import json

from server.auth import hash_password


def _seed_user(db, email: str, password: str, role_name: str, stages: list[int]):
    now = db.now()
    db.ex(
        "INSERT INTO users(email, password_hash, role, stages, is_active, created_at, updated_at) "
        "VALUES (?,?,?,?,1,?,?)",
        (email.lower(), hash_password(password), role_name, json.dumps(stages), now, now),
    )


def _login(client, email: str, password: str):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r


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


def test_unknown_api_returns_404_json(client):
    r = client.get("/api/v1/does-not-exist")
    assert r.status_code == 404
    assert r.json()["error"] == "not_found"


def test_board_requires_auth(client):
    r = client.get("/api/v1/live/board")
    assert r.status_code == 401


def test_admin_requires_auth(client):
    r = client.get("/api/v1/admin/venues")
    assert r.status_code == 401


def test_advance_requires_auth(client):
    r = client.post(
        "/api/v1/live/advance",
        json={"venue_id": 1, "action": "START_NEXT"},
        headers={"Idempotency-Key": "test-key-1"},
    )
    assert r.status_code == 401


def test_login_endpoint_registered(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "ghost@example.com", "password": "wrong"},
    )
    assert r.status_code == 401
    fails = client.app.state.db.one(
        "SELECT COUNT(*) c FROM auth_audit WHERE event = 'login_fail'"
    )["c"]
    assert fails == 1


def test_login_rate_limiting(client):
    for _ in range(8):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "victim@example.com", "password": "wrong"},
        )
        assert r.status_code == 401
    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "victim@example.com", "password": "wrong"},
    )
    assert blocked.status_code == 429


def test_registration_blocked(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "x@y.z", "password": "shouldnotmatter1234"},
    )
    assert r.status_code == 403
    assert r.json()["error"] == "registration_disabled"


def test_score_endpoint_unauthorized(client):
    r = client.post("/api/v1/live/score", json={"queue_item_id": 1, "judge_no": 1, "value": 85.5})
    assert r.status_code == 401


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


def test_bearer_auth_and_session_revocation(client):
    db = client.app.state.db
    _seed_user(db, "admin@example.com", "StrongPass1234!", "admin", [])
    _seed_user(db, "staff@example.com", "StaffPass1234!", "stagemaster", [])

    login_admin = _login(client, "admin@example.com", "StrongPass1234!")
    admin_tok = login_admin.json()["access_token"]
    client.cookies.clear()

    # Admin self-disable is rejected
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_tok}"})
    assert me.status_code == 200
    self_id = me.json()["id"]
    assert client.post(
        f"/api/v1/admin/users/{self_id}/disable",
        headers={"Authorization": f"Bearer {admin_tok}"},
    ).status_code == 400

    # Staff Bearer login + immediate revocation on disable
    staff_login = _login(client, "staff@example.com", "StaffPass1234!")
    staff_tok = staff_login.json()["access_token"]
    client.cookies.clear()

    assert client.get(
        "/api/v1/live/board",
        headers={"Authorization": f"Bearer {staff_tok}"},
    ).status_code == 200

    users = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {admin_tok}"},
    ).json()["users"]
    staff_id = next(u["id"] for u in users if u["email"] == "staff@example.com")

    assert client.post(
        f"/api/v1/admin/users/{staff_id}/disable",
        headers={"Authorization": f"Bearer {admin_tok}"},
    ).status_code == 200

    assert client.get(
        "/api/v1/live/board",
        headers={"Authorization": f"Bearer {staff_tok}"},
    ).status_code == 401


def test_full_admin_and_stage_workflow(client):
    db = client.app.state.db
    _seed_user(db, "admin@example.com", "StrongPass1234!", "admin", [])
    _login(client, "admin@example.com", "StrongPass1234!")

    r = client.post("/api/v1/admin/venues", json={"name": "   ", "kind": "stage", "active": True})
    assert r.status_code == 422

    v = client.post("/api/v1/admin/venues", json={"name": "Stage 1", "kind": "stage", "active": True}).json()
    c = client.post("/api/v1/admin/categories", json={"name": "HS General", "group": "HS"}).json()
    e = client.post(
        "/api/v1/admin/events",
        json={"code": "101", "title": "Bharathanatyam", "category_id": c["id"], "venue_id": v["id"]},
    ).json()

    q1 = client.post(
        "/api/v1/admin/queue",
        json={"venue_id": v["id"], "event_id": e["id"], "school": "School A", "student_name": "Asha", "roll": "101"},
    ).json()
    q2 = client.post(
        "/api/v1/admin/queue",
        json={"venue_id": v["id"], "event_id": e["id"], "school": "School B", "student_name": "Binu", "roll": "102"},
    ).json()

    r = client.post("/api/v1/live/advance", json={"venue_id": v["id"], "action": "START_NEXT"}, headers={"Idempotency-Key": "k1"})
    assert r.status_code == 200 and r.json()["item_id"] == q1["id"]

    r = client.post("/api/v1/live/advance", json={"venue_id": v["id"], "action": "COMPLETE_CURRENT"}, headers={"Idempotency-Key": "k2"})
    assert r.status_code == 200 and r.json()["status"] == "COMPLETE"

    r = client.post("/api/v1/live/advance", json={"venue_id": v["id"], "action": "START_NEXT"}, headers={"Idempotency-Key": "k3"})
    assert r.status_code == 200 and r.json()["item_id"] == q2["id"]

    r = client.post(
        "/api/v1/live/advance",
        json={"venue_id": v["id"], "action": "RECALL", "item_id": q1["id"]},
        headers={"Idempotency-Key": "k4"},
    )
    assert r.status_code == 200 and r.json()["item_id"] == q1["id"]

    paused_q2 = db.one("SELECT status, completed_at FROM queue_items WHERE id = ?", (q2["id"],))
    assert paused_q2["status"] == "PAUSED"
    assert paused_q2["completed_at"] is None

    r = client.post("/api/v1/live/score", json={"queue_item_id": q1["id"], "judge_no": 1, "value": 92.5})
    assert r.status_code == 200 and r.json()["total"] == 92.5

    dash = client.get("/api/v1/admin/dashboard")
    assert dash.status_code == 200
    assert dash.json()["overall"]["scores_entered"] == 1
    assert dash.json()["top_schools"][0]["school"] == "School A"

    sched = client.get(f"/api/v1/public/schedule?venue_id={v['id']}")
    assert sched.status_code == 200
    assert len(sched.json()["events"]) == 1


def test_cors_and_cross_origin_cookies(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from server.app import create_app
    from server.config import Settings
    from server.db import Database

    db_path = tmp_path / "cors_k.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://kalolsavam.pages.dev")
    monkeypatch.setenv("SECRET_KEY", "super-secret-test-key-01234567890123456789")

    db = Database(db_path)
    app = create_app(Settings(), db)
    with TestClient(app, base_url="https://api.example.com") as c:
        _seed_user(db, "admin@example.com", "StrongPass1234!", "admin", [])

        pre = c.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "https://abc123.kalolsavam.pages.dev",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type, Authorization",
            },
        )
        assert pre.status_code == 200
        assert pre.headers.get("access-control-allow-origin") == "https://abc123.kalolsavam.pages.dev"
        assert pre.headers.get("access-control-allow-credentials") == "true"

        bad = c.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "StrongPass1234!"},
            headers={"Origin": "https://evil.example.org"},
        )
        assert bad.status_code == 403
        assert bad.json()["error"] == "origin_mismatch"

        ok = c.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "StrongPass1234!"},
            headers={"Origin": "https://kalolsavam.pages.dev"},
        )
        assert ok.status_code == 200
        assert ok.headers.get("access-control-allow-origin") == "https://kalolsavam.pages.dev"
        cookies = " ".join(ok.headers.get_list("set-cookie")).lower()
        assert "samesite=none" in cookies
        assert "secure" in cookies
