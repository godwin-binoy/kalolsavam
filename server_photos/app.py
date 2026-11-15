import os
import shutil
import uuid
import httpx
from pathlib import Path
from typing import List
import jwt
from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session, select
from .models import init_db, PhotoBatch, PhotoAsset, PhotoAssetEntry


import logging
import queue
import threading
import requests
import time

class HttpLogHandler(logging.Handler):
    def __init__(self, url, service, token):
        super().__init__()
        self.url = url
        self.service = service
        self.token = token
        self.queue = queue.Queue()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
    def emit(self, record):
        self.queue.put({"service": self.service, "level": record.levelname, "msg": record.getMessage()})
    def _worker(self):
        while True:
            batch = []
            try:
                batch.append(self.queue.get(timeout=2))
                while len(batch) < 100:
                    batch.append(self.queue.get_nowait())
            except queue.Empty:
                pass
            if batch:
                try:
                    requests.post(self.url, json={"logs": batch}, headers={"X-Obs-Token": self.token}, timeout=5)
                except Exception:
                    pass
            time.sleep(0.5)


log = logging.getLogger("photos")
log.setLevel(logging.INFO)

app = FastAPI(title="Kalolsavam Photos")
SECRET_KEY = os.getenv("SECRET_KEY", "")
CORE_URL = os.getenv("CORE_URL", "http://backend:8000")
OBS_URL = os.getenv("OBS_URL")
if OBS_URL:
    log.addHandler(HttpLogHandler(OBS_URL, "photos", SECRET_KEY))
PHOTOS_ROOT = Path(os.getenv("PHOTOS_ROOT", "/app/photos_data"))
PHOTOS_ROOT.mkdir(parents=True, exist_ok=True)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
engine = init_db(os.getenv("PHOTOS_DB_PATH", "sqlite:////app/photos_data/photos.db"))

def get_db():
    with Session(engine) as session:
        yield session

def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "unauthorized")
    try:
        payload = jwt.decode(authorization.split(" ")[1], SECRET_KEY, algorithms=["HS256"])
        return payload
    except Exception:
        raise HTTPException(401, "invalid_token")

# -----------------------------------------------------------------------------
# Upload & Batch Management
# -----------------------------------------------------------------------------
class BatchCreate(BaseModel):
    queue_item_id: int
    venue_id: int
    perf_date: str
    workflow: str

