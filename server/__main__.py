"""Entry point: python -m server."""
from __future__ import annotations

import logging
from pathlib import Path

from .app import create_app
from .config import Settings
from .db import Database
from .logging_setup import setup as setup_logging


def main() -> None:
    setup_logging()
    cfg = Settings()
    db = Database(Path(cfg.db_path))
    app = create_app(cfg, db)

    import uvicorn
    logging.getLogger("kalolsavam").info(
        f"binding {cfg.server_host}:{cfg.server_port}")
    uvicorn.run(
        app=app, host=cfg.server_host, port=cfg.server_port,
        log_level="warning", proxy_headers=False,
    )


if __name__ == "__main__":
    main()
