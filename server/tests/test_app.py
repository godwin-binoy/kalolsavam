"""Smoke, security, and workflow tests for the Kalolsavam backend."""
from __future__ import annotations

import asyncio
import json

from argon2 import PasswordHasher
from sqlmodel import select

from server.database import make_engine, make_session_maker
from server.deps import _RATE_BUCKETS, derive_worker_token
from server.models import Role, User

_MIN_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc`\x00\x00"
    b"\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)
_MIN_WEBP = b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x00\x10\x00\x00\x9d\x01*\x01\x00\x01\x00\x02\x004\x25\xa4\x00\x03p\x00\xfe\xfb\x94\x00\x00"


async def _seed_user(db_path: str, email: str, password: str, role_name: str, stages: list[int]):
    engine = make_engine(db_path)
    session_maker = make_session_maker(engine)
    ph = PasswordHasher()
    try:
        async with session_maker() as session:
            role = (await session.exec(select(Role).where(Role.name == role_name))).first()
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
    assert client.get("/api/v1/live/board").status_code == 401


def test_admin_requires_auth(client):
    assert client.get("/api/v1/admin/venues").status_code == 401


def test_advance_requires_auth(client):
    r = client.post(
        "/api/v1/live/advance",
        json={"venue_id": 1, "action": "START_NEXT"},
        headers={"Idempotency-Key": "test-key-1"},
    )
    assert r.status_code == 401


def test_login_endpoint_registered(client):
    r = client.post("/api/v1/auth/login", json={"email": "ghost@example.com", "password": "wrong"})
    assert r.status_code in (400, 401, 422)


def test_registration_blocked(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"email": "x@y.z", "password": "shouldnotmatter1234"},
    )
    assert r.status_code == 403
    assert r.json()["error"] == "registration_disabled"


def test_cors_preflight(client):
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


def test_full_admin_workflow_and_security(client):
    cfg = client.app.state.cfg
    asyncio.run(_seed_user(cfg.db_path, "admin@example.com", "StrongPass1234!", "admin", []))
    tok = _login(client, "admin@example.com", "StrongPass1234!").json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert client.post(f"/api/v1/admin/users/{me['id']}/disable", headers=headers).status_code == 400

    assert client.post("/api/v1/admin/venues", json={"name": "   ", "kind": "stage"}, headers=headers).status_code == 422
    v = client.post(
        "/api/v1/admin/venues",
        json={"name": "Stage 1", "kind": "stage", "slug": "stage-1", "active": True},
        headers=headers,
    ).json()
    assert v["slug"] == "stage-1"

    c = client.post("/api/v1/admin/categories", json={"name": "HS General", "group": "HS"}, headers=headers).json()
    client.post(
        "/api/v1/admin/events",
        json={"code": "101", "title": "Bharathanatyam", "category_id": c["id"], "venue_id": v["id"]},
        headers=headers,
    )

    # Create participants with formula-like characters and enqueue via registry entries
    p1 = client.post("/api/v1/admin/participants", json={
        "register_no": "10001", "name": "+Asha", "school_name": "=CMD()", "school_code": "22001", "class": 9,
    }, headers=headers).json()
    e1 = client.post(f"/api/v1/admin/participants/{p1['id']}/entries", json={
        "item_code": "101", "venue_id": v["id"], "venue_name": v["name"], "perf_date": "2026-11-14",
    }, headers=headers).json()

    p2 = client.post("/api/v1/admin/participants", json={
        "register_no": "10002", "name": "Binu", "school_name": "School B", "school_code": "22002", "class": 10,
    }, headers=headers).json()
    e2 = client.post(f"/api/v1/admin/participants/{p2['id']}/entries", json={
        "item_code": "101", "venue_id": v["id"], "venue_name": v["name"], "perf_date": "2026-11-14",
    }, headers=headers).json()

    q1 = client.post(
        "/api/v1/admin/queue",
        json={"venue_id": v["id"], "participant_entry_id": e1["id"], "chest_no": "C101"},
        headers=headers,
    ).json()
    q2 = client.post(
        "/api/v1/admin/queue",
        json={"venue_id": v["id"], "participant_entry_id": e2["id"], "chest_no": "C102"},
        headers=headers,
    ).json()

    csv_res = client.get("/api/v1/admin/export/participants.csv", headers=headers)
    assert csv_res.status_code == 200
    assert "'=CMD()" in csv_res.text and "'+Asha" in csv_res.text

    # Stage run-of-show controls: START_NEXT -> PAUSE pins item at top of board
    r_start = client.post(
        "/api/v1/live/advance",
        json={"venue_id": v["id"], "action": "START_NEXT"},
        headers={**headers, "Idempotency-Key": "k1"},
    )
    assert r_start.status_code == 200
    assert r_start.json()["item_id"] == q1["id"]

    r_pause = client.post(
        "/api/v1/live/advance",
        json={"venue_id": v["id"], "action": "PAUSE"},
        headers={**headers, "Idempotency-Key": "k2"},
    )
    assert r_pause.status_code == 200

    board = client.get("/api/v1/live/board", headers=headers).json()["board"]
    assert len(board) == 1
    assert board[0]["items"][0]["status"] == "PAUSED"
    assert board[0]["items"][0]["id"] == q1["id"]
    assert board[0]["items"][0]["chest_no"] == "C101"
    assert board[0]["items"][1]["id"] == q2["id"]

    # Public status reflects live chest_no and school_name
    pub_status = client.get("/api/v1/public/status").json()
    assert pub_status["venues"][0]["now"]["chest_no"] == "C101"
    assert pub_status["venues"][0]["now"]["school"] == "=CMD()"

    assert client.get("/api/v1/admin/dashboard", headers=headers).status_code == 200
    assert len(client.get("/api/v1/admin/audit", headers=headers).json()["items"]) > 0


def test_participant_registry_smoke(client):
    cfg = client.app.state.cfg
    asyncio.run(_seed_user(cfg.db_path, "reg@example.com", "StrongPass1234!", "admin", []))
    tok = _login(client, "reg@example.com", "StrongPass1234!").json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}

    r = client.post("/api/v1/admin/participants", json={
        "register_no": "10342", "name": "Asha", "school_name": "Sacred Heart HSS", "school_code": "22001", "class": 9,
    }, headers=h)
    assert r.status_code == 200, r.text
    pid = r.json()["id"]

    r = client.post(f"/api/v1/admin/participants/{pid}/entries", json={
        "item_code": "101", "venue_id": 3, "venue_name": "GLPS Mala", "perf_date": "2026-11-14",
    }, headers=h)
    assert r.status_code == 200, r.text

    r = client.get("/api/v1/admin/participants", headers=h)
    assert r.json()["total"] == 1
    assert r.json()["participants"][0]["entry_count"] == 1

    assert client.delete(f"/api/v1/admin/participants/{pid}", headers=h).status_code == 200
    assert client.get("/api/v1/admin/participants", headers=h).json()["total"] == 0
    assert client.get("/api/v1/public/dashboard").json()["overall"]["participants"] == 0


def test_worker_auth_isolation(client):
    cfg = client.app.state.cfg
    asyncio.run(_seed_user(cfg.db_path, "adm_w@example.com", "StrongPass1234!", "admin", []))
    adm_tok = _login(client, "adm_w@example.com", "StrongPass1234!").json()["access_token"]

    obs_tok = derive_worker_token(cfg.secret_key, "obs")
    photo_tok = derive_worker_token(cfg.secret_key, "photos")

    # Missing, raw secret, user JWT, or wrong-scope worker token are all rejected
    for bad_hdr in (
        {},
        {"X-Worker-Token": ""},
        {"X-Worker-Token": cfg.secret_key},
        {"Authorization": f"Bearer {adm_tok}"},
        {"X-Worker-Token": photo_tok},
    ):
        assert client.get("/api/v1/internal/backup", headers=bad_hdr).status_code == 403

    assert client.post("/api/v1/photos/internal/jobs/pull", headers={"X-Worker-Token": obs_tok}).status_code == 403

    # Valid obs worker token succeeds
    bak = client.get("/api/v1/internal/backup", headers={"X-Worker-Token": obs_tok})
    assert bak.status_code == 200
    assert bak.content.startswith(b"SQLite format 3\x00")
    assert client.get("/api/v1/internal/audit-export", headers={"X-Worker-Token": obs_tok}).status_code == 200


def test_photo_lifecycle_and_privacy_gate(client):
    cfg = client.app.state.cfg
    asyncio.run(_seed_user(cfg.db_path, "adm_p@example.com", "StrongPass1234!", "admin", []))
    asyncio.run(_seed_user(cfg.db_path, "sm1@example.com", "StrongPass1234!", "stagemaster", [1]))
    asyncio.run(_seed_user(cfg.db_path, "dw1@example.com", "StrongPass1234!", "dataworker", []))

    adm_h = {"Authorization": f"Bearer {_login(client, 'adm_p@example.com', 'StrongPass1234!').json()['access_token']}"}
    sm_h = {"Authorization": f"Bearer {_login(client, 'sm1@example.com', 'StrongPass1234!').json()['access_token']}"}
    dw_h = {"Authorization": f"Bearer {_login(client, 'dw1@example.com', 'StrongPass1234!').json()['access_token']}"}

    v1 = client.post("/api/v1/admin/venues", json={"name": "Stage 1", "kind": "stage", "active": True}, headers=adm_h).json()
    v2 = client.post("/api/v1/admin/venues", json={"name": "Stage 2", "kind": "stage", "active": True}, headers=adm_h).json()
    client.post("/api/v1/admin/events", json={"code": "201", "title": "Mohiniyattam", "venue_id": v1["id"]}, headers=adm_h)

    part = client.post("/api/v1/admin/participants", json={
        "register_no": "54321", "name": "Meera", "school_name": "GHSS Mala", "school_code": "22009", "class": 11,
    }, headers=adm_h).json()
    entry = client.post(f"/api/v1/admin/participants/{part['id']}/entries", json={
        "item_code": "201", "venue_id": v1["id"], "venue_name": v1["name"], "perf_date": "2026-11-14",
    }, headers=adm_h).json()
    qi = client.post("/api/v1/admin/queue", json={"venue_id": v1["id"], "participant_entry_id": entry["id"]}, headers=adm_h).json()

    # Dataworker cannot access admin or live endpoints
    assert client.get("/api/v1/admin/venues", headers=dw_h).status_code == 403
    assert client.get("/api/v1/live/board", headers=dw_h).status_code == 403

    # Stagemaster stage check on photo batches
    assert client.post(
        "/api/v1/photos/batches",
        json={"queue_item_id": qi["id"], "venue_id": v2["id"], "workflow": "bulk"},
        headers=sm_h,
    ).status_code == 403

    b = client.post(
        "/api/v1/photos/batches",
        json={"queue_item_id": qi["id"], "venue_id": v1["id"], "workflow": "bulk"},
        headers=sm_h,
    )
    assert b.status_code == 200
    bid = b.json()["batch_id"]

    # Reject SVG/HTML disguise upload
    bad_up = client.post(
        f"/api/v1/photos/batches/{bid}/upload",
        data={"kind": "stage"},
        files={"file": ("evil.jpg", b"<svg onload=alert(1)>", "image/jpeg")},
        headers=sm_h,
    )
    assert bad_up.status_code == 400

    slip_id = client.post(
        f"/api/v1/photos/batches/{bid}/upload",
        data={"kind": "slip"},
        files={"file": ("slip.png", _MIN_PNG, "image/png")},
        headers=sm_h,
    ).json()["asset_id"]

    stage_id = client.post(
        f"/api/v1/photos/batches/{bid}/upload",
        data={"kind": "stage"},
        files={"file": ("stage.png", _MIN_PNG, "image/png")},
        headers=sm_h,
    ).json()["asset_id"]

    # Public cannot read staff endpoint or unsigned/tampered asset URL
    assert client.get(f"/api/v1/photos/staff/assets/{slip_id}/view").status_code == 401
    assert client.get(f"/api/v1/photos/assets/{stage_id}/view", params={"exp": 9999999999, "sig": "deadbeef"}).status_code == 403

    # Dataworker searches participant, views slip via staff route, assigns & publishes
    search = client.get("/api/v1/photos/participants/search", params={"q": "543"}, headers=dw_h)
    assert search.status_code == 200
    assert search.json()["participants"][0]["entries"][0]["id"] == entry["id"]
    assert client.get(f"/api/v1/photos/staff/assets/{slip_id}/view", headers=dw_h).status_code == 200

    assign = client.post(
        "/api/v1/photos/assign",
        json={"asset_id": stage_id, "participant_entry_ids": [entry["id"]]},
        headers=dw_h,
    )
    assert assign.status_code == 200 and assign.json()["batch_id"] == bid

    # Unpublished batch returns no photos on public lookup
    pre_pub = client.post("/api/v1/photos/public/lookup", json={"register_no": "54321", "name": "meera"})
    assert pre_pub.status_code == 200 and pre_pub.json()["photos"] == []

    # Photo worker optimizes stage photo without stealing batch from Data Worker
    pw_h = {"X-Worker-Token": derive_worker_token(cfg.secret_key, "photos")}
    job = client.post("/api/v1/photos/internal/jobs/pull", headers=pw_h).json()["job"]
    assert job["id"] == stage_id
    assert client.get(f"/api/v1/photos/internal/assets/{stage_id}/raw", headers=pw_h).status_code == 200
    assert client.post(
        f"/api/v1/photos/internal/jobs/{stage_id}/complete",
        files={"file": ("out.webp", _MIN_WEBP, "image/webp")},
        headers=pw_h,
    ).status_code == 200
    assert client.post("/api/v1/photos/internal/jobs/pull", headers=pw_h).json()["job"] is None

    # Publish & verify signed public lookup + download
    assert client.post(f"/api/v1/photos/batches/{bid}/publish", headers=dw_h).status_code == 200
    assert client.post("/api/v1/photos/public/lookup", json={"register_no": "54321", "name": "Wrong"}).status_code == 404

    pub = client.post("/api/v1/photos/public/lookup", json={"register_no": "54321", "name": "meera"})
    assert pub.status_code == 200
    photos = pub.json()["photos"]
    assert len(photos) == 1
    assert photos[0]["entries"] == ["201"]

    view_r = client.get(photos[0]["url"])
    assert view_r.status_code == 200
    assert view_r.content == _MIN_WEBP
    dl_r = client.get(photos[0]["url"] + "&dl=1")
    assert dl_r.status_code == 200
    assert "attachment" in dl_r.headers.get("content-disposition", "")


def test_rate_limiting(client):
    _RATE_BUCKETS.clear()
    try:
        for _ in range(12):
            r = client.post("/api/v1/photos/public/lookup", json={"register_no": "99999", "name": "Nobody"})
            assert r.status_code == 404
        blocked = client.post("/api/v1/photos/public/lookup", json={"register_no": "99999", "name": "Nobody"})
        assert blocked.status_code == 429
    finally:
        _RATE_BUCKETS.clear()
