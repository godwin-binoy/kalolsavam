"""Core Photo API: stage upload, Data Worker assignment, HMAC-signed public lookup, worker jobs."""
from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from ..auth import has_role
from ..deps import (
    check_stage,
    escape_like,
    get_cfg,
    get_db,
    rate_limit,
    require_photo_staff,
    require_worker,
)
from ..models import PhotoAssignByRegisterIn, PhotoAssignIn, PhotoBatchIn, PhotoLookupIn

router = APIRouter()

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_SIGNED_URL_TTL = 900
_INFLIGHT_TIMEOUT = 300
_EXT_TO_MIME = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def _storage_dir(request: Request) -> Path:
    p = Path(get_cfg(request).db_path).parent / "photos"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _detect_image_ext(head: bytes) -> str | None:
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if len(head) >= 12 and head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return None


def _sign_asset(secret: str, asset_id: int, exp: int) -> str:
    msg = f"asset:{asset_id}:{exp}".encode()
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


async def _save_validated_image(file: UploadFile, storage: Path) -> str:
    head = await file.read(64)
    ext = _detect_image_ext(head)
    if not ext:
        raise HTTPException(400, "unsupported_image_type")

    fname = f"{uuid.uuid4().hex}{ext}"
    fpath = storage / fname
    written = len(head)
    try:
        with open(fpath, "wb") as out:
            out.write(head)
            while chunk := await file.read(65536):
                written += len(chunk)
                if written > _MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "file_too_large")
                out.write(chunk)
    except BaseException:
        fpath.unlink(missing_ok=True)
        raise
    return fname


def _safe_asset_path(storage: Path, filename: str) -> Path:
    root = storage.resolve()
    target = (storage / Path(filename).name).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise HTTPException(404, "file_missing")
    return target


@router.post("/batches")
def create_batch(body: PhotoBatchIn, request: Request, user=Depends(require_photo_staff)):
    if not has_role(user, "admin", "dataworker"):
        check_stage(user, body.venue_id)
    db = get_db(request)
    if not db.one("SELECT id FROM venues WHERE id = ?", (body.venue_id,)):
        raise HTTPException(404, "venue_not_found")
    if body.queue_item_id is not None:
        qi = db.one("SELECT id, venue_id FROM queue_items WHERE id = ?", (body.queue_item_id,))
        if not qi or qi["venue_id"] != body.venue_id:
            raise HTTPException(404, "queue_item_not_found")
    status = "staging" if body.workflow == "quick" else "queued"
    with db.transaction():
        cur = db.ex(
            "INSERT INTO photo_batches(queue_item_id, venue_id, workflow, perf_date, status, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (body.queue_item_id, body.venue_id, body.workflow, body.perf_date, status, db.now()),
        )
    return {"batch_id": cur.lastrowid}


@router.post("/batches/{batch_id}/upload")
async def upload_file(
    batch_id: int,
    request: Request,
    kind: str = Form(..., pattern=r"^(slip|stage)$"),
    file: UploadFile = File(...),
    user=Depends(require_photo_staff),
):
    db = get_db(request)
    b = db.one("SELECT id, venue_id FROM photo_batches WHERE id = ?", (batch_id,))
    if not b:
        raise HTTPException(404, "batch_not_found")
    if not has_role(user, "admin", "dataworker"):
        check_stage(user, b["venue_id"])

    storage = _storage_dir(request)
    fname = await _save_validated_image(file, storage)
    try:
        with db.transaction():
            cur = db.ex(
                "INSERT INTO photo_assets(batch_id, kind, filename, uploaded_at, processed) "
                "VALUES (?,?,?,?,0)",
                (batch_id, kind, fname, db.now()),
            )
    except BaseException:
        (storage / fname).unlink(missing_ok=True)
        raise
    return {"asset_id": cur.lastrowid}


@router.get("/batches")
def list_batches(request: Request, user=Depends(require_photo_staff)):
    batches = get_db(request).q(
        "SELECT b.*, v.name AS venue_name, "
        "(SELECT COUNT(*) FROM photo_assets a WHERE a.batch_id = b.id) AS asset_count "
        "FROM photo_batches b "
        "LEFT JOIN venues v ON v.id = b.venue_id "
        "WHERE b.status = 'queued' ORDER BY b.created_at ASC"
    )
    return {"batches": [dict(b) for b in batches]}


