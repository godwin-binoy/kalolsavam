"""Obs Worker: Polls Core for backups and logs, stores locally."""
import os
import time
import requests
import logging
from pathlib import Path
import sqlite3

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("obs_worker")

CORE_URL = os.getenv("CORE_URL", "https://api.yourdomain.com")
SECRET_KEY = os.getenv("SECRET_KEY", "")
BACKUP_DIR = Path("/app/backups")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def pull_backup():
    log.info("Pulling hourly backup from Core...")
    try:
        r = requests.get(f"{CORE_URL}/api/v1/internal/backup", headers={"X-Obs-Token": SECRET_KEY}, timeout=60)
        if r.status_code == 200:
            ts = time.strftime("%Y%m%d-%H%M%S")
            dst = BACKUP_DIR / f"core-{ts}.db"
            dst.write_bytes(r.content)
            log.info(f"Saved backup: {dst.name} ({len(r.content)} bytes)")
    except Exception as e:
        log.error(f"Backup failed: {e}")

def run():
    log.info(f"Obs Worker starting. Polling {CORE_URL}...")
    last_backup = 0
    while True:
        if time.time() - last_backup > 3600:
            pull_backup()
            last_backup = time.time()
        time.sleep(60)

if __name__ == "__main__":
    run()
