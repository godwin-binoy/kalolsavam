"""Admin, Participant Registry, and Obs Worker internal endpoints."""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import re
import shutil
import sqlite3
import tempfile
import time as _t
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, BeforeValidator, EmailStr, Field
from starlette.background import BackgroundTask

from ..auth import (
    client_ip,
    csv_cell,
    escape_like,
    get_cfg,
    get_db,
    hash_ip,
    ph,
    require_admin,
    require_worker,
)
from .public import invalidate_public_cache

router = APIRouter()
internal_router = APIRouter()
log = logging.getLogger("kalolsavam")

MAX_ITEMS_PER_PARTICIPANT = 7
_ON_STAGE_IDS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 26}
_REG_RE = re.compile(r"^\d{4,5}$")
_SCHOOL_RE = re.compile(r"^\d{5,6}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CSV_COLS = (
    "register_no", "name", "school_name", "school_code", "class",
    "item_code", "venue_id", "venue_name", "perf_date",
)


def _strip(v: object) -> object:
    return v.strip() if isinstance(v, str) else v


def _clean_slug(v: object) -> str | None:
    if v is None:
        return None
    s = str(v).strip().lower()
    if not s:
        return None
    if not re.fullmatch(r"[a-z0-9-]+", s) or len(s) > 64:
        raise ValueError("invalid slug")
    return s


CleanSlug = Annotated[str | None, BeforeValidator(_clean_slug)]
ReqStr = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=200)]
OptStr = Annotated[str | None, BeforeValidator(_strip), Field(min_length=1, max_length=200)]
ReqShort = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=120)]
OptShort = Annotated[str | None, BeforeValidator(_strip), Field(min_length=1, max_length=120)]


class VenueIn(BaseModel):
    name: ReqShort
    kind: Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=32)] = "stage"
    slug: CleanSlug = None
    active: bool = True


class VenueUpdateIn(BaseModel):
    name: OptShort = None
    kind: Annotated[str | None, BeforeValidator(_strip), Field(min_length=1, max_length=32)] = None
    slug: CleanSlug = None
    active: bool | None = None


class EventIn(BaseModel):
    code: Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=32)]
    title: ReqStr
    category: str | None = Field(default=None, max_length=64)
    venue_id: int | None = None
    day: str | None = Field(default=None, max_length=32)
    scheduled_time: str | None = Field(default=None, max_length=16)


class EventUpdateIn(BaseModel):
    code: Annotated[str | None, BeforeValidator(_strip), Field(min_length=1, max_length=32)] = None
    title: OptStr = None
    category: str | None = Field(default=None, max_length=64)
    venue_id: int | None = None
    day: str | None = Field(default=None, max_length=32)
    scheduled_time: str | None = Field(default=None, max_length=16)


class UserIn(BaseModel):
    email: EmailStr
    role: str = Field(pattern=r"^(stagemaster|dataworker|admin)$")
    stages: list[int] = Field(default_factory=list)
    password: str = Field(min_length=12, max_length=256)


class UserUpdateIn(BaseModel):
    email: EmailStr | None = None
    role: str | None = Field(default=None, pattern=r"^(stagemaster|dataworker|admin)$")
    stages: list[int] | None = None
    is_active: bool | None = None


class PasswordResetIn(BaseModel):
    password: str = Field(min_length=12, max_length=256)


class ParticipantIn(BaseModel):
    register_no: str = Field(pattern=r"^\d{4,5}$")
    name: ReqStr
    school_name: ReqStr
    school_code: str = Field(pattern=r"^\d{5,6}$")
    student_class: int = Field(alias="class", ge=1, le=12)
    model_config = {"populate_by_name": True}


class ParticipantUpdateIn(BaseModel):
    register_no: str | None = Field(default=None, pattern=r"^\d{4,5}$")
    name: OptStr = None
    school_name: OptStr = None
    school_code: str | None = Field(default=None, pattern=r"^\d{5,6}$")
    student_class: int | None = Field(default=None, alias="class", ge=1, le=12)
    model_config = {"populate_by_name": True}


class ParticipantEntryIn(BaseModel):
    item_code: Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=32)]
    venue_id: int
    venue_name: ReqShort
    perf_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class ParticipantEntryUpdateIn(BaseModel):
    item_code: Annotated[str | None, BeforeValidator(_strip), Field(min_length=1, max_length=32)] = None
    venue_id: int | None = None
    venue_name: OptShort = None
    perf_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