@router.get("/batches/{batch_id}")
def get_batch(batch_id: int, request: Request, user=Depends(require_photo_staff)):
    db = get_db(request)
    b = db.one("SELECT * FROM photo_batches WHERE id = ?", (batch_id,))
    if not b:
        raise HTTPException(404, "not_found")
    assets = db.q("SELECT * FROM photo_assets WHERE batch_id = ? ORDER BY id", (batch_id,))
    out = []
    for a in assets:
        assigned = db.q(
            """
            SELECT pae.participant_entry_id, pe.item_code, p.register_no, p.name
            FROM photo_asset_entries pae
            JOIN participant_entries pe ON pe.id = pae.participant_entry_id
            JOIN participants p ON p.id = pe.participant_id
            WHERE pae.photo_asset_id = ? AND pe.deleted_at IS NULL AND p.deleted_at IS NULL
            """,
            (a["id"],),
        )
        out.append({
            "id": a["id"],
            "kind": a["kind"],
            "processed": a["processed"],
            "url": f"/api/v1/photos/staff/assets/{a['id']}/view",
            "assigned_to": [x["participant_entry_id"] for x in assigned],
            "assigned_details": [dict(x) for x in assigned],
        })
    return {"batch": dict(b), "assets": out}


@router.get("/participants/search")
def search_participants_for_photos(
    request: Request,
    q: str = "",
    item_code: str = "",
    user=Depends(require_photo_staff),
):
    term = q.strip()
    icode = item_code.strip()
    if len(term) < 2 and not icode:
        return {"participants": []}
    db = get_db(request)
    if len(term) >= 2:
        safe_q = escape_like(term)
        parts = db.q(
            "SELECT id, register_no, name, school_name FROM participants "
            "WHERE deleted_at IS NULL AND (register_no LIKE ? ESCAPE '\\' OR name LIKE ? ESCAPE '\\') "
            "ORDER BY register_no LIMIT 20",
            (f"%{safe_q}%", f"%{safe_q}%"),
        )
    else:
        parts = db.q(
            "SELECT DISTINCT p.id, p.register_no, p.name, p.school_name "
            "FROM participants p "
            "JOIN participant_entries pe ON pe.participant_id = p.id "
            "WHERE p.deleted_at IS NULL AND pe.deleted_at IS NULL AND pe.item_code = ? "
            "ORDER BY p.register_no LIMIT 30",
            (icode,),
        )
    if not parts:
        return {"participants": []}
    pids = [p["id"] for p in parts]
    placeholders = ",".join(["?"] * len(pids))
    entries = db.q(
        f"SELECT id, participant_id, item_code, venue_name, perf_date FROM participant_entries "  # noqa: S608
        f"WHERE participant_id IN ({placeholders}) AND deleted_at IS NULL ORDER BY perf_date, item_code",
        tuple(pids),
    )
    by_p: dict[int, list[dict]] = {}
    for e in entries:
        by_p.setdefault(e["participant_id"], []).append(dict(e))
    return {
        "participants": [
            {**dict(p), "entries": by_p.get(p["id"], [])}
            for p in parts
        ]
    }


@router.post("/assign")
def assign_photo(body: PhotoAssignIn, request: Request, user=Depends(require_photo_staff)):
    db = get_db(request)
    asset = db.one("SELECT id, batch_id FROM photo_assets WHERE id = ?", (body.asset_id,))
    if not asset:
        raise HTTPException(404, "asset_not_found")
    source = "data_worker" if has_role(user, "dataworker") else "stagemaster_quick"
    with db.transaction():
        for eid in body.participant_entry_ids:
            entry = db.one(
                "SELECT id FROM participant_entries WHERE id = ? AND deleted_at IS NULL",
                (eid,),
            )
            if not entry:
                raise HTTPException(404, "entry_not_found")
            db.ex(
                "INSERT OR IGNORE INTO photo_asset_entries(photo_asset_id, participant_entry_id, source) "
                "VALUES (?,?,?)",
                (body.asset_id, eid, source),
            )
    return {"ok": True, "batch_id": asset["batch_id"]}




