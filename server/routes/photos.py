"""Photo API: stage upload, Data Worker assignment, school-team lookup, HMAC-signed public lookup, worker jobs."""
from __future__ import annotations

import hashlib
import hmac
import re
import time
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, BeforeValidator, Field

from ..auth import (
    check_stage,
    escape_like,
    get_cfg,
    get_db,
    has_role,
    rate_limit,
    require_photo_staff,
    require_worker,
)

router = APIRouter()

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_SIGNED_URL_TTL = 900
_INFLIGHT_TIMEOUT = 300
_EXT_TO_MIME = {".jpg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}


def _strip(v: object) -> object:
    return v.strip() if isinstance(v, str) else v


def _norm_name(s: str) -> str:
    return re.sub(r"[\s.]+", " ", (s or "").strip().lower()).strip()


class PhotoBatchIn(BaseModel):
    venue_id: int
    workflow: str = Field(pattern=r"^(bulk|quick)$")
    perf_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class PhotoAssignIn(BaseModel):
    asset_id: int
    participant_entry_ids: list[int] = Field(min_length=1, max_length=30)


class PhotoAssignByRegisterIn(BaseModel):
    asset_id: int
    venue_id: int
    item_code: Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=32)]
    register_nos: list[str] = Field(min_length=1, max_length=30)
    perf_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class PhotoLookupIn(BaseModel):
    register_no: str = Field(pattern=r"^\d{4,5}$")
    name: Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=200)]


def _check_photo_stage(user: dict, venue_id: int) -> None:
    if not has_role(user, "admin", "dataworker"):
        check_stage(user, venue_id)


