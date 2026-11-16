"""Obs Worker (Device 3): polls Core outbound for verified DB backups & audit logs."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import signal
import sqlite3
import sys
import time
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("obs_worker")

CORE_URL = os.getenv("CORE_URL", "http://backend:8000").rstrip("/")
SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "/app/backups"))
BACKUP_INTERVAL = max(300, int(os.getenv("BACKUP_INTERVAL_SEC", "3600")))
AUDIT_INTERVAL = max(30, int(os.getenv("AUDIT_INTERVAL_SEC", "60")))
KEEP_BACKUPS = max(5, int(os.getenv("KEEP_BACKUPS", "48")))

_RUNNING = True


def _stop(*_args) -> None:
    global _RUNNING
    _RUNNING = False


def _worker_token(secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), b"worker:obs", hashlib.sha256).hexdigest()


def _verify_sqlite(path: Path) -> bool:
    con = sqlite3.connect(str(path))
    try:
        row = con.execute("PRAGMA quick_check").fetchone()
        return bool(row and row[0] == "ok")
    finally:
        con.close()


def pull_backup(client: httpx.Client) -> bool:
    log.info("Pulling DB backup from Core...")
    r = client.get("/api/v1/internal/backup", timeout=90.0)
    r.raise_for_status()
    ts = time.strftime("%Y%m%d-%H%M%S")
    tmp = BACKUP_DIR / f".core-{ts}.db.tmp"
    dst = BACKUP_DIR / f"core-{ts}.db"
    try:
        tmp.write_bytes(r.content)
        if not _verify_sqlite(tmp):
            raise RuntimeError("SQLite quick_check failed on downloaded backup")
        os.replace(tmp, dst)
    finally:
        tmp.unlink(missing_ok=True)

    existing = sorted(BACKUP_DIR.glob("core-*.db"), key=lambda f: f.stat().st_mtime)
    for old in existing[:-KEEP_BACKUPS]:
        old.unlink(missing_ok=True)
    log.info("Saved verified backup: %s (%d bytes)", dst.name, dst.stat().st_size)
    return True


def pull_audit(client: httpx.Client, cursor_file: Path, log_file: Path) -> None:
    since = 0.0
    if cursor_file.exists():
        try:
            since = float(cursor_file.read_text().strip() or "0")
        except ValueError:
            since = 0.0

    r = client.get("/api/v1/internal/audit-export", params={"since": since, "limit": 500}, timeout=20.0)
    r.raise_for_status()
    items = r.json().get("items") or []
    if not items:
        return
    with open(log_file, "a", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, default=str) + "\n")
    last_ts = max(float(i["ts"]) for i in items)
    cursor_file.write_text(f"{last_ts:.6f}")
    log.info("Archived %d audit record(s)", len(items))


def run() -> None:
    if len(SECRET_KEY) < 32:
        log.error("SECRET_KEY missing or shorter than 32 characters.")
        sys.exit(2)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    cursor_file = BACKUP_DIR / "audit_cursor.txt"
    log_file = BACKUP_DIR / "audit_log.jsonl"
    headers = {"X-Worker-Token": _worker_token(SECRET_KEY)}

    log.info("Obs Worker starting (CORE_URL=%s)", CORE_URL)
    last_backup = 0.0
    last_audit = 0.0

    with httpx.Client(base_url=CORE_URL, headers=headers, timeout=30.0) as client:
        while _RUNNING:
            now = time.monotonic()
            if now - last_backup >= BACKUP_INTERVAL:
                try:
                    pull_backup(client)
                    last_backup = now
                except Exception as exc:
                    log.warning("Backup pull failed: %s", exc)
            if now - last_audit >= AUDIT_INTERVAL:
                try:
                    pull_audit(client, cursor_file, log_file)
                    last_audit = now
                except Exception as exc:
                    log.warning("Audit pull failed: %s", exc)
            time.sleep(10)


if __name__ == "__main__":
    run()
