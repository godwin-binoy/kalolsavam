"""Core Photo API: Handles uploads, downloads, and assignment."""
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from ..deps import get_cfg, get_db, require_admin, require_staff

router = APIRouter()

def _get_storage(request) -> Path:
    cfg = get_cfg(request)
    p = Path(cfg.db_path).parent / "photos"
    p.mkdir(parents=True, exist_ok=True)
    return p

@router.post("/batches")
def create_batch(
    queue_item_id: int = Form(...),
    venue_id: int = Form(...),
    workflow: str = Form(...),
    request = None,
    user=Depends(require_staff)
):
    db = get_db(request)
    with db.transaction():
        cur = db.ex(
            "INSERT INTO photo_batches(queue_item_id, venue_id, workflow, status, created_at) "
            "VALUES (?,?,?,?,?)",
            (queue_item_id, venue_id, workflow, 'staging' if workflow=='quick' else 'queued', db.now())
        )
    return {"batch_id": cur.lastrowid}

@router.post("/batches/{batch_id}/upload")
def upload_file(
    batch_id: int,
    kind: str = Form(...),
    file: UploadFile = File(...),
    request = None,
    user=Depends(require_staff)
):
    db = get_db(request)
    b = db.one("SELECT id FROM photo_batches WHERE id = ?", (batch_id,))
    if not b:
        raise HTTPException(404, "batch_not_found")
    
    storage = _get_storage(request)
    ext = Path(file.filename).suffix or ".jpg"
    fname = f"{uuid.uuid4().hex}{ext}"
    fpath = storage / fname
    
    with open(fpath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    with db.transaction():
        cur = db.ex(
            "INSERT INTO photo_assets(batch_id, kind, filename, uploaded_at) VALUES (?,?,?,?)",
            (batch_id, kind, fname, db.now())
        )
    return {"asset_id": cur.lastrowid}

@router.get("/batches")
def list_batches(request = None, user=Depends(require_staff)):
    db = get_db(request)
    batches = db.q("SELECT * FROM photo_batches WHERE status = 'queued'")
    return {"batches": [dict(b) for b in batches]}

@router.get("/batches/{batch_id}")
def get_batch(batch_id: int, request = None, user=Depends(require_staff)):
    db = get_db(request)
    b = db.one("SELECT * FROM photo_batches WHERE id = ?", (batch_id,))
    if not b:
        raise HTTPException(404, "not_found")
    assets = db.q("SELECT * FROM photo_assets WHERE batch_id = ?", (batch_id,))
    
    out = []
    for a in assets:
        assigned = db.q("SELECT participant_entry_id FROM photo_asset_entries WHERE photo_asset_id = ?", (a["id"],))
        out.append({
            "id": a["id"], "kind": a["kind"], "filename": a["filename"],
            "url": f"/api/v1/photos/assets/{a['id']}/view",
            "assigned_to": [x["participant_entry_id"] for x in assigned]
        })
    return {"batch": dict(b), "assets": out}

class AssignIn(BaseModel):
    asset_id: int
    participant_entry_ids: list[int]

@router.post("/assign")
def assign_photo(body: AssignIn, request = None, user=Depends(require_staff)):
    db = get_db(request)
    with db.transaction():
        for eid in body.participant_entry_ids:
            db.ex("INSERT OR IGNORE INTO photo_asset_entries(photo_asset_id, participant_entry_id, source) VALUES (?,?,?)", (body.asset_id, eid, 'stagemaster_quick'))
    return {"ok": True}

@router.post("/batches/{batch_id}/publish")
def publish_batch(batch_id: int, request = None, user=Depends(require_staff)):
    db = get_db(request)
    db.ex("UPDATE photo_batches SET status = 'published' WHERE id = ?", (batch_id,))
    return {"ok": True}

@router.get("/assets/{asset_id}/view")
def view_asset(asset_id: int, request = None):
    db = get_db(request)
    a = db.one("SELECT filename, batch_id FROM photo_assets WHERE id = ?", (asset_id,))
    if not a:
        raise HTTPException(404, "not_found")
    fpath = _get_storage(request) / a["filename"]
    if not fpath.exists():
        raise HTTPException(404, "file_missing")
    return FileResponse(fpath)

@router.post("/public/lookup")
def public_lookup(register_no: str, name: str, request = None):
    # Same lookup logic as before, but served locally by Core
        db = get_db(request)
    p = db.one("SELECT id FROM participants WHERE register_no = ? AND lower(name) = lower(?) AND deleted_at IS NULL", (register_no, name))
    if not p:
        raise HTTPException(404, "not_found")
    
    entries = db.q("SELECT id, item_code FROM participant_entries WHERE participant_id = ? AND deleted_at IS NULL", (p["id"],))
    eids = [e["id"] for e in entries]
    if not eids:
        return {"photos": []}
    
    placeholders = ",".join(["?"] * len(eids))
    photos = db.q(f"SELECT photo_asset_id FROM photo_asset_entries WHERE participant_entry_id IN ({placeholders})"  # noqa: S608, tuple(eids))
    aids = list(set([x["photo_asset_id"] for x in photos]))
    if not aids:
        return {"photos": []}
    
    placeholders = ",".join(["?"] * len(aids))
    assets = db.q(f"SELECT id FROM photo_assets WHERE id IN ({placeholders}) AND kind = 'stage'"  # noqa: S608, tuple(aids))
    
    return {"photos": [{"asset_id": a["id"], "url": f"/api/v1/photos/assets/{a['id']}/view", "entries": [e["item_code"] for e in entries]} for a in assets]}

@router.post("/internal/queue/pull")
def pull_queue(request = None, _=Depends(require_admin)):
    """Worker endpoint: Fetch next batch to process."""
    db = get_db(request)
    b = db.one("SELECT * FROM photo_batches WHERE status = 'queued' LIMIT 1")
    if not b:
        return {"batch": None}
    
    # Mark as processing so no other worker grabs it
    db.ex("UPDATE photo_batches SET status = 'processing' WHERE id = ?", (b["id"],))
    assets = db.q("SELECT id, kind, filename FROM photo_assets WHERE batch_id = ?", (b["id"],))
    return {"batch": dict(b), "assets": [dict(a) for a in assets]}

@router.post("/internal/result")
def upload_result(request = None, _=Depends(require_admin)):
    return {"ok": True}
