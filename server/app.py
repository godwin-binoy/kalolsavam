"""FastAPI app factory. Static mounts, security middleware, SSE bus."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .db import Database
from .deps import CSRF_COOKIE
from .errors import http_error

log = logging.getLogger("kalolsavam")

SEC_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}

DASH_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)

PUBLIC_CSP = (
    "default-src 'self'; script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
    "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
)


def create_app(cfg: Settings, db: Database) -> FastAPI:
    app = FastAPI(
        title="Kalolsavam",
        docs_url=None, redoc_url=None, openapi_url=None,
    )
    app.state.cfg = cfg
    app.state.db = db
    app.state.subscribers = set()

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex[:12]
        start = time.perf_counter()

        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            if request.url.path not in ("/api/v1/auth/login",):
                origin = request.headers.get("origin", "")
                if origin and origin.rstrip("/") != cfg.public_origin:
                    return JSONResponse({"error": "origin_mismatch"}, status_code=403)
                cookie = request.cookies.get(CSRF_COOKIE, "")
                header = request.headers.get("x-csrf-token", "")
                if cookie and cookie != header:
                    return JSONResponse({"error": "csrf_failed"}, status_code=403)

        resp = await call_next(request)

        for k, v in SEC_HEADERS.items():
            resp.headers.setdefault(k, v)
        resp.headers["X-Request-ID"] = request.state.request_id

        path = request.url.path
        if path.startswith(("/admin", "/stagemaster", "/dashboard")):
            resp.headers["Content-Security-Policy"] = DASH_CSP
            resp.headers["Cache-Control"] = "no-store"
        elif not path.startswith("/assets/") and not path.startswith("/api/"):
            resp.headers["Content-Security-Policy"] = PUBLIC_CSP

        if path.startswith("/assets/"):
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"

        dur = int((time.perf_counter() - start) * 1000)
        log.info(
            "req",
            extra={
                "request_id": request.state.request_id,
                "method": request.method,
                "path": path,
                "status": resp.status_code,
                "duration_ms": dur,
            },
        )
        return resp

    srv = Path(__file__).resolve().parent
    dist = srv.parent / "dist"

    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
        if (dist / "pages").exists():
            app.mount("/pages", StaticFiles(directory=dist / "pages"), name="pages")

    app.mount("/dashboard", StaticFiles(directory=srv / "dashboard"), name="dashboard")
    app.mount("/stagemaster",
              StaticFiles(directory=srv / "static" / "stagemaster", html=True),
              name="stagemaster")
    app.mount("/admin",
              StaticFiles(directory=srv / "static" / "admin", html=True),
              name="admin")

    @app.get("/")
    async def root():
        index = dist / "index.html"
        if index.exists():
            return FileResponse(index)
        return FileResponse(srv / "static" / "gate.html")

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    @app.get("/readyz")
    async def readyz():
        try:
            db.one("SELECT 1 AS x")
            return {"ok": True, "version": "3.0.0"}
        except Exception:
            return JSONResponse({"ok": False}, status_code=503)

    @app.get("/robots.txt")
    async def robots():
        f = dist / "robots.txt"
        if f.exists():
            return FileResponse(f, media_type="text/plain")
        return JSONResponse({"robots": "disallowed"}, status_code=404)

    from .routes.auth import router as auth_router
    from .routes.public import router as public_router
    from .routes.live import router as live_router
    from .routes.admin import router as admin_router

    app.include_router(auth_router, prefix="/api/v1/auth")
    app.include_router(public_router, prefix="/api/v1/public")
    app.include_router(live_router, prefix="/api/v1/live")
    app.include_router(admin_router, prefix="/api/v1/admin")

    app.add_exception_handler(HTTPException, http_error)
    return app
