#!/usr/bin/env python3
"""Host script — starts uvicorn with TLS on the configured LAN bind.

Usage:  python -m server.scripts.run [--dev]
  --dev  plain HTTP on 127.0.0.1 (no TLS, for local development only)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from server.config import Config          # noqa: E402
from server.db import Database            # noqa: E402
from server.app import create_app         # noqa: E402


def main() -> None:
    dev = "--dev" in sys.argv
    cfg = Config()
    if dev:
        cfg.host, cfg.port = "127.0.0.1", 8000
    else:
        cfg.validate()
        if not cfg.tls_cert.exists() or not cfg.tls_key.exists():
            raise SystemExit("TLS material missing — run: "
                             "python -m server.scripts.init_tls")
    cfg.ensure_dirs()
    db = Database(cfg.db_path)
    app = create_app(cfg, db)

    import uvicorn
    kwargs = dict(app=app, host=cfg.host, port=cfg.port, log_level="info",
                 loop="uvloop" if _has_uvloop() else "asyncio")
    if not dev:
        kwargs.update(ssl_certfile=str(cfg.tls_cert), ssl_keyfile=str(cfg.tls_key),
                      ssl_version=None)
    print(f"[run] binding {cfg.host}:{cfg.port} ({'DEV/http' if dev else 'prod/https'})")
    uvicorn.run(**kwargs)


def _has_uvloop() -> bool:
    try:
        import uvloop  # noqa
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    main()
