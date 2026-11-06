"""Snapshot the SQLite DB. Keeps 24 backups."""
from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from server.config import Settings


def main() -> None:
    cfg = Settings()
    src = Path(cfg.db_path)
    if not src.exists():
        raise SystemExit(f"DB not found: {src}")
    dst_dir = src.parent / "backups"
    dst_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dst = dst_dir / f"kalolsavam-{stamp}.db"
    src_con = sqlite3.connect(str(src))
    dst_con = sqlite3.connect(str(dst))
    src_con.backup(dst_con)
    dst_con.close()
    src_con.close()
    backups = sorted(dst_dir.glob("kalolsavam-*.db"))
    for old in backups[:-24]:
        old.unlink()
    print(f"Backup written: {dst}")


if __name__ == "__main__":
    main()