@router.post("/assign-by-register")
def assign_photo_by_register(
    body: PhotoAssignByRegisterIn,
    request: Request,
    user=Depends(require_photo_staff),
):
    if not has_role(user, "admin", "dataworker"):
        check_stage(user, body.venue_id)
    db = get_db(request)
    asset = db.one("SELECT id, batch_id FROM photo_assets WHERE id = ?", (body.asset_id,))
    if not asset:
        raise HTTPException(404, "asset_not_found")
    venue = db.one("SELECT id, name FROM venues WHERE id = ?", (body.venue_id,))
    if not venue:
        raise HTTPException(404, "venue_not_found")

    item_code = body.item_code.strip()
    perf_date = body.perf_date or time.strftime("%Y-%m-%d")
    now = db.now()
    entry_ids: list[int] = []

    with db.transaction():
        for raw_reg in body.register_nos:
            reg = raw_reg.strip()
            p = db.one(
                "SELECT id FROM participants WHERE register_no = ? AND deleted_at IS NULL",
                (reg,),
            )
            if not p:
                raise HTTPException(404, f"participant_not_found:{reg}")
            entry = db.one(
                "SELECT id FROM participant_entries "
                "WHERE participant_id = ? AND item_code = ? AND deleted_at IS NULL",
                (p["id"], item_code),
            )
            if entry:
                eid = entry["id"]
            else:
                cnt = db.one(
                    "SELECT COUNT(*) c FROM participant_entries "
                    "WHERE participant_id = ? AND deleted_at IS NULL",
                    (p["id"],),
                )["c"]
                if cnt >= 7:
                    raise HTTPException(409, f"participant_at_7_items:{reg}")
                cur_e = db.ex(
                    "INSERT INTO participant_entries(participant_id, item_code, venue_id, "
                    " venue_name, perf_date, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                    (p["id"], item_code, venue["id"], venue["name"], perf_date, now, now),
                )
                eid = cur_e.lastrowid
            entry_ids.append(eid)
            db.ex(
                "INSERT OR IGNORE INTO photo_asset_entries(photo_asset_id, participant_entry_id, source) "
                "VALUES (?,?,?)",
                (body.asset_id, eid, "stagemaster_quick"),
            )

    return {"ok": True, "batch_id": asset["batch_id"], "entry_ids": entry_ids}

@router.post("/batches/{batch_id}/publish")
def publish_batch(batch_id: int, request: Request, user=Depends(require_photo_staff)):
    db = get_db(request)
    b = db.one("SELECT id, venue_id FROM photo_batches WHERE id = ?", (batch_id,))
    if not b:
        raise HTTPException(404, "not_found")
    if not has_role(user, "admin", "dataworker"):
        check_stage(user, b["venue_id"])
    db.ex("UPDATE photo_batches SET status = 'published' WHERE id = ?", (batch_id,))
    return {"ok": True}


@router.get("/staff/assets/{asset_id}/view")
def view_staff_asset(asset_id: int, request: Request, user=Depends(require_photo_staff)):
    db = get_db(request)
    a = db.one("SELECT filename FROM photo_assets WHERE id = ?", (asset_id,))
    if not a:
        raise HTTPException(404, "not_found")
    fpath = _safe_asset_path(_storage_dir(request), a["filename"])
    media_type = _EXT_TO_MIME.get(fpath.suffix.lower(), "application/octet-stream")
    return FileResponse(
        fpath,
        media_type=media_type,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )


@router.get("/assets/{asset_id}/view")
def view_public_asset(
    asset_id: int,
    request: Request,
    exp: int,
    sig: str,
    dl: int = 0,
):
    if exp < int(time.time()):
        raise HTTPException(403, "url_expired")
    cfg = get_cfg(request)
    expected = _sign_asset(cfg.secret_key, asset_id, exp)
    if not hmac.compare_digest(sig, expected):
        raise HTTPException(403, "invalid_signature")

    db = get_db(request)
    a = db.one(
        """
        SELECT a.filename
        FROM photo_assets a
        JOIN photo_batches b ON b.id = a.batch_id
        WHERE a.id = ? AND a.kind = 'stage' AND b.status = 'published'
        """,
        (asset_id,),
    )
    if not a:
        raise HTTPException(404, "not_found")
    fpath = _safe_asset_path(_storage_dir(request), a["filename"])
    media_type = _EXT_TO_MIME.get(fpath.suffix.lower(), "application/octet-stream")
    headers = {"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"}
    if dl:
        return FileResponse(
            fpath,
            media_type=media_type,
            filename=f"kalolsavam-photo-{asset_id}{fpath.suffix.lower()}",
            headers=headers,
        )
    return FileResponse(fpath, media_type=media_type, headers=headers)


