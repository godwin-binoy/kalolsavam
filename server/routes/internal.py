"""Internal endpoints for inter-server communication (Obs server)."""
from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import FileResponse

router = APIRouter()

@router.get("/backup")
def download_backup(request: Request, x_obs_token: str = Header(None)):
    """Hot-backup the DB and stream it to the Obs server."""
    cfg = request.app.state.cfg
    if not x_obs_token or x_obs_token != cfg.secret_key:
        raise HTTPException(403, "invalid_token")

    src_path = Path(cfg.db_path)
    if not src_path.exists():
        raise HTTPException(500, "db_not_found")

    # Create a hot backup to a temp file
    temp_dir = tempfile.mkdtemp()
    tmp_file = Path(temp_dir) / "backup.db"
    
    src_con = sqlite3.connect(str(src_path))
    dst_con = sqlite3.connect(str(tmp_file))
    try:
        src_con.backup(dst_con)
    finally:
        dst_con.close()
        src_con.close()

    return FileResponse(tmp_file, media_type="application/x-sqlite3", filename="kalolsavam.db")