def _audit(db, request: Request, user: dict, action: str, detail: str = "") -> None:
    try:
        db.ex(
            "INSERT INTO auth_audit(ts, username, ip_hash, event, detail) VALUES (?,?,?,?,?)",
            (db.now(), user.get("email", "admin"), hash_ip(client_ip(request), get_cfg(request).secret_key),
             "admin_action", f"{action}|{detail}"),
        )
    except Exception as exc:
        log.warning("audit_write_failed: %s", exc)


def _patch(row, body: BaseModel, *cols: str, always_set_if_not_none: bool = False) -> list:
    fields = body.model_fields_set
    vals = []
    for col in cols:
        attr = "student_class" if col == "student_class" else col
        val = getattr(body, attr)
        use_new = (val is not None) if always_set_if_not_none else (attr in fields)
        vals.append(val if use_new else row[col])
    return vals


def _row_or_404(db, table: str, row_id: int, err: str):
    row = db.one(f"SELECT * FROM {table} WHERE id = ?", (row_id,))  # noqa: S608
    if not row:
        raise HTTPException(404, err)
    return row


def _validate_stage_ids(db, stages: list[int]) -> None:
    if not stages:
        return
    valid = {r["id"] for r in db.q("SELECT id FROM venues")}
    bad = [s for s in stages if s not in valid]
    if bad:
        raise HTTPException(400, f"invalid_stage_ids:{bad}")


# ── Venues ────────────────────────────────────────────────────────────────────
@router.get("/venues")
def list_venues(request: Request, user=Depends(require_admin)):
    return {"venues": [dict(r) for r in get_db(request).q("SELECT * FROM venues ORDER BY id")]}