@router.post("/public/lookup", dependencies=[Depends(rate_limit("photo_lookup", 12, 60))])
def public_lookup(body: PhotoLookupIn, request: Request):
    db = get_db(request)
    cfg = get_cfg(request)
    p = db.one(
        "SELECT id FROM participants WHERE register_no = ? AND lower(name) = lower(?) AND deleted_at IS NULL",
        (body.register_no.strip(), body.name.strip()),
    )
    if not p:
        raise HTTPException(404, "not_found")

    rows = db.q(
        """
        SELECT a.id AS asset_id, pe.item_code
        FROM participant_entries pe
        JOIN photo_asset_entries pae ON pae.participant_entry_id = pe.id
        JOIN photo_assets a ON a.id = pae.photo_asset_id
        JOIN photo_batches b ON b.id = a.batch_id
        WHERE pe.participant_id = ?
          AND pe.deleted_at IS NULL
          AND a.kind = 'stage'
          AND b.status = 'published'
        ORDER BY a.id DESC, pe.item_code
        """,
        (p["id"],),
    )
    if not rows:
        return {"photos": []}

    exp = int(time.time()) + _SIGNED_URL_TTL
    grouped: dict[int, list[str]] = {}
    for r in rows:
        grouped.setdefault(r["asset_id"], []).append(r["item_code"])

    return {
        "photos": [
            {
                "asset_id": aid,
                "url": f"/api/v1/photos/assets/{aid}/view?exp={exp}&sig={_sign_asset(cfg.secret_key, aid, exp)}",
                "entries": codes,
            }
            for aid, codes in grouped.items()
        ]
    }


# ── Worker Endpoints (Device 2: server_photos/worker.py) ──────────────────────
@router.post("/internal/jobs/pull")
def pull_worker_job(request: Request, _=Depends(require_worker("photos"))):
    """Atomically claim one unprocessed stage photo (with stale in-flight recovery)."""
    db = get_db(request)
    now = db.now()
    stale_before = now - _INFLIGHT_TIMEOUT
    with db.transaction():
        row = db.one(
            """
            SELECT id, batch_id, kind, filename
            FROM photo_assets
            WHERE kind = 'stage'
              AND (processed = 0 OR (processed = 2 AND processed_at < ?))
            ORDER BY id ASC LIMIT 1
            """,
            (stale_before,),
        )
        if not row:
            return {"job": None}
        upd = db.ex(
            "UPDATE photo_assets SET processed = 2, processed_at = ? "
            "WHERE id = ? AND (processed = 0 OR (processed = 2 AND processed_at < ?))",
            (now, row["id"], stale_before),
        )
        if upd.rowcount == 0:
            return {"job": None}
    return {"job": dict(row)}


@router.get("/internal/assets/{asset_id}/raw")
def download_raw_for_worker(asset_id: int, request: Request, _=Depends(require_worker("photos"))):
    a = get_db(request).one("SELECT filename FROM photo_assets WHERE id = ?", (asset_id,))
    if not a:
        raise HTTPException(404, "not_found")
    fpath = _safe_asset_path(_storage_dir(request), a["filename"])
    return FileResponse(fpath, media_type="application/octet-stream")


@router.post("/internal/jobs/{asset_id}/complete")
async def complete_worker_job(
    asset_id: int,
    request: Request,
    file: UploadFile = File(...),
    _=Depends(require_worker("photos")),
):
    db = get_db(request)
    a = db.one("SELECT id, filename FROM photo_assets WHERE id = ?", (asset_id,))
    if not a:
        raise HTTPException(404, "not_found")

    storage = _storage_dir(request)
    new_fname = await _save_validated_image(file, storage)
    old_fname = a["filename"]
    try:
        with db.transaction():
            db.ex(
                "UPDATE photo_assets SET filename = ?, processed = 1, processed_at = ? WHERE id = ?",
                (new_fname, db.now(), asset_id),
            )
    except BaseException:
        (storage / new_fname).unlink(missing_ok=True)
        raise

    if old_fname and old_fname != new_fname:
        try:
            old_path = (storage / Path(old_fname).name).resolve()
            if old_path.is_relative_to(storage.resolve()):
                old_path.unlink(missing_ok=True)
        except OSError:
            pass
    return {"ok": True}