@app.post("/api/v1/photos/batches")
def create_batch(body: BatchCreate, db: Session = Depends(get_db), user=Depends(verify_token)):
    b = PhotoBatch(
        queue_item_id=body.queue_item_id, venue_id=body.venue_id,
        perf_date=body.perf_date, workflow=body.workflow,
        status="queued" if body.workflow == "bulk" else "staging"
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return {"batch_id": b.id}

@app.post("/api/v1/photos/batches/{batch_id}/upload")
def upload_file(
    batch_id: int, kind: str = Form(...), file: UploadFile = File(...),
    db: Session = Depends(get_db), user=Depends(verify_token)
):
    b = db.get(PhotoBatch, batch_id)
    if not b: raise HTTPException(404, "batch_not_found")
    
    batch_dir = PHOTOS_ROOT / str(batch_id)
    batch_dir.mkdir(exist_ok=True)
    ext = Path(file.filename).suffix or ".jpg"
    fname = f"{uuid.uuid4().hex}{ext}"
    fpath = batch_dir / fname
    
    with open(fpath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    asset = PhotoAsset(batch_id=batch_id, kind=kind, filename=fname)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {"asset_id": asset.id}

# -----------------------------------------------------------------------------
# Data Worker Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/v1/photos/batches")
def list_batches(db: Session = Depends(get_db), user=Depends(verify_token)):
    batches = db.query(PhotoBatch).filter(PhotoBatch.status == "queued").all()
    return {"batches": batches}

@app.get("/api/v1/photos/batches/{batch_id}")
def get_batch(batch_id: int, db: Session = Depends(get_db), user=Depends(verify_token)):
    b = db.get(PhotoBatch, batch_id)
    if not b: raise HTTPException(404, "batch_not_found")
    assets = db.query(PhotoAsset).filter(PhotoAsset.batch_id == batch_id).all()
    
    # Get assignments
    assigned = db.query(PhotoAssetEntry).filter(PhotoAssetEntry.photo_asset_id.in_([a.id for a in assets])).all()
    assignments = {}
    for a in assigned:
        assignments.setdefault(a.photo_asset_id, []).append(a.participant_entry_id)
        
    out_assets = []
    for a in assets:
        out_assets.append({
            "id": a.id, "kind": a.kind, "filename": a.filename,
            "url": f"/api/v1/photos/assets/{a.id}/view",
            "assigned_to": assignments.get(a.id, [])
        })
    return {"batch": b, "assets": out_assets}

@app.post("/api/v1/photos/batches/{batch_id}/publish")
def publish_batch(batch_id: int, db: Session = Depends(get_db), user=Depends(verify_token)):
    b = db.get(PhotoBatch, batch_id)
    if not b: raise HTTPException(404, "batch_not_found")
    b.status = "published"
    db.commit()
    return {"ok": True}

class AssignIn(BaseModel):
    asset_id: int
    participant_entry_ids: List[int]

@app.post("/api/v1/photos/assign")
def assign_photo(body: AssignIn, db: Session = Depends(get_db), user=Depends(verify_token)):
    for eid in body.participant_entry_ids:
        # Check if exists to avoid duplicates
        exists = db.query(PhotoAssetEntry).filter_by(photo_asset_id=body.asset_id, participant_entry_id=eid).first()
        if not exists:
            pae = PhotoAssetEntry(photo_asset_id=body.asset_id, participant_entry_id=eid, source="data_worker")
            db.add(pae)
    db.commit()
    return {"ok": True}

@app.get("/api/v1/photos/assets/{asset_id}/view")
def view_asset(asset_id: int, db: Session = Depends(get_db)):
    # Note: view is public (unguessable UUID filename)
    a = db.get(PhotoAsset, asset_id)
    if not a: raise HTTPException(404, "not_found")
    return FileResponse(PHOTOS_ROOT / str(a.batch_id) / a.filename)

# -----------------------------------------------------------------------------
# Public Lookup (Privacy Gate -> Core Server -> Photo DB)
# -----------------------------------------------------------------------------
class LookupIn(BaseModel):
    register_no: str
    name: str

@app.post("/api/v1/photos/public/lookup")
def public_lookup(body: LookupIn, db: Session = Depends(get_db)):
    # 1. Verify with Core Server
    try:
        r = httpx.post(f"{CORE_URL}/api/v1/public/participant-lookup", json=body.model_dump(), timeout=5)
        if r.status_code != 200:
            raise HTTPException(404, "participant_not_found_or_name_mismatch")
        core_data = r.json()
    except httpx.RequestError:
        raise HTTPException(502, "core_server_unreachable")
        
    entries = core_data.get("entries", [])
    entry_ids = [e["id"] for e in entries]
    if not entry_ids:
        return {"valid": True, "photos": []}
        
    # 2. Fetch photos for these entries
    assignments = db.query(PhotoAssetEntry).filter(PhotoAssetEntry.participant_entry_id.in_(entry_ids)).all()
    asset_ids = list(set(a.photo_asset_id for a in assignments))
    
    photos = []
    if asset_ids:
        assets = db.query(PhotoAsset).filter(PhotoAsset.id.in_(asset_ids), PhotoAsset.kind == "stage").all()
        for a in assets:
            photos.append({
                "asset_id": a.id,
                "url": f"/api/v1/photos/assets/{a.id}/view",
                "entries": [e["item_code"] for e in entries if any(pe.participant_entry_id == e["id"] and pe.photo_asset_id == a.id for pe in assignments)]
            })
            
    return {"valid": True, "participant": core_data.get("participant"), "photos": photos}

@app.get("/healthz")
def health():
    return {"ok": True, "service": "photos"}