@router.post("/venues")
def create_venue(body: VenueIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    try:
        cur = db.ex(
            "INSERT INTO venues(name, kind, slug, active) VALUES (?,?,?,?)",
            (body.name, body.kind, body.slug, int(body.active)),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "duplicate_slug") from exc
    invalidate_public_cache(request.app)
    _audit(db, request, user, "create_venue", f"id={cur.lastrowid}")
    return dict(db.one("SELECT * FROM venues WHERE id = ?", (cur.lastrowid,)))


@router.put("/venues/{vid}")
def update_venue(vid: int, body: VenueUpdateIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    row = _row_or_404(db, "venues", vid, "venue_not_found")
    name = body.name if body.name is not None else row["name"]
    kind = body.kind if body.kind is not None else row["kind"]
    slug = body.slug if "slug" in body.model_fields_set else row["slug"]
    active = int(body.active) if body.active is not None else row["active"]
    try:
        db.ex("UPDATE venues SET name = ?, kind = ?, slug = ?, active = ? WHERE id = ?", (name, kind, slug, active, vid))
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "duplicate_slug") from exc
    invalidate_public_cache(request.app)
    _audit(db, request, user, "update_venue", f"id={vid}")
    return dict(db.one("SELECT * FROM venues WHERE id = ?", (vid,)))


@router.delete("/venues/{vid}")
def delete_venue(vid: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    _row_or_404(db, "venues", vid, "venue_not_found")
    if db.one("SELECT COUNT(*) c FROM events WHERE venue_id = ?", (vid,))["c"]:
        raise HTTPException(409, "venue_has_events")
    with db.transaction():
        db.ex("DELETE FROM live_state WHERE venue_id = ?", (vid,))
        db.ex("DELETE FROM venues WHERE id = ?", (vid,))
    invalidate_public_cache(request.app)
    _audit(db, request, user, "delete_venue", f"id={vid}")
    return {"ok": True}


# ── Events ────────────────────────────────────────────────────────────────────
@router.get("/events")
def list_events(request: Request, venue_id: int | None = None, user=Depends(require_admin)):
    db = get_db(request)
    q = "SELECT * FROM events"
    params: tuple = ()
    if venue_id is not None:
        q += " WHERE venue_id = ?"
        params = (venue_id,)
    return {"events": [dict(r) for r in db.q(q + " ORDER BY id LIMIT 5000", params)]}


@router.post("/events")
def create_event(body: EventIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    try:
        cur = db.ex(
            "INSERT INTO events(code, title, category, venue_id, day, scheduled_time) VALUES (?,?,?,?,?,?)",
            (body.code, body.title, body.category, body.venue_id, body.day, body.scheduled_time),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "duplicate_or_fk") from exc
    invalidate_public_cache(request.app)
    _audit(db, request, user, "create_event", f"id={cur.lastrowid},code={body.code}")
    return {"id": cur.lastrowid}


@router.put("/events/{eid}")
def update_event(eid: int, body: EventUpdateIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    row = _row_or_404(db, "events", eid, "event_not_found")
    try:
        code, title = _patch(row, body, "code", "title", always_set_if_not_none=True)
        cat, ven, day, when = _patch(row, body, "category", "venue_id", "day", "scheduled_time")
        db.ex(
            "UPDATE events SET code = ?, title = ?, category = ?, venue_id = ?, day = ?, scheduled_time = ? WHERE id = ?",
            (code, title, cat, ven, day, when, eid),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "duplicate_code_or_fk") from exc
    invalidate_public_cache(request.app)
    _audit(db, request, user, "update_event", f"id={eid}")
    return dict(db.one("SELECT * FROM events WHERE id = ?", (eid,)))


@router.delete("/events/{eid}")
def delete_event(eid: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    _row_or_404(db, "events", eid, "event_not_found")
    db.ex("DELETE FROM events WHERE id = ?", (eid,))
    invalidate_public_cache(request.app)
    _audit(db, request, user, "delete_event", f"id={eid}")
    return {"ok": True}


# ── Participants & Entries Registry ───────────────────────────────────────────
def _get_participant_or_404(db, pid: int):
    row = db.one("SELECT * FROM participants WHERE id = ? AND deleted_at IS NULL", (pid,))
    if not row:
        raise HTTPException(404, "participant_not_found")
    return row


def _active_entry_count(db, pid: int) -> int:
    return db.one("SELECT COUNT(*) c FROM participant_entries WHERE participant_id = ? AND deleted_at IS NULL", (pid,))["c"]


@router.get("/participants")
def list_participants(
    request: Request,
    q: str | None = None,
    school_code: str | None = None,
    limit: int = 200,
    offset: int = 0,
    user=Depends(require_admin),
):
    db = get_db(request)
    limit = max(1, min(limit, 1000))
    clauses = ["p.deleted_at IS NULL"]
    params: list = []
    if q:
        sq = escape_like(q.strip())
        clauses.append("(p.register_no LIKE ? ESCAPE '\\' OR p.name LIKE ? ESCAPE '\\')")
        params.extend([f"%{sq}%", f"%{sq}%"])
    if school_code:
        clauses.append("p.school_code = ?")
        params.append(school_code)
    where = " WHERE " + " AND ".join(clauses)
    rows = db.q(
        "SELECT p.*, (SELECT COUNT(*) FROM participant_entries pe "  # noqa: S608
        "WHERE pe.participant_id = p.id AND pe.deleted_at IS NULL) AS entry_count "
        f"FROM participants p{where} ORDER BY p.school_code, p.register_no LIMIT ? OFFSET ?",
        tuple(params) + (limit, offset),
    )
    total = db.one(f"SELECT COUNT(*) c FROM participants p{where}", tuple(params))["c"]  # noqa: S608
    return {"participants": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}


@router.post("/participants")
def create_participant(body: ParticipantIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    now = db.now()
    try:
        cur = db.ex(
            "INSERT INTO participants(register_no, name, school_name, school_code, student_class, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (body.register_no, body.name, body.school_name, body.school_code, body.student_class, now, now),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "register_no_taken") from exc
    invalidate_public_cache(request.app)
    _audit(db, request, user, "participant_create", f"id={cur.lastrowid}")
    return dict(db.one("SELECT * FROM participants WHERE id = ?", (cur.lastrowid,)))


@router.post("/participants/import")
async def import_csv(request: Request, file: UploadFile = File(...), user=Depends(require_admin)):
    db = get_db(request)
    raw = await file.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(413, "csv_too_large")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(400, "csv_must_be_utf8") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(400, "csv_empty")
    missing = [c for c in _CSV_COLS if c not in reader.fieldnames]
    if missing:
        raise HTTPException(400, f"csv_missing_columns:{missing}")

    errors: list[str] = []
    cp = ce = up = ue = 0
    now = db.now()
    try:
        with db.transaction():
            for lineno, raw_row in enumerate(reader, start=2):
                row = {(k or "").strip(): (v or "").strip() for k, v in raw_row.items()}
                reg, sc, perf_date, item_code = row.get("register_no", ""), row.get("school_code", ""), row.get("perf_date", ""), row.get("item_code", "")
                if not _REG_RE.match(reg):
                    errors.append(f"line {lineno}: invalid register_no {reg!r}")
                    continue
                if not _SCHOOL_RE.match(sc):
                    errors.append(f"line {lineno}: invalid school_code {sc!r}")
                    continue
                try:
                    cls = int(row.get("class", ""))
                    venue_id = int(row.get("venue_id", ""))
                except ValueError:
                    errors.append(f"line {lineno}: invalid class or venue_id")
                    continue
                if not 1 <= cls <= 12 or not _DATE_RE.match(perf_date) or not item_code:
                    errors.append(f"line {lineno}: invalid class, perf_date, or item_code")
                    continue
                v_kind = "stage" if venue_id in _ON_STAGE_IDS else "off-stage"
                v_slug = f"stage-{venue_id}" if venue_id in _ON_STAGE_IDS else f"venue-{venue_id}"
                db.ex(
                    "INSERT INTO venues(id, name, kind, slug, active) VALUES (?,?,?,?,1) "
                    "ON CONFLICT(id) DO UPDATE SET name = excluded.name, kind = excluded.kind",
                    (venue_id, row["venue_name"], v_kind, v_slug),
                )
                ev_title = row.get("item_name") or row.get("title") or f"Item {item_code}"
                db.ex(
                    "INSERT INTO events(code, title, venue_id, day) VALUES (?,?,?,?) "
                    "ON CONFLICT(code) DO UPDATE SET venue_id = excluded.venue_id, day = COALESCE(events.day, excluded.day)",
                    (item_code, ev_title, venue_id, perf_date),
                )

                ex_p = db.one("SELECT * FROM participants WHERE register_no = ? AND deleted_at IS NULL", (reg,))
                if ex_p:
                    pid = ex_p["id"]
                    if (ex_p["name"] != row["name"] or ex_p["school_name"] != row["school_name"]
                            or ex_p["school_code"] != sc or ex_p["student_class"] != cls):
                        db.ex(
                            "UPDATE participants SET name = ?, school_name = ?, school_code = ?, student_class = ?, updated_at = ? WHERE id = ?",
                            (row["name"], row["school_name"], sc, cls, now, pid),
                        )
                        up += 1
                else:
                    pid = db.ex(
                        "INSERT INTO participants(register_no, name, school_name, school_code, student_class, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                        (reg, row["name"], row["school_name"], sc, cls, now, now),
                    ).lastrowid
                    cp += 1

                ex_e = db.one(
                    "SELECT * FROM participant_entries WHERE participant_id = ? AND item_code = ? AND deleted_at IS NULL",
                    (pid, item_code),
                )
                if ex_e:
                    if ex_e["venue_id"] != venue_id or ex_e["venue_name"] != row["venue_name"] or ex_e["perf_date"] != perf_date:
                        db.ex(
                            "UPDATE participant_entries SET venue_id = ?, venue_name = ?, perf_date = ?, updated_at = ? WHERE id = ?",
                            (venue_id, row["venue_name"], perf_date, now, ex_e["id"]),
                        )
                        ue += 1
                else:
                    if _active_entry_count(db, pid) >= MAX_ITEMS_PER_PARTICIPANT:
                        errors.append(f"line {lineno}: {reg} at {MAX_ITEMS_PER_PARTICIPANT} entries")
                        continue
                    db.ex(
                        "INSERT INTO participant_entries(participant_id, item_code, venue_id, venue_name, perf_date, created_at, updated_at) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (pid, item_code, venue_id, row["venue_name"], perf_date, now, now),
                    )
                    ce += 1
    except Exception as exc:
        raise HTTPException(500, "import_failed") from exc

    invalidate_public_cache(request.app)
    _audit(db, request, user, "participant_import", f"p+{cp}/p~{up}/e+{ce}/e~{ue}/err{len(errors)}")
    return {
        "ok": not errors,
        "participants_created": cp,
        "participants_updated": up,
        "entries_created": ce,
        "entries_updated": ue,
        "errors": errors,
    }


@router.get("/participants/export.csv")
def export_participants_csv(request: Request, user=Depends(require_admin)):
    rows = get_db(request).q(
        "SELECT p.register_no, p.name, p.school_name, p.school_code, p.student_class, "
        "pe.item_code, pe.venue_id, pe.venue_name, pe.perf_date "
        "FROM participants p "
        "LEFT JOIN participant_entries pe ON pe.participant_id = p.id AND pe.deleted_at IS NULL "
        "WHERE p.deleted_at IS NULL ORDER BY p.school_code, p.register_no, pe.perf_date, pe.item_code"
    )
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(_CSV_COLS)
    for r in rows:
        w.writerow([
            csv_cell(r["register_no"]),
            csv_cell(r["name"]),
            csv_cell(r["school_name"]),
            csv_cell(r["school_code"]),
            r["student_class"],
            csv_cell(r["item_code"]),
            r["venue_id"],
            csv_cell(r["venue_name"]),
            csv_cell(r["perf_date"]),
        ])
    return Response(
        content=out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=participants.csv"},
    )


@router.get("/participants/{pid}")
def get_participant(pid: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    row = _get_participant_or_404(db, pid)
    entries = db.q(
        "SELECT * FROM participant_entries WHERE participant_id = ? AND deleted_at IS NULL ORDER BY perf_date, item_code",
        (pid,),
    )
    return {"participant": dict(row), "entries": [dict(e) for e in entries]}


@router.put("/participants/{pid}")
def update_participant(pid: int, body: ParticipantUpdateIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    row = _get_participant_or_404(db, pid)
    try:
        reg, name, sname, scode, scls = _patch(row, body, "register_no", "name", "school_name", "school_code", "student_class", always_set_if_not_none=True)
        db.ex(
            "UPDATE participants SET register_no = ?, name = ?, school_name = ?, school_code = ?, student_class = ?, updated_at = ? "
            "WHERE id = ? AND deleted_at IS NULL",
            (reg, name, sname, scode, scls, db.now(), pid),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "register_no_taken") from exc
    _audit(db, request, user, "participant_update", f"id={pid}")
    return dict(db.one("SELECT * FROM participants WHERE id = ?", (pid,)))


@router.delete("/participants/{pid}")
def delete_participant(pid: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    _get_participant_or_404(db, pid)
    now = db.now()
    with db.transaction():
        db.ex("UPDATE participants SET deleted_at = ?, updated_at = ? WHERE id = ?", (now, now, pid))
        db.ex("UPDATE participant_entries SET deleted_at = ?, updated_at = ? WHERE participant_id = ? AND deleted_at IS NULL", (now, now, pid))
    invalidate_public_cache(request.app)
    _audit(db, request, user, "participant_delete", f"id={pid}")
    return {"ok": True}


@router.post("/participants/{pid}/entries")
def add_entry(pid: int, body: ParticipantEntryIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    _get_participant_or_404(db, pid)
    if _active_entry_count(db, pid) >= MAX_ITEMS_PER_PARTICIPANT:
        raise HTTPException(409, f"participant_at_{MAX_ITEMS_PER_PARTICIPANT}_items")
    now = db.now()
    try:
        cur = db.ex(
            "INSERT INTO participant_entries(participant_id, item_code, venue_id, venue_name, perf_date, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (pid, body.item_code, body.venue_id, body.venue_name, body.perf_date, now, now),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "duplicate_item_for_participant") from exc
    invalidate_public_cache(request.app)
    _audit(db, request, user, "entry_add", f"pid={pid},eid={cur.lastrowid}")
    return dict(db.one("SELECT * FROM participant_entries WHERE id = ?", (cur.lastrowid,)))


@router.put("/participants/{pid}/entries/{eid}")
def update_entry(pid: int, eid: int, body: ParticipantEntryUpdateIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    row = db.one("SELECT * FROM participant_entries WHERE id = ? AND participant_id = ? AND deleted_at IS NULL", (eid, pid))
    if not row:
        raise HTTPException(404, "entry_not_found")
    try:
        ic, vid, vname, pd = _patch(row, body, "item_code", "venue_id", "venue_name", "perf_date", always_set_if_not_none=True)
        db.ex(
            "UPDATE participant_entries SET item_code = ?, venue_id = ?, venue_name = ?, perf_date = ?, updated_at = ? WHERE id = ?",
            (ic, vid, vname, pd, db.now(), eid),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "duplicate_item_for_participant") from exc
    _audit(db, request, user, "entry_update", f"pid={pid},eid={eid}")
    return dict(db.one("SELECT * FROM participant_entries WHERE id = ?", (eid,)))


@router.delete("/participants/{pid}/entries/{eid}")
def delete_entry(pid: int, eid: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    if not db.one("SELECT id FROM participant_entries WHERE id = ? AND participant_id = ? AND deleted_at IS NULL", (eid, pid)):
        raise HTTPException(404, "entry_not_found")
    now = db.now()
    db.ex("UPDATE participant_entries SET deleted_at = ?, updated_at = ? WHERE id = ?", (now, now, eid))
    invalidate_public_cache(request.app)
    _audit(db, request, user, "entry_delete", f"pid={pid},eid={eid}")
    return {"ok": True}


# ── Staff Users Administration ────────────────────────────────────────────────
@router.get("/users")
def list_users(request: Request, user=Depends(require_admin)):
    rows = get_db(request).q("SELECT id, email, role, stages, is_active FROM users ORDER BY email")
    return {
        "users": [
            {"id": str(r["id"]), "email": r["email"], "stages": r["stages"], "roles": [r["role"]], "disabled": not r["is_active"]}
            for r in rows
        ]
    }


@router.post("/users")
def create_user(body: UserIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    _validate_stage_ids(db, body.stages)
    clean_email = body.email.strip().lower()
    try:
        cur = db.ex(
            "INSERT INTO users(email, password_hash, role, stages, is_active, token_version, created_at) "
            "VALUES (?,?,?,?,1,1,?)",
            (clean_email, ph.hash(body.password), body.role, json.dumps(body.stages), db.now()),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "email_taken") from exc
    _audit(db, request, user, "create_user", f"id={cur.lastrowid},role={body.role}")
    return {"id": str(cur.lastrowid), "email": clean_email, "role": body.role}


@router.put("/users/{uid}")
def update_user(uid: int, body: UserUpdateIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    if body.stages is not None:
        _validate_stage_ids(db, body.stages)
    target = _row_or_404(db, "users", uid, "not_found")
    if uid == user["id"] and (body.is_active is False or (body.role is not None and body.role != "admin")):
        raise HTTPException(400, "cannot_modify_own_access")

    email = body.email.strip().lower() if body.email is not None else target["email"]
    role = body.role if body.role is not None else target["role"]
    stages = json.dumps(body.stages) if body.stages is not None else target["stages"]
    active = int(body.is_active) if body.is_active is not None else target["is_active"]
    bump = 1 if (not active or role != target["role"]) else 0

    try:
        with db.transaction():
            db.ex(
                "UPDATE users SET email = ?, role = ?, stages = ?, is_active = ?, "
                "token_version = token_version + ? WHERE id = ?",
                (email, role, stages, active, bump, uid),
            )
            if not active:
                db.ex("UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?", (uid,))
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "email_taken") from exc
    _audit(db, request, user, "update_user", f"id={uid}")
    return {"ok": True}


@router.post("/users/{uid}/disable")
def disable_user(uid: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    _row_or_404(db, "users", uid, "not_found")
    if uid == user["id"]:
        raise HTTPException(400, "cannot_disable_self")
    with db.transaction():
        db.ex("UPDATE users SET is_active = 0, token_version = token_version + 1 WHERE id = ?", (uid,))
        db.ex("UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?", (uid,))
    _audit(db, request, user, "disable_user", f"id={uid}")
    return {"ok": True}


@router.post("/users/{uid}/enable")
def enable_user(uid: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    _row_or_404(db, "users", uid, "not_found")
    db.ex("UPDATE users SET is_active = 1 WHERE id = ?", (uid,))
    _audit(db, request, user, "enable_user", f"id={uid}")
    return {"ok": True}


@router.post("/users/{uid}/reset-password")
def reset_user_password(uid: int, body: PasswordResetIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    _row_or_404(db, "users", uid, "not_found")
    with db.transaction():
        db.ex("UPDATE users SET password_hash = ?, token_version = token_version + 1 WHERE id = ?", (ph.hash(body.password), uid))
        db.ex("UPDATE refresh_tokens SET revoked = 1 WHERE user_id = ?", (uid,))
    _audit(db, request, user, "reset_password", f"id={uid}")
    return {"ok": True}


# ── Audit / Stats / Health / Backup ───────────────────────────────────────────
@router.get("/audit")
def list_audit(request: Request, limit: int = 100, offset: int = 0, user=Depends(require_admin)):
    limit = max(1, min(limit, 500))
    return {"items": [dict(r) for r in get_db(request).q("SELECT * FROM auth_audit ORDER BY ts DESC LIMIT ? OFFSET ?", (limit, offset))]}


@router.get("/stats")
def stats(request: Request, user=Depends(require_admin)):
    row = get_db(request).one("""
        SELECT
            (SELECT COUNT(*) FROM venues) AS venues,
            (SELECT COUNT(*) FROM venues WHERE active = 1) AS active_venues,
            (SELECT COUNT(*) FROM events) AS events,
            (SELECT COUNT(*) FROM participants WHERE deleted_at IS NULL) AS participants,
            (SELECT COUNT(*) FROM participant_entries WHERE deleted_at IS NULL) AS entries,
            (SELECT COUNT(*) FROM photo_assets a JOIN photo_batches b ON b.id = a.batch_id
             WHERE a.kind = 'stage' AND b.status = 'published') AS photos_published
    """)
    return dict(row)


@router.get("/health")
def health(request: Request, user=Depends(require_admin)):
    db, cfg = get_db(request), get_cfg(request)
    try:
        db_bytes = os.stat(cfg.db_path).st_size
    except OSError:
        db_bytes = 0
    try:
        disk_free = shutil.disk_usage(cfg.db_path).free
    except OSError:
        disk_free = 0
    fails = db.one("SELECT COUNT(*) c FROM auth_audit WHERE event = 'login_fail' AND ts > ?", (db.now() - 3600,))["c"]
    return {
        "time": db.now(),
        "db_bytes": db_bytes,
        "sse_connections": len(request.app.state.subscribers),
        "disk_free_bytes": disk_free,
        "recent_auth_failures": fails,
    }


@router.post("/backup")
def backup(request: Request, user=Depends(require_admin)):
    db, cfg = get_db(request), get_cfg(request)
    dst_dir = Path(cfg.db_path).parent / "backups"
    dst_dir.mkdir(parents=True, exist_ok=True)
    src = Path(cfg.db_path)
    if not src.exists():
        raise HTTPException(500, "db_not_found")
    dst = dst_dir / f"{src.stem}-{_t.strftime('%Y%m%d-%H%M%S')}.db"
    src_con, dst_con = sqlite3.connect(str(src)), sqlite3.connect(str(dst))
    try:
        src_con.backup(dst_con)
    finally:
        dst_con.close()
        src_con.close()
    for old in sorted(dst_dir.glob(f"{src.stem}-*.db"), key=lambda f: f.stat().st_mtime)[:-24]:
        try:
            old.unlink()
        except OSError:
            pass
    _audit(db, request, user, "backup", f"file={dst.name}")
    return {"ok": True, "backups": [str(dst)]}




@router.post("/wipe")
def wipe_database(request: Request, user=Depends(require_admin)):
    db = get_db(request)
    with db.transaction():
        for tbl in (
            "photo_asset_entries",
            "photo_assets",
            "photo_batches",
            "participant_entries",
            "participants",
            "events",
            "live_state",
            "venues",
        ):
            db.ex(f"DELETE FROM {tbl}")  # noqa: S608
    invalidate_public_cache(request.app)
    _audit(db, request, user, "wipe_database", "all_festival_data_cleared")
    return {"ok": True}


# ── Device 3 Obs Worker Internal Endpoints ────────────────────────────────────
@internal_router.get("/backup")
def download_backup(request: Request, _=Depends(require_worker("obs"))):
    src_path = Path(get_cfg(request).db_path)
    if not src_path.exists():
        raise HTTPException(500, "db_not_found")
    temp_dir = tempfile.mkdtemp(prefix="kal-bak-")
    tmp_file = Path(temp_dir) / "kalolsavam.db"
    src_con, dst_con = sqlite3.connect(str(src_path)), sqlite3.connect(str(tmp_file))
    try:
        src_con.backup(dst_con)
    except BaseException:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    finally:
        dst_con.close()
        src_con.close()
    return FileResponse(
        tmp_file,
        media_type="application/x-sqlite3",
        filename="kalolsavam.db",
        background=BackgroundTask(shutil.rmtree, temp_dir, ignore_errors=True),
    )


@internal_router.get("/audit-export")
def export_audit_logs(request: Request, since: float = 0.0, limit: int = 500, _=Depends(require_worker("obs"))):
    limit = max(1, min(limit, 1000))
    rows = get_db(request).q(
        "SELECT id, ts, username, ip_hash, event, detail FROM auth_audit WHERE ts > ? ORDER BY ts ASC LIMIT ?",
        (since, limit),
    )
    return {"items": [dict(r) for r in rows]}
