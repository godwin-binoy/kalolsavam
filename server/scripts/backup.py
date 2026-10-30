#!/usr/bin/env python3
"""Snapshot the SQLite DB into server/backups/ with rotation (keep last 24)."""
from __future__ import annotations

import shutil
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from server.config import Config  # noqa: E402

KEEP = 24


def main() -> None:
    cfg = Config()
    src = cfg.db_path
    if not src.exists():
        raise SystemExit(f"database not found: {src}")
    dst_dir = src.parent / "backups"
    dst_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = dst_dir / f"kalolsavam-{stamp}.db"
    con = sqlite3.connect(str(src))
    dst_con = sqlite3.connect(str(dst))
    con.backup(dst_con)          # online backup API — safe under WAL
    dst_con.close(); con.close()
    backups = sorted(dst_dir.glob("kalolsavam-*.db"))
    for old in backups[:-KEEP]:
        old.unlink()
    print(str(dst))


if __name__ == "__main__":
    main()