def _batch_for_staff(db, batch_id: int, user: dict, err: str = "not_found"):
    b = db.one("SELECT id, venue_id FROM photo_batches WHERE id = ?", (batch_id,))
    if not b:
        raise HTTPException(404, err)
    _check_photo_stage(user, b["venue_id"])
    return b


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
    return hmac.new(secret.encode("utf-8"), f"asset:{asset_id}:{exp}".encode(), hashlib.sha256).hexdigest()


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
    _check_photo_stage(user, body.venue_id)
    db = get_db(request)
    if not db.one("SELECT id FROM venues WHERE id = ?", (body.venue_id,)):
        raise HTTPException(404, "venue_not_found")
    status_val = "staging" if body.workflow == "quick" else "queued"
    with db.transaction():
        cur = db.ex(
            "INSERT INTO photo_batches(venue_id, workflow, perf_date, status, created_at) VALUES (?,?,?,?,?)",
            (body.venue_id, body.workflow, body.perf_date, status_val, db.now()),
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
    _batch_for_staff(db, batch_id, user, "batch_not_found")

    storage = _storage_dir(request)
    fname = await _save_validated_image(file, storage)
    try:
        with db.transaction():
            cur = db.ex(
                "INSERT INTO photo_assets(batch_id, kind, filename, uploaded_at, processed) VALUES (?,?,?,?,0)",
                (batch_id, kind, fname, db.now()),
            )
    except BaseException:
        (storage / fname).unlink(missing_ok=True)
        raise
    return {"asset_id": cur.lastrowid}


@router.get("/batches")
def list_batches(request: Request, status: str = "queued", user=Depends(require_photo_staff)):
    stage_filter = "b.venue_id IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 26)"
    where = (
        f"WHERE {stage_filter} AND b.status IN ('queued', 'published', 'staging')"
        if status == "all"
        else (
            f"WHERE {stage_filter} AND b.status = 'published'"
            if status == "published"
            else f"WHERE {stage_filter} AND b.status = 'queued'"
        )
    )
    order = "DESC" if status == "published" else "ASC"
    batches = get_db(request).q(
        f"""
        SELECT b.*, v.name AS venue_name,
               (SELECT COUNT(*) FROM photo_assets a WHERE a.batch_id = b.id) AS asset_count,
               (SELECT COUNT(*) FROM photo_assets a WHERE a.batch_id = b.id AND a.kind = 'slip') AS slip_count,
               (SELECT COUNT(*) FROM photo_assets a WHERE a.batch_id = b.id AND a.kind = 'stage') AS stage_count,
               (SELECT COUNT(DISTINCT a.id) FROM photo_assets a
                JOIN photo_asset_entries pae ON pae.photo_asset_id = a.id
                WHERE a.batch_id = b.id AND a.kind = 'stage') AS assigned_stage_count
        FROM photo_batches b
        LEFT JOIN venues v ON v.id = b.venue_id
        {where}
        ORDER BY b.created_at {order} LIMIT 100
        """  # noqa: S608
    )
    return {"batches": [dict(b) for b in batches]}


@router.get("/batches/{batch_id}")
def get_batch(batch_id: int, request: Request, user=Depends(require_photo_staff)):
    db = get_db(request)
    b = db.one("SELECT b.*, v.name AS venue_name FROM photo_batches b LEFT JOIN venues v ON v.id = b.venue_id WHERE b.id = ?", (batch_id,))
    if not b:
        raise HTTPException(404, "not_found")
    assets = db.q("SELECT * FROM photo_assets WHERE batch_id = ? ORDER BY id", (batch_id,))
    out = []
    for a in assets:
        assigned = db.q(
            """
            SELECT pae.participant_entry_id, pe.item_code, COALESCE(pe.item_name, '') AS item_name,
                   p.register_no, p.name, p.school_name, p.school_code
            FROM photo_asset_entries pae
            JOIN participant_entries pe ON pe.id = pae.participant_entry_id
            JOIN participants p ON p.id = pe.participant_id
            WHERE pae.photo_asset_id = ? AND pe.deleted_at IS NULL AND p.deleted_at IS NULL
            ORDER BY p.register_no
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
    term, icode = q.strip(), item_code.strip()
    is_num = term.isdigit()
    if (not term or (not is_num and len(term) < 2)) and not icode:
        return {"participants": []}
    db = get_db(request)
    if term and (is_num or len(term) >= 2):
        safe_q = escape_like(term)
        parts = db.q(
            "SELECT id, register_no, name, school_name, school_code, student_class FROM participants "
            "WHERE deleted_at IS NULL AND (register_no LIKE ? ESCAPE '\\' OR name LIKE ? ESCAPE '\\' OR school_name LIKE ? ESCAPE '\\') "
            "ORDER BY register_no LIMIT 25",
            (f"%{safe_q}%", f"%{safe_q}%", f"%{safe_q}%"),
        )
    else:
        parts = db.q(
            "SELECT DISTINCT p.id, p.register_no, p.name, p.school_name, p.school_code, p.student_class "
            "FROM participants p JOIN participant_entries pe ON pe.participant_id = p.id "
            "WHERE p.deleted_at IS NULL AND pe.deleted_at IS NULL AND pe.item_code = ? "
            "ORDER BY p.register_no LIMIT 35",
            (icode,),
        )
    if not parts:
        return {"participants": []}
    pids = [p["id"] for p in parts]
    placeholders = ",".join(["?"] * len(pids))
    entries = db.q(
        f"SELECT id, participant_id, item_code, COALESCE(item_name, '') AS item_name, venue_name, perf_date FROM participant_entries "  # noqa: S608
        f"WHERE participant_id IN ({placeholders}) AND deleted_at IS NULL ORDER BY perf_date, item_code",
        tuple(pids),
    )
    by_p: dict[int, list[dict]] = {}
    for e in entries:
        by_p.setdefault(e["participant_id"], []).append(dict(e))
    return {"participants": [{**dict(p), "entries": by_p.get(p["id"], [])} for p in parts]}


@router.get("/team-lookup")
def lookup_school_team(
    request: Request,
    register_no: str,
    item_code: str = "",
    user=Depends(require_photo_staff),
):
    """Given one register number (and optional item_code), fetch the entire team from the same school."""
    reg = register_no.strip()
    icode = item_code.strip()
    db = get_db(request)
    anchor = db.one(
        "SELECT id, register_no, name, school_name, school_code, student_class FROM participants "
        "WHERE register_no = ? AND deleted_at IS NULL",
        (reg,),
    )
    if not anchor:
        raise HTTPException(404, "participant_not_found")

    school_code = anchor["school_code"]
    team_members: list[dict] = []
    if icode:
        ev_match = db.one("SELECT code, title FROM events WHERE code = ? OR lower(title) = lower(?)", (icode, icode))
        resolved_code = ev_match["code"] if ev_match else icode
        resolved_title = ev_match["title"] if ev_match else icode
        rows = db.q(
            """
            SELECT p.id, p.register_no, p.name, p.school_name, p.school_code, p.student_class,
                   pe.id AS entry_id, pe.item_code, COALESCE(pe.item_name, '') AS item_name
            FROM participants p
            JOIN participant_entries pe ON pe.participant_id = p.id
            WHERE p.school_code = ? AND p.deleted_at IS NULL
              AND pe.deleted_at IS NULL
              AND (pe.item_code = ? OR lower(COALESCE(pe.item_name, '')) = lower(?))
            ORDER BY p.register_no
            """,
            (school_code, resolved_code, resolved_title),
        )
        team_members = [dict(r) for r in rows]

    all_school = [
        dict(r) for r in db.q(
            "SELECT id, register_no, name, school_name, school_code, student_class "
            "FROM participants WHERE school_code = ? AND deleted_at IS NULL ORDER BY register_no",
            (school_code,),
        )
    ]
    if not team_members:
        team_members = [{**dict(anchor), "entry_id": None, "item_code": icode, "item_name": ""}]

    return {
        "anchor": dict(anchor),
        "school_name": anchor["school_name"],
        "school_code": school_code,
        "item_code": icode,
        "team": team_members,
        "school_peers": all_school,
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
            if not db.one("SELECT id FROM participant_entries WHERE id = ? AND deleted_at IS NULL", (eid,)):
                raise HTTPException(404, "entry_not_found")
            db.ex(
                "INSERT OR IGNORE INTO photo_asset_entries(photo_asset_id, participant_entry_id, source) VALUES (?,?,?)",
                (body.asset_id, eid, source),
            )
    return {"ok": True, "batch_id": asset["batch_id"]}


@router.post("/assign-by-register")
def assign_photo_by_register(
    body: PhotoAssignByRegisterIn,
    request: Request,
    user=Depends(require_photo_staff),
):
    _check_photo_stage(user, body.venue_id)
    db = get_db(request)
    asset = db.one("SELECT id, batch_id FROM photo_assets WHERE id = ?", (body.asset_id,))
    if not asset:
        raise HTTPException(404, "asset_not_found")
    venue = db.one("SELECT id, name FROM venues WHERE id = ?", (body.venue_id,))
    if not venue:
        raise HTTPException(404, "venue_not_found")

    ev = db.one("SELECT code, title FROM events WHERE code = ? OR lower(title) = lower(?)", (body.item_code, body.item_code))
    norm_item_code = ev["code"] if ev else body.item_code
    ev_title = ev["title"] if ev else None
    source = "data_worker" if has_role(user, "dataworker") else "stagemaster_quick"
    perf_date = body.perf_date or time.strftime("%Y-%m-%d")
    now = db.now()
    entry_ids: list[int] = []
    with db.transaction():
        for raw_reg in body.register_nos:
            reg = raw_reg.strip()
            p = db.one("SELECT id FROM participants WHERE register_no = ? AND deleted_at IS NULL", (reg,))
            if not p:
                raise HTTPException(404, f"participant_not_found:{reg}")
            entry = db.one(
                "SELECT id FROM participant_entries WHERE participant_id = ? AND item_code = ? AND deleted_at IS NULL",
                (p["id"], norm_item_code),
            )
            if entry:
                eid = entry["id"]
            else:
                if db.one(
                    "SELECT COUNT(*) c FROM participant_entries WHERE participant_id = ? AND deleted_at IS NULL",
                    (p["id"],),
                )["c"] >= 7:
                    raise HTTPException(409, f"participant_at_7_items:{reg}")
                cur_e = db.ex(
                    "INSERT INTO participant_entries(participant_id, item_code, item_name, venue_id, venue_name, perf_date, created_at, updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (p["id"], norm_item_code, ev_title, venue["id"], venue["name"], perf_date, now, now),
                )
                eid = cur_e.lastrowid
            entry_ids.append(eid)
            db.ex(
                "INSERT OR IGNORE INTO photo_asset_entries(photo_asset_id, participant_entry_id, source) VALUES (?,?,?)",
                (body.asset_id, eid, source),
            )
    return {"ok": True, "batch_id": asset["batch_id"], "entry_ids": entry_ids}


@router.delete("/assets/{asset_id}/entries/{entry_id}")
def unassign_photo_entry(asset_id: int, entry_id: int, request: Request, user=Depends(require_photo_staff)):
    db = get_db(request)
    asset = db.one(
        "SELECT a.id, a.batch_id, b.venue_id FROM photo_assets a JOIN photo_batches b ON b.id = a.batch_id WHERE a.id = ?",
        (asset_id,),
    )
    if not asset:
        raise HTTPException(404, "asset_not_found")
    _check_photo_stage(user, asset["venue_id"])
    db.ex(
        "DELETE FROM photo_asset_entries WHERE photo_asset_id = ? AND participant_entry_id = ?",
        (asset_id, entry_id),
    )
    return {"ok": True, "batch_id": asset["batch_id"]}


@router.delete("/assets/{asset_id}")
def delete_photo_asset(asset_id: int, request: Request, user=Depends(require_photo_staff)):
    db = get_db(request)
    asset = db.one(
        "SELECT a.id, a.batch_id, a.filename, b.venue_id FROM photo_assets a JOIN photo_batches b ON b.id = a.batch_id WHERE a.id = ?",
        (asset_id,),
    )
    if not asset:
        raise HTTPException(404, "asset_not_found")
    _check_photo_stage(user, asset["venue_id"])
    with db.transaction():
        db.ex("DELETE FROM photo_assets WHERE id = ?", (asset_id,))
    try:
        storage = _storage_dir(request)
        p = (storage / Path(asset["filename"]).name).resolve()
        if p.is_relative_to(storage.resolve()):
            p.unlink(missing_ok=True)
    except OSError:
        pass
    return {"ok": True, "batch_id": asset["batch_id"]}


@router.post("/batches/{batch_id}/publish")
def publish_batch(batch_id: int, request: Request, user=Depends(require_photo_staff)):
    db = get_db(request)
    _batch_for_staff(db, batch_id, user)
    db.ex("UPDATE photo_batches SET status = 'published' WHERE id = ?", (batch_id,))
    return {"ok": True}


@router.get("/staff/assets/{asset_id}/view")
def view_staff_asset(asset_id: int, request: Request, user=Depends(require_photo_staff)):
    a = get_db(request).one("SELECT filename FROM photo_assets WHERE id = ?", (asset_id,))
    if not a:
        raise HTTPException(404, "not_found")
    fpath = _safe_asset_path(_storage_dir(request), a["filename"])
    return FileResponse(
        fpath,
        media_type=_EXT_TO_MIME.get(fpath.suffix.lower(), "application/octet-stream"),
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )


@router.get("/assets/{asset_id}/view")
def view_public_asset(asset_id: int, request: Request, exp: int, sig: str, dl: int = 0):
    if exp < int(time.time()):
        raise HTTPException(403, "url_expired")
    cfg = get_cfg(request)
    if not hmac.compare_digest(sig, _sign_asset(cfg.secret_key, asset_id, exp)):
        raise HTTPException(403, "invalid_signature")

    a = get_db(request).one(
        "SELECT a.filename FROM photo_assets a JOIN photo_batches b ON b.id = a.batch_id "
        "WHERE a.id = ? AND a.kind = 'stage' AND b.status = 'published'",
        (asset_id,),
    )
    if not a:
        raise HTTPException(404, "not_found")
    fpath = _safe_asset_path(_storage_dir(request), a["filename"])
    mime = _EXT_TO_MIME.get(fpath.suffix.lower(), "application/octet-stream")
    headers = {"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"}
    if dl:
        return FileResponse(fpath, media_type=mime, filename=f"kalolsavam-photo-{asset_id}{fpath.suffix.lower()}", headers=headers)
    return FileResponse(fpath, media_type=mime, headers=headers)


@router.post("/public/lookup", dependencies=[Depends(rate_limit("photo_lookup", 45, 60))])
def public_lookup(body: PhotoLookupIn, request: Request):
    db, cfg = get_db(request), get_cfg(request)
    p = db.one(
        "SELECT id, register_no, name, school_name FROM participants WHERE register_no = ? AND deleted_at IS NULL",
        (body.register_no.strip(),),
    )
    if not p:
        raise HTTPException(404, "not_found")

    db_name = _norm_name(p["name"])
    in_name = _norm_name(body.name)
    db_tokens = [t for t in db_name.split(" ") if t]
    in_tokens = [t for t in in_name.split(" ") if t]
    matched = (
        db_name == in_name
        or db_name.replace(" ", "") == in_name.replace(" ", "")
        or (bool(in_tokens) and len(in_name.replace(" ", "")) >= 3 and all(t in db_tokens for t in in_tokens))
    )
    if not matched:
        raise HTTPException(404, "not_found")

    rows = db.q(
        """
        SELECT a.id AS asset_id, a.uploaded_at, pe.item_code,
               COALESCE(NULLIF(pe.item_name, ''), ev.title) AS item_name,
               COALESCE(v.name, pe.venue_name) AS venue_name
        FROM participant_entries pe
        JOIN photo_asset_entries pae ON pae.participant_entry_id = pe.id
        JOIN photo_assets a ON a.id = pae.photo_asset_id
        JOIN photo_batches b ON b.id = a.batch_id
        LEFT JOIN venues v ON v.id = b.venue_id
        LEFT JOIN events ev ON ev.code = pe.item_code
        WHERE pe.participant_id = ? AND pe.deleted_at IS NULL AND a.kind = 'stage' AND b.status = 'published'
        ORDER BY a.id DESC, pe.item_code
        """,
        (p["id"],),
    )
    if not rows:
        return {
            "participant": {"register_no": p["register_no"], "name": p["name"], "school_name": p["school_name"]},
            "photos": [],
        }

    exp = int(time.time()) + _SIGNED_URL_TTL
    grouped: dict[int, dict] = {}
    for r in rows:
        r_dict = dict(r)
        aid = r_dict["asset_id"]
        item_name = r_dict.get("item_name")
        label = f"{r_dict['item_code']} · {item_name}" if item_name else r_dict["item_code"]
        if aid not in grouped:
            grouped[aid] = {
                "asset_id": aid,
                "url": f"/api/v1/photos/assets/{aid}/view?exp={exp}&sig={_sign_asset(cfg.secret_key, aid, exp)}",
                "venue_name": r_dict.get("venue_name") or "",
                "uploaded_at": r_dict.get("uploaded_at"),
                "entries": [],
            }
        if label not in grouped[aid]["entries"]:
            grouped[aid]["entries"].append(label)

    return {
        "participant": {"register_no": p["register_no"], "name": p["name"], "school_name": p["school_name"]},
        "photos": list(grouped.values()),
    }


@router.post("/internal/jobs/pull")
def pull_worker_job(request: Request, _=Depends(require_worker("photos"))):
    db = get_db(request)
    now = db.now()
    stale_before = now - _INFLIGHT_TIMEOUT
    with db.transaction():
        row = db.one(
            "SELECT id, batch_id, kind, filename FROM photo_assets "
            "WHERE kind = 'stage' AND (processed = 0 OR (processed = 2 AND processed_at < ?)) "
            "ORDER BY id ASC LIMIT 1",
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
    return FileResponse(_safe_asset_path(_storage_dir(request), a["filename"]), media_type="application/octet-stream")


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
