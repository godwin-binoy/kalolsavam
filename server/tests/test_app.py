"""End-to-end smoke, security, auth-rotation, photo, and worker tests."""
from __future__ import annotations

import json
from pathlib import Path

from server.auth import _RATE_BUCKETS, derive_worker_token, ph
from server.db import Database

_MIN_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc`\x00\x00"
    b"\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)
_MIN_WEBP = b"RIFF\x1a\x00\x00\x00WEBPVP8 \x0e\x00\x00\x00\x10\x00\x00\x9d\x01*\x01\x00\x01\x00\x02\x004\x25\xa4\x00\x03p\x00\xfe\xfb\x94\x00\x00"


def _seed_user(db_path: str, email: str, password: str, role: str, stages: list[int]):
    db = Database(Path(db_path))
    db.ex(
        "INSERT INTO users(email, password_hash, role, stages, is_active, token_version, created_at) VALUES (?,?,?,?,1,1,?)",
        (email.strip().lower(), ph.hash(password), role, json.dumps(stages), db.now()),
    )


def _login(client, email: str, password: str):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r


def test_health_and_public_defaults(client):
    assert client.get("/healthz").json() == {"ok": True}
    assert client.get("/readyz").json()["ok"] is True
    assert client.get("/api/v1/public/status").json()["venues"] == []
    assert client.get("/api/v1/public/schedule").json()["events"] == []
    r404 = client.get("/api/v1/does-not-exist")
    assert r404.status_code == 404 and r404.json()["error"] == "not_found"


def test_auth_boundaries_and_cors(client):
    assert client.get("/api/v1/live/board").status_code == 401
    assert client.get("/api/v1/admin/venues").status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "x@y.z", "password": "wrong"}).status_code == 401
    reg = client.post("/api/v1/auth/register", json={"email": "x@y.z", "password": "shouldnotmatter1234"})
    assert reg.status_code == 403 and reg.json()["error"] == "registration_disabled"

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


def test_refresh_rotation_reuse_detection_and_immediate_invalidation(client):
    cfg = client.app.state.cfg
    _seed_user(cfg.db_path, "rot@example.com", "StrongPass1234!", "admin", [])
    tokens = _login(client, "rot@example.com", "StrongPass1234!").json()

    ref = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert ref.status_code == 200
    new_tokens = ref.json()

    # Reusing the rotated refresh token must fail AND revoke the whole session
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {new_tokens['access_token']}"}).status_code == 401

    # Password change immediately invalidates existing access tokens
    t2 = _login(client, "rot@example.com", "StrongPass1234!").json()["access_token"]
    assert client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "StrongPass1234!", "new_password": "EvenStrongerPass99!"},
        headers={"Authorization": f"Bearer {t2}"},
    ).status_code == 200
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t2}"}).status_code == 401


def test_admin_crud_participants_and_csv_security(client):
    cfg = client.app.state.cfg
    _seed_user(cfg.db_path, "admin@example.com", "StrongPass1234!", "admin", [])
    tok = _login(client, "admin@example.com", "StrongPass1234!").json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}

    me = client.get("/api/v1/auth/me", headers=h).json()
    assert client.post(f"/api/v1/admin/users/{me['id']}/disable", headers=h).status_code == 400
    assert client.post("/api/v1/admin/venues", json={"name": "   ", "kind": "stage"}, headers=h).status_code == 422

    v = client.post("/api/v1/admin/venues", json={"name": "Stage 1", "kind": "stage", "slug": "stage-1", "active": True}, headers=h).json()
    assert v["slug"] == "stage-1"
    client.post("/api/v1/admin/events", json={"code": "101", "title": "Bharathanatyam", "category": "HS General", "venue_id": v["id"]}, headers=h)
    assert client.get("/api/v1/public/schedule").json()["events"][0]["category"] == "HS General"

    p = client.post("/api/v1/admin/participants", json={
        "register_no": "10342", "name": "+Asha", "school_name": "=CMD()", "school_code": "22001", "class": 9,
    }, headers=h).json()
    client.post(f"/api/v1/admin/participants/{p['id']}/entries", json={
        "item_code": "101", "venue_id": v["id"], "venue_name": v["name"], "perf_date": "2026-11-14",
    }, headers=h)

    csv_res = client.get("/api/v1/admin/participants/export.csv", headers=h)
    assert csv_res.status_code == 200
    assert "'=CMD()" in csv_res.text and "'+Asha" in csv_res.text

    assert client.get("/api/v1/admin/stats", headers=h).status_code == 200
    assert client.get("/api/v1/admin/health", headers=h).status_code == 200
    assert len(client.get("/api/v1/admin/audit", headers=h).json()["items"]) > 0

    assert client.delete(f"/api/v1/admin/participants/{p['id']}", headers=h).status_code == 200
    assert client.get("/api/v1/admin/participants", headers=h).json()["total"] == 0
    assert client.get("/api/v1/public/dashboard").json()["overall"]["participants"] == 0


def test_stagemaster_direct_control_and_quick_register_assign(client):
    cfg = client.app.state.cfg
    _seed_user(cfg.db_path, "adm_d@example.com", "StrongPass1234!", "admin", [])
    _seed_user(cfg.db_path, "sm_d@example.com", "StrongPass1234!", "stagemaster", [1])

    adm_h = {"Authorization": f"Bearer {_login(client, 'adm_d@example.com', 'StrongPass1234!').json()['access_token']}"}
    sm_h = {"Authorization": f"Bearer {_login(client, 'sm_d@example.com', 'StrongPass1234!').json()['access_token']}"}

    v1 = client.post("/api/v1/admin/venues", json={"name": "Stage 1", "kind": "stage", "active": True}, headers=adm_h).json()
    client.post("/api/v1/admin/participants", json={
        "register_no": "77777", "name": "Kavya", "school_name": "St. Marys", "school_code": "22010", "class": 10,
    }, headers=adm_h)

    r = client.post("/api/v1/live/state", json={
        "venue_id": v1["id"], "active": True, "state": "RUNNING",
        "current_item": "101 · Bharathanatyam", "current_chest": "C50",
        "upcoming_chests": "C51, C52", "announcement": "Report backstage",
    }, headers=sm_h)
    assert r.status_code == 200

    st = client.get("/api/v1/public/status").json()["venues"][0]
    assert st["state"] == "RUNNING" and st["now"]["roll"] == "C50"
    assert [u["roll"] for u in st["upcoming"]] == ["C51", "C52"]
    assert client.get("/api/v1/public/dashboard").json()["overall"]["running_venues"] == 1

    # Deactivating stage keeps it visible to its assigned stagemaster
    assert client.post("/api/v1/live/state", json={
        "venue_id": v1["id"], "active": False, "state": "IDLE",
        "current_item": None, "current_chest": None, "upcoming_chests": None, "announcement": "",
    }, headers=sm_h).status_code == 200
    assert client.get("/api/v1/public/status").json()["venues"][0]["state"] == "INACTIVE"
    assert len(client.get("/api/v1/live/board", headers=sm_h).json()["board"]) == 1

    bid = client.post("/api/v1/photos/batches", json={"venue_id": v1["id"], "workflow": "quick", "perf_date": "2026-11-16"}, headers=sm_h).json()["batch_id"]
    aid = client.post(f"/api/v1/photos/batches/{bid}/upload", data={"kind": "stage"}, files={"file": ("stage.png", _MIN_PNG, "image/png")}, headers=sm_h).json()["asset_id"]
    assert client.post("/api/v1/photos/assign-by-register", json={"asset_id": aid, "venue_id": v1["id"], "item_code": "101", "register_nos": ["77777"]}, headers=sm_h).status_code == 200
    assert client.post(f"/api/v1/photos/batches/{bid}/publish", headers=sm_h).status_code == 200

    pub = client.post("/api/v1/photos/public/lookup", json={"register_no": "77777", "name": "kavya"}).json()
    assert len(pub["photos"]) == 1 and pub["photos"][0]["entries"] == ["101"]


def test_worker_auth_isolation(client):
    cfg = client.app.state.cfg
    _seed_user(cfg.db_path, "adm_w@example.com", "StrongPass1234!", "admin", [])
    adm_tok = _login(client, "adm_w@example.com", "StrongPass1234!").json()["access_token"]
    obs_tok = derive_worker_token(cfg.secret_key, "obs")
    photo_tok = derive_worker_token(cfg.secret_key, "photos")

    for bad in ({}, {"X-Worker-Token": ""}, {"X-Worker-Token": cfg.secret_key}, {"Authorization": f"Bearer {adm_tok}"}, {"X-Worker-Token": photo_tok}):
        assert client.get("/api/v1/internal/backup", headers=bad).status_code == 403
    assert client.post("/api/v1/photos/internal/jobs/pull", headers={"X-Worker-Token": obs_tok}).status_code == 403

    bak = client.get("/api/v1/internal/backup", headers={"X-Worker-Token": obs_tok})
    assert bak.status_code == 200 and bak.content.startswith(b"SQLite format 3\x00")
    assert client.get("/api/v1/internal/audit-export", headers={"X-Worker-Token": obs_tok}).status_code == 200


def test_photo_lifecycle_and_privacy_gate(client):
    cfg = client.app.state.cfg
    _seed_user(cfg.db_path, "adm_p@example.com", "StrongPass1234!", "admin", [])
    _seed_user(cfg.db_path, "sm1@example.com", "StrongPass1234!", "stagemaster", [1])
    _seed_user(cfg.db_path, "dw1@example.com", "StrongPass1234!", "dataworker", [])

    adm_h = {"Authorization": f"Bearer {_login(client, 'adm_p@example.com', 'StrongPass1234!').json()['access_token']}"}
    sm_h = {"Authorization": f"Bearer {_login(client, 'sm1@example.com', 'StrongPass1234!').json()['access_token']}"}
    dw_h = {"Authorization": f"Bearer {_login(client, 'dw1@example.com', 'StrongPass1234!').json()['access_token']}"}

    v1 = client.post("/api/v1/admin/venues", json={"name": "Stage 1", "kind": "stage", "active": True}, headers=adm_h).json()
    v2 = client.post("/api/v1/admin/venues", json={"name": "Stage 2", "kind": "stage", "active": True}, headers=adm_h).json()
    part = client.post("/api/v1/admin/participants", json={"register_no": "54321", "name": "Meera", "school_name": "GHSS Mala", "school_code": "22009", "class": 11}, headers=adm_h).json()
    entry = client.post(f"/api/v1/admin/participants/{part['id']}/entries", json={"item_code": "201", "venue_id": v1["id"], "venue_name": v1["name"], "perf_date": "2026-11-14"}, headers=adm_h).json()

    assert client.get("/api/v1/admin/venues", headers=dw_h).status_code == 403
    assert client.get("/api/v1/live/board", headers=dw_h).status_code == 403
    assert client.post("/api/v1/photos/batches", json={"venue_id": v2["id"], "workflow": "bulk"}, headers=sm_h).status_code == 403

    bid = client.post("/api/v1/photos/batches", json={"venue_id": v1["id"], "workflow": "bulk"}, headers=sm_h).json()["batch_id"]
    assert client.post(f"/api/v1/photos/batches/{bid}/upload", data={"kind": "stage"}, files={"file": ("x.jpg", b"<svg/>", "image/jpeg")}, headers=sm_h).status_code == 400
    slip_id = client.post(f"/api/v1/photos/batches/{bid}/upload", data={"kind": "slip"}, files={"file": ("s.png", _MIN_PNG, "image/png")}, headers=sm_h).json()["asset_id"]
    stage_id = client.post(f"/api/v1/photos/batches/{bid}/upload", data={"kind": "stage"}, files={"file": ("p.png", _MIN_PNG, "image/png")}, headers=sm_h).json()["asset_id"]

    assert client.get(f"/api/v1/photos/staff/assets/{slip_id}/view").status_code == 401
    assert client.get(f"/api/v1/photos/assets/{stage_id}/view", params={"exp": 9999999999, "sig": "bad"}).status_code == 403
    assert client.get(f"/api/v1/photos/staff/assets/{slip_id}/view", headers=dw_h).status_code == 200
    assert client.post("/api/v1/photos/assign", json={"asset_id": stage_id, "participant_entry_ids": [entry["id"]]}, headers=dw_h).status_code == 200
    assert client.post("/api/v1/photos/public/lookup", json={"register_no": "54321", "name": "meera"}).json()["photos"] == []

    pw_h = {"X-Worker-Token": derive_worker_token(cfg.secret_key, "photos")}
    job = client.post("/api/v1/photos/internal/jobs/pull", headers=pw_h).json()["job"]
    assert job["id"] == stage_id
    assert client.get(f"/api/v1/photos/internal/assets/{stage_id}/raw", headers=pw_h).status_code == 200
    assert client.post(f"/api/v1/photos/internal/jobs/{stage_id}/complete", files={"file": ("o.webp", _MIN_WEBP, "image/webp")}, headers=pw_h).status_code == 200
    assert client.post("/api/v1/photos/internal/jobs/pull", headers=pw_h).json()["job"] is None

    assert client.post(f"/api/v1/photos/batches/{bid}/publish", headers=dw_h).status_code == 200
    assert client.post("/api/v1/photos/public/lookup", json={"register_no": "54321", "name": "Wrong"}).status_code == 404
    pub = client.post("/api/v1/photos/public/lookup", json={"register_no": "54321", "name": "meera"}).json()
    assert len(pub["photos"]) == 1
    assert client.get(pub["photos"][0]["url"]).content == _MIN_WEBP
    assert "attachment" in client.get(pub["photos"][0]["url"] + "&dl=1").headers.get("content-disposition", "")


def test_rate_limiting(client):
    _RATE_BUCKETS.clear()
    try:
        for _ in range(12):
            assert client.post("/api/v1/photos/public/lookup", json={"register_no": "99999", "name": "Nobody"}).status_code == 404
        assert client.post("/api/v1/photos/public/lookup", json={"register_no": "99999", "name": "Nobody"}).status_code == 429
    finally:
        _RATE_BUCKETS.clear()
