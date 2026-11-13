"""Smoke and workflow tests for the Kalolsavam backend."""
from __future__ import annotations

import asyncio
import json

from argon2 import PasswordHasher
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import select

from server.auth import Role, User


async def _seed_user(auth_db_path: str, email: str, password: str, role_name: str, stages: list[int]):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{auth_db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_maker() as session:
            role = (await session.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
            if not role:
                role = Role(name=role_name)
                session.add(role)
                await session.commit()
                await session.refresh(role)
            u = User(
                email=email,
                hashed_password=PasswordHasher().hash(password),
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
    assert r.status_code in (400, 401, 403, 422)


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
    asyncio.run(_seed_user(cfg.auth_db_path, "admin@example.com", "StrongPass1234!", "admin", []))
    _login(client, "admin@example.com", "StrongPass1234!")

    # Reject blank venue name
    r = client.post("/api/v1/admin/venues", json={"name": "   ", "kind": "stage", "active": True})
    assert r.status_code == 422

    # Create venue, category, event, and two queue items
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

    # Start q1 -> Complete q1 -> Start q2 -> Recall q1 (pauses q2 without setting completed_at)
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

    # Score q1 and verify leaderboard & dashboard
    r = client.post("/api/v1/live/score", json={"queue_item_id": q1["id"], "judge_no": 1, "value": 92.5})
    assert r.status_code == 200 and r.json()["total"] == 92.5

    dash = client.get("/api/v1/admin/dashboard")
    assert dash.status_code == 200
    assert dash.json()["overall"]["scores_entered"] == 1
    assert dash.json()["top_schools"][0]["school"] == "School A"

    # Public schedule supports venue_id filtering
    sched = client.get(f"/api/v1/public/schedule?venue_id={v['id']}")
    assert sched.status_code == 200
    assert len(sched.json()["events"]) == 1
