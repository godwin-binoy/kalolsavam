"""Participant registry admin API: CRUD for participants + entries, CSV I/O.

All routes require admin. Soft delete via ``deleted_at``. Enforces the 7-items
per-participant cap. CSV import is one row per entry (register info repeated).
"""
from __future__ import annotations

import csv
import io
import re
import sqlite3

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response

from ..deps import client_ip, get_cfg, get_db, hash_ip, require_admin
from ..models import (
    ParticipantEntryIn,
    ParticipantEntryUpdateIn,
    ParticipantIn,
    ParticipantUpdateIn,
)

router = APIRouter()

MAX_ITEMS_PER_PARTICIPANT = 7
_REG_RE = re.compile(r"^\d{5}$")
_SCHOOL_RE = re.compile(r"^\d{5,6}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _audit(db, request: Request, user, action: str, detail: str = "") -> None:
    try:
        secret = get_cfg(request).secret_key
        email = getattr(user, "email", "admin")
        db.ex(
            "INSERT INTO auth_audit(ts, username, ip_hash, event, detail) "
            "VALUES (?,?,?,?,?)",
            (db.now(), email, hash_ip(client_ip(request), secret),
             "admin_action", f"participant_{action}|{detail}"),
        )
    except Exception as exc:
        import logging
        logging.getLogger("kalolsavam").debug("audit failed: %s", exc)


def _get_participant_or_404(db, participant_id: int):
    row = db.one(
        "SELECT * FROM participants WHERE id = ? AND deleted_at IS NULL",
        (participant_id,),
    )
    if not row:
        raise HTTPException(404, "participant_not_found")
    return row


def _active_entry_count(db, participant_id: int) -> int:
    return db.one(
        "SELECT COUNT(*) c FROM participant_entries "
        "WHERE participant_id = ? AND deleted_at IS NULL",
        (participant_id,),
    )["c"]


def _csv_cell(val: object) -> str:
    s = "" if val is None else str(val)
    stripped = s.lstrip()
    if stripped and stripped[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s


# ── Participants ────────────────────────────────────────────────────────
@router.get("/participants")
def list_participants(
    request: Request,
    q: str | None = None,
    school_code: str | None = None,
    item_code: str | None = None,
    venue_id: int | None = None,
    day: str | None = None,
    include_deleted: bool = False,
    limit: int = 200,
    offset: int = 0,
    user=Depends(require_admin),
):
    db = get_db(request)
    limit = max(1, min(limit, 1000))
    clauses: list[str] = []
    params: list = []
    if not include_deleted:
        clauses.append("p.deleted_at IS NULL")
    if q:
        clauses.append("(p.register_no LIKE ? OR p.name LIKE ?)")
        params.extend([f"%{q}%", f"%{q}%"])
    if school_code:
        clauses.append("p.school_code = ?")
        params.append(school_code)

    entry_filter = ""
    entry_params: list = []
    if item_code or venue_id is not None or day:
        entry_clauses = ["pe.deleted_at IS NULL"]
        if item_code:
            entry_clauses.append("pe.item_code = ?")
            entry_params.append(item_code)
        if venue_id is not None:
            entry_clauses.append("pe.venue_id = ?")
            entry_params.append(venue_id)
        if day:
            entry_clauses.append("pe.perf_date = ?")
            entry_params.append(day)
        entry_filter = (
            " AND p.id IN (SELECT participant_id FROM participant_entries pe "
            "WHERE " + " AND ".join(entry_clauses) + ")"  # noqa: S608  # noqa: S608
        )
        params.extend(entry_params)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = (
        "SELECT p.*, "
        "(SELECT COUNT(*) FROM participant_entries pe "
        " WHERE pe.participant_id = p.id AND pe.deleted_at IS NULL) AS entry_count "
        "FROM participants p" + where + entry_filter +  # noqa: S608  # noqa: S608
        " ORDER BY p.school_code, p.register_no LIMIT ? OFFSET ?"
    )
    rows = db.q(sql, tuple(params) + (limit, offset))
    total = db.one(
        "SELECT COUNT(*) c FROM participants p" + where + entry_filter,  # noqa: S608
        tuple(params),
    )["c"]
    return {"participants": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}


@router.post("/participants")
def create_participant(body: ParticipantIn, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    now = db.now()
    try:
        cur = db.ex(
            "INSERT INTO participants(register_no, name, school_name, school_code, "
            " student_class, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (body.register_no, body.name, body.school_name, body.school_code,
             body.student_class, now, now),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "register_no_taken") from exc
    _audit(db, request, user, "create", f"id={cur.lastrowid}")
    return dict(db.one("SELECT * FROM participants WHERE id = ?", (cur.lastrowid,)))


@router.get("/participants/{participant_id}")
def get_participant(participant_id: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    row = _get_participant_or_404(db, participant_id)
    entries = db.q(
        "SELECT * FROM participant_entries WHERE participant_id = ? "
        "AND deleted_at IS NULL ORDER BY perf_date, item_code",
        (participant_id,),
    )
    return {"participant": dict(row), "entries": [dict(e) for e in entries]}


@router.put("/participants/{participant_id}")
def update_participant(
    participant_id: int,
    body: ParticipantUpdateIn,
    request: Request,
    user=Depends(require_admin),
):
    db = get_db(request)
    row = _get_participant_or_404(db, participant_id)
    fields = body.model_fields_set
    register_no = body.register_no if "register_no" in fields else row["register_no"]
    name = body.name if "name" in fields else row["name"]
    school_name = body.school_name if "school_name" in fields else row["school_name"]
    school_code = body.school_code if "school_code" in fields else row["school_code"]
    student_class = (
        body.student_class if "student_class" in fields and body.student_class is not None
        else row["student_class"]
    )
    try:
        db.ex(
            "UPDATE participants SET register_no = ?, name = ?, school_name = ?, "
            " school_code = ?, student_class = ?, updated_at = ? "
            "WHERE id = ? AND deleted_at IS NULL",
            (register_no, name, school_name, school_code, student_class, db.now(), participant_id),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "register_no_taken") from exc
    _audit(db, request, user, "update", f"id={participant_id}")
    return dict(db.one("SELECT * FROM participants WHERE id = ?", (participant_id,)))


@router.delete("/participants/{participant_id}")
def delete_participant(participant_id: int, request: Request, user=Depends(require_admin)):
    db = get_db(request)
    _get_participant_or_404(db, participant_id)
    now = db.now()
    with db.transaction():
        db.ex("UPDATE participants SET deleted_at = ?, updated_at = ? WHERE id = ?",
              (now, now, participant_id))
        db.ex("UPDATE participant_entries SET deleted_at = ?, updated_at = ? "
              "WHERE participant_id = ? AND deleted_at IS NULL",
              (now, now, participant_id))
    _audit(db, request, user, "soft_delete", f"id={participant_id}")
    return {"ok": True}


# ── Entries ─────────────────────────────────────────────────────────────
@router.post("/participants/{participant_id}/entries")
def add_entry(
    participant_id: int,
    body: ParticipantEntryIn,
    request: Request,
    user=Depends(require_admin),
):
    db = get_db(request)
    _get_participant_or_404(db, participant_id)
    if _active_entry_count(db, participant_id) >= MAX_ITEMS_PER_PARTICIPANT:
        raise HTTPException(409, f"participant_at_{MAX_ITEMS_PER_PARTICIPANT}_items")
    now = db.now()
    try:
        cur = db.ex(
            "INSERT INTO participant_entries(participant_id, item_code, venue_id, "
            " venue_name, perf_date, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (participant_id, body.item_code, body.venue_id, body.venue_name,
             body.perf_date, now, now),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "duplicate_item_for_participant") from exc
    _audit(db, request, user, "entry_add", f"pid={participant_id},eid={cur.lastrowid}")
    return dict(db.one("SELECT * FROM participant_entries WHERE id = ?", (cur.lastrowid,)))


@router.put("/participants/{participant_id}/entries/{entry_id}")
def update_entry(
    participant_id: int,
    entry_id: int,
    body: ParticipantEntryUpdateIn,
    request: Request,
    user=Depends(require_admin),
):
    db = get_db(request)
    row = db.one(
        "SELECT * FROM participant_entries WHERE id = ? AND participant_id = ? "
        "AND deleted_at IS NULL",
        (entry_id, participant_id),
    )
    if not row:
        raise HTTPException(404, "entry_not_found")
    fields = body.model_fields_set
    item_code = body.item_code if "item_code" in fields and body.item_code else row["item_code"]
    venue_id = body.venue_id if "venue_id" in fields and body.venue_id is not None else row["venue_id"]
    venue_name = body.venue_name if "venue_name" in fields and body.venue_name else row["venue_name"]
    perf_date = body.perf_date if "perf_date" in fields and body.perf_date else row["perf_date"]
    try:
        db.ex(
            "UPDATE participant_entries SET item_code = ?, venue_id = ?, venue_name = ?, "
            " perf_date = ?, updated_at = ? WHERE id = ?",
            (item_code, venue_id, venue_name, perf_date, db.now(), entry_id),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(409, "duplicate_item_for_participant") from exc
    _audit(db, request, user, "entry_update", f"pid={participant_id},eid={entry_id}")
    return dict(db.one("SELECT * FROM participant_entries WHERE id = ?", (entry_id,)))


@router.delete("/participants/{participant_id}/entries/{entry_id}")
def delete_entry(
    participant_id: int,
    entry_id: int,
    request: Request,
    user=Depends(require_admin),
):
    db = get_db(request)
    row = db.one(
        "SELECT * FROM participant_entries WHERE id = ? AND participant_id = ? "
        "AND deleted_at IS NULL",
        (entry_id, participant_id),
    )
    if not row:
        raise HTTPException(404, "entry_not_found")
    now = db.now()
    db.ex("UPDATE participant_entries SET deleted_at = ?, updated_at = ? WHERE id = ?",
          (now, now, entry_id))
    _audit(db, request, user, "entry_soft_delete", f"pid={participant_id},eid={entry_id}")
    return {"ok": True}


# ── CSV import / export ─────────────────────────────────────────────────
_CSV_COLS = ("register_no", "name", "school_name", "school_code", "class",
             "item_code", "venue_id", "venue_name", "perf_date")


@router.post("/participants/import")
async def import_csv(
    request: Request,
    file: UploadFile = File(...),
    user=Depends(require_admin),
):
    db = get_db(request)
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(400, "csv_must_be_utf8") from None
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(400, "csv_empty")
    missing = [c for c in _CSV_COLS if c not in reader.fieldnames]
    if missing:
        raise HTTPException(400, f"csv_missing_columns:{missing}")

    errors: list[str] = []
    created_p = 0
    created_e = 0
    updated_p = 0
    updated_e = 0
    now = db.now()

    try:
        with db.transaction():
            for lineno, raw_row in enumerate(reader, start=2):
                row = {(k or "").strip(): (v or "").strip() for k, v in raw_row.items()}
                reg = row.get("register_no", "")
                if not _REG_RE.match(reg):
                    errors.append(f"line {lineno}: invalid register_no {reg!r}")
                    continue
                sc = row.get("school_code", "")
                if not _SCHOOL_RE.match(sc):
                    errors.append(f"line {lineno}: invalid school_code {sc!r}")
                    continue
                try:
                    cls = int(row.get("class", ""))
                except ValueError:
                    errors.append(f"line {lineno}: invalid class {row.get('class')!r}")
                    continue
                if not 1 <= cls <= 12:
                    errors.append(f"line {lineno}: class out of range")
                    continue
                perf_date = row.get("perf_date", "")
                if not _DATE_RE.match(perf_date):
                    errors.append(f"line {lineno}: invalid perf_date {perf_date!r}")
                    continue
                try:
                    venue_id = int(row.get("venue_id", ""))
                except ValueError:
                    errors.append(f"line {lineno}: invalid venue_id {row.get('venue_id')!r}")
                    continue
                item_code = row.get("item_code", "")
                if not item_code:
                    errors.append(f"line {lineno}: missing item_code")
                    continue

                existing = db.one(
                    "SELECT * FROM participants WHERE register_no = ? AND deleted_at IS NULL",
                    (reg,),
                )
                if existing:
                    pid = existing["id"]
                    if (existing["name"] != row["name"]
                            or existing["school_code"] != sc
                            or existing["student_class"] != cls):
                        db.ex(
                            "UPDATE participants SET name = ?, school_name = ?, "
                            " school_code = ?, student_class = ?, updated_at = ? "
                            "WHERE id = ?",
                            (row["name"], row["school_name"], sc, cls, now, pid),
                        )
                        updated_p += 1
                else:
                    cur = db.ex(
                        "INSERT INTO participants(register_no, name, school_name, "
                        " school_code, student_class, created_at, updated_at) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (reg, row["name"], row["school_name"], sc, cls, now, now),
                    )
                    pid = cur.lastrowid
                    created_p += 1

                entry = db.one(
                    "SELECT * FROM participant_entries WHERE participant_id = ? "
                    "AND item_code = ? AND deleted_at IS NULL",
                    (pid, item_code),
                )
                if entry:
                    if (entry["venue_id"] != venue_id
                            or entry["venue_name"] != row["venue_name"]
                            or entry["perf_date"] != perf_date):
                        db.ex(
                            "UPDATE participant_entries SET venue_id = ?, venue_name = ?, "
                            " perf_date = ?, updated_at = ? WHERE id = ?",
                            (venue_id, row["venue_name"], perf_date, now, entry["id"]),
                        )
                        updated_e += 1
                else:
                    if _active_entry_count(db, pid) >= MAX_ITEMS_PER_PARTICIPANT:
                        errors.append(
                            f"line {lineno}: {reg} already has {MAX_ITEMS_PER_PARTICIPANT} entries"
                        )
                        continue
                    try:
                        db.ex(
                            "INSERT INTO participant_entries(participant_id, item_code, "
                            " venue_id, venue_name, perf_date, created_at, updated_at) "
                            "VALUES (?,?,?,?,?,?,?)",
                            (pid, item_code, venue_id, row["venue_name"], perf_date, now, now),
                        )
                        created_e += 1
                    except sqlite3.IntegrityError:
                        errors.append(f"line {lineno}: duplicate entry for {reg}/{item_code}")
    except Exception as exc:
        raise HTTPException(500, f"import_failed:{exc}") from exc

    _audit(db, request, user, "import",
           f"p+{created_p}/p~{updated_p}/e+{created_e}/e~{updated_e}/err{len(errors)}")
    return {
        "ok": len(errors) == 0,
        "participants_created": created_p,
        "participants_updated": updated_p,
        "entries_created": created_e,
        "entries_updated": updated_e,
        "errors": errors,
    }


@router.get("/participants/export.csv")
def export_participants_csv(request: Request, user=Depends(require_admin)):
    db = get_db(request)
    rows = db.q(
        "SELECT p.register_no, p.name, p.school_name, p.school_code, p.student_class, "
        " pe.item_code, pe.venue_id, pe.venue_name, pe.perf_date "
        "FROM participants p "
        "LEFT JOIN participant_entries pe ON pe.participant_id = p.id AND pe.deleted_at IS NULL "
        "WHERE p.deleted_at IS NULL "
        "ORDER BY p.school_code, p.register_no, pe.perf_date, pe.item_code"
    )
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(_CSV_COLS)
    for r in rows:
        w.writerow([
            _csv_cell(r["register_no"]),
            _csv_cell(r["name"]),
            _csv_cell(r["school_name"]),
            _csv_cell(r["school_code"]),
            r["student_class"],
            _csv_cell(r["item_code"]),
            r["venue_id"],
            _csv_cell(r["venue_name"]),
            _csv_cell(r["perf_date"]),
        ])
    return Response(
        content=out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=participants.csv"},
    )
