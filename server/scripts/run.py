#!/usr/bin/env python3
"""Host script — starts uvicorn on plain HTTP, reached from outside through a
Cloudflare Tunnel (cloudflared). No TLS/certificates are handled here any more:
the unreliable venue internet is published via the tunnel, which terminates
HTTPS at Cloudflare's edge and connects to us over http://127.0.0.1:<port>.

Usage:  python -m server.scripts.run [--dev]
  --dev   same thing, but forces loopback + port 8000 (local development)
  Default binds SERVER_HOST/SERVER_PORT from .env (127.0.0.1:8000 recommended).

Only set FORCE_TLS=1 (+TLS_CERT_PATH/TLS_KEY_PATH) if you deliberately front
this server with your own HTTPS reverse proxy instead of the tunnel.
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
        if cfg.force_tls and (not cfg.tls_cert or not cfg.tls_cert.exists()
                              or not cfg.tls_key or not cfg.tls_key.exists()):
            raise SystemExit("FORCE_TLS=1 but certificate files are missing — "
                             "set TLS_CERT_PATH/TLS_KEY_PATH, or unset FORCE_TLS "
                             "to serve plain HTTP behind the Cloudflare tunnel.")
    cfg.ensure_dirs()
    db = Database(cfg.db_path)
    app = create_app(cfg, db)

    import uvicorn
    kwargs = dict(app=app, host=cfg.host, port=cfg.port, log_level="info",
                  loop="uvloop" if _has_uvloop() else "asyncio",
                  # cloudflared/proxy sits on localhost; give SSE streams room
                  forwarded_allow_ips="127.0.0.1,::1")
    if cfg.force_tls:
        kwargs.update(ssl_certfile=str(cfg.tls_cert), ssl_keyfile=str(cfg.tls_key))
    mode = "DEV/http" if dev else ("prod/https" if cfg.force_tls
                                  else "prod/http (Cloudflare tunnel)")
    print(f"[run] binding {cfg.host}:{cfg.port} ({mode})")
    if not cfg.force_tls:
        print("[run] point cloudflared at this address, e.g.\n"
              f"      cloudflared tunnel --url http://{cfg.host}:{cfg.port}")
    uvicorn.run(**kwargs)


def _has_uvloop() -> bool:
    try:
        import uvloop  # noqa
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    main()
