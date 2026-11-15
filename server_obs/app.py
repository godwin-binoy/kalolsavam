import os
import asyncio
from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, select, func
from .models import init_db, LogEntry
from .backup import hourly_backup_job

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(hourly_backup_job())
    yield
    task.cancel()

app = FastAPI(title="Kalolsavam Obs", lifespan=lifespan)
SECRET_KEY = os.getenv("SECRET_KEY", "")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

engine = init_db(os.getenv("OBS_DB_PATH", "sqlite:////app/obs_data/obs.db"))

def get_db():
    with Session(engine) as session:
        yield session

def verify_token(x_obs_token: str = Header(None)):
    if not x_obs_token or x_obs_token != SECRET_KEY:
        raise HTTPException(403, "invalid_token")

class LogItem(BaseModel):
    service: str
    level: str
    msg: str
    request_id: str | None = None
    method: str | None = None
    path: str | None = None
    status: int | None = None
    duration_ms: int | None = None
    client_ip: str | None = None

class LogBatch(BaseModel):
    logs: List[LogItem]

@app.post("/api/v1/obs/logs")
def receive_logs(req: LogBatch, db: Session = Depends(get_db), _=Depends(verify_token)):
    for item in req.logs:
        db.add(LogEntry(**item.model_dump()))
    db.commit()
    return {"ok": True, "count": len(req.logs)}

@app.get("/api/v1/obs/stats")
def get_stats(db: Session = Depends(get_db), _=Depends(verify_token)):
    total = db.exec(select(func.count()).select_from(LogEntry)).one()
    errors = db.exec(select(func.count()).select_from(LogEntry).where(LogEntry.level == "ERROR")).one()
    
    # Simple aggregation
    services = db.exec(select(LogEntry.service, func.count(LogEntry.id)).group_by(LogEntry.service)).all()
    
    return {
        "total_requests": total,
        "total_errors": errors,
        "services": [{"name": s[0], "count": s[1]} for s in services]
    }

@app.get("/api/v1/obs/logs")
def get_logs(limit: int = 100, db: Session = Depends(get_db), _=Depends(verify_token)):
    logs = db.exec(select(LogEntry).order_by(LogEntry.ts.desc()).limit(limit)).all()
    return {"logs": logs}

@app.get("/healthz")
def health():
    return {"ok": True, "service": "obs"}
