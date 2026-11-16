"""Internal endpoints for Device 3 Obs Worker (backups & audit log export)."""
from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from ..deps import get_cfg, get_db, require_worker

router = APIRouter()


@router.get("/backup")
def download_backup(request: Request, _=Depends(require_worker("obs"))):
    """Hot-backup the DB and stream it to the Obs Worker, cleaning temp dir afterward."""
    cfg = get_cfg(request)
    src_path = Path(cfg.db_path)
    if not src_path.exists():
        raise HTTPException(500, "db_not_found")

    temp_dir = tempfile.mkdtemp(prefix="kal-bak-")
    tmp_file = Path(temp_dir) / "kalolsavam.db"
    src_con = sqlite3.connect(str(src_path))
    dst_con = sqlite3.connect(str(tmp_file))
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


@router.get("/audit-export")
def export_audit_logs(
    request: Request,
    since: float = 0.0,
    limit: int = 500,
    _=Depends(require_worker("obs")),
):
    limit = max(1, min(limit, 1000))
    rows = get_db(request).q(
        "SELECT id, ts, username, ip_hash, event, detail "
        "FROM auth_audit WHERE ts > ? ORDER BY ts ASC LIMIT ?",
        (since, limit),
    )
    return {"items": [dict(r) for r in rows]}
