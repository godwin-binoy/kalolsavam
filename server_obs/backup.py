import asyncio
import logging
import os
import time
from pathlib import Path
import requests

log = logging.getLogger("obs")
CORE_URL = os.getenv("CORE_URL", "http://backend:8000")
SECRET_KEY = os.getenv("SECRET_KEY", "")
BACKUP_DIR = Path("/app/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

async def hourly_backup_job():
    while True:
        try:
            log.info("Starting hourly backup pull...")
            headers = {"X-Obs-Token": SECRET_KEY}
            r = requests.get(f"{CORE_URL}/api/v1/internal/backup", headers=headers, timeout=60)
            if r.status_code == 200:
                ts = time.strftime("%Y%m%d-%H%M%S")
                dst = BACKUP_DIR / f"core-{ts}.db"
                dst.write_bytes(r.content)
                log.info(f"Backup saved: {dst.name} ({len(r.content)} bytes)")
            else:
                log.error(f"Backup failed: HTTP {r.status_code}")
        except Exception as e:
            log.error(f"Backup error: {e}")
        
        await asyncio.sleep(3600)  # 1 hour
