import asyncio
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .backup import hourly_backup_job

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the hourly backup task in the background
    task = asyncio.create_task(hourly_backup_job())
    yield
    task.cancel()

app = FastAPI(title="Kalolsavam Obs", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/healthz")
def health():
    return {"ok": True, "service": "obs"}
