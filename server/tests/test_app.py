"""Smoke and workflow tests for the Kalolsavam backend."""
from __future__ import annotations

import asyncio
import json

from argon2 import PasswordHasher
from sqlmodel import select
from server.database import make_engine, make_session_maker
from server.models import Role, User


async def _seed_user(db_path: str, email: str, password: str, role_name: str, stages: list[int]):
    engine = make_engine(db_path)
    session_maker = make_session_maker(engine)
    ph = PasswordHasher()
    try:
        async with session_maker() as session:
            role = (await session.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
            if not role:
                role = Role(name=role_name)
                session.add(role)
                await session.commit()
                await session.refresh(role)
            u = User(
                email=email.strip().lower(),
                hashed_password=ph.hash(password),
                is_active=True,
                is_verified=True,
                stages=json.dumps(stages),
            )
            u.roles.append(role)
            session.add(u)
            await session.commit()
    finally:
        await engine.dispose()


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
    assert r.status_code in (400, 401, 422)


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


def test_full_admin_and_stage_workflow(client):
    cfg = client.app.state.cfg
    db = client.app.state.db
    asyncio.run(_seed_user(cfg.db_path, "admin@example.com", "StrongPass1234!", "admin", []))
    login_res = _login(client, "admin@example.com", "StrongPass1234!")
    tok = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    r = client.post("/api/v1/admin/venues", json={"name": "   ", "kind": "stage", "active": True}, headers=headers)
    assert r.status_code == 422

    v = client.post("/api/v1/admin/venues", json={"name": "Stage 1", "kind": "stage", "slug": "stage-1", "active": True}, headers=headers).json()
    c = client.post("/api/v1/admin/categories", json={"name": "HS General", "group": "HS"}, headers=headers).json()
    e = client.post(
        "/api/v1/admin/events",
        json={"code": "101", "title": "Bharathanatyam", "category_id": c["id"], "venue_id": v["id"]},
        headers=headers,
    ).json()

    q1 = client.post(
        "/api/v1/admin/queue",
        json={"venue_id": v["id"], "event_id": e["id"], "school": "School A", "student_name": "Asha", "roll": "101"},
        headers=headers,
    ).json()
    q2 = client.post(
        "/api/v1/admin/queue",
        json={"venue_id": v["id"], "event_id": e["id"], "school": "School B", "student_name": "Binu", "roll": "102"},
        headers=headers,
    ).json()

    r = client.post("/api/v1/live/advance", json={"venue_id": v["id"], "action": "START_NEXT"}, headers={**headers, "Idempotency-Key": "k1"})
    assert r.status_code == 200 and r.json()["item_id"] == q1["id"]

    r = client.post("/api/v1/live/advance", json={"venue_id": v["id"], "action": "COMPLETE_CURRENT"}, headers={**headers, "Idempotency-Key": "k2"})
    assert r.status_code == 200 and r.json()["status"] == "COMPLETE"

    r = client.post("/api/v1/live/advance", json={"venue_id": v["id"], "action": "START_NEXT"}, headers={**headers, "Idempotency-Key": "k3"})
    assert r.status_code == 200 and r.json()["item_id"] == q2["id"]

    r = client.post(
        "/api/v1/live/advance",
        json={"venue_id": v["id"], "action": "RECALL", "item_id": q1["id"]},
        headers={**headers, "Idempotency-Key": "k4"},
    )
    assert r.status_code == 200 and r.json()["item_id"] == q1["id"]

    paused_q2 = db.one("SELECT status, completed_at FROM queue_items WHERE id = ?", (q2["id"],))
    assert paused_q2["status"] == "PAUSED"
    assert paused_q2["completed_at"] is None

    r = client.post("/api/v1/live/score", json={"queue_item_id": q1["id"], "judge_no": 1, "value": 92.5}, headers=headers)
    assert r.status_code == 200 and r.json()["total"] == 92.5

    dash = client.get("/api/v1/admin/dashboard", headers=headers)
    assert dash.status_code == 200
    assert dash.json()["overall"]["scores_entered"] == 1
    assert dash.json()["top_schools"][0]["school"] == "School A"

    sched = client.get(f"/api/v1/public/schedule?venue_id={v['id']}")
    assert sched.status_code == 200
    assert len(sched.json()["events"]) == 1


def test_cors_and_preflight(client):
    pre = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://testserver",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Authorization",
        },
    )
    assert pre.status_code == 200
    assert pre.headers.get("access-control-allow-origin") == "http://testserver"
    assert "authorization" in pre.headers.get("access-control-allow-headers", "").lower()
