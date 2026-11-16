"""FastAPI app factory: security middleware, GZip, CORS, SSE, and API routers."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
import time
import uuid
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .auth import check_rate_limit
from .auth import router as auth_router
from .config import Settings
from .db import Database

log = logging.getLogger("kalolsavam")

SEC_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}


class _JsonFmt(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"), "level": record.levelname, "logger": record.name, "msg": record.getMessage()}
        for k in ("request_id", "method", "path", "status", "duration_ms"):
            v = getattr(record, k, None)
            if v is not None:
                payload[k] = v
        return json.dumps(payload, default=str)


def setup_logging() -> None:
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(_JsonFmt())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(h)
    root.setLevel(logging.INFO)


async def _http_error(request: Request, exc: HTTPException) -> JSONResponse:
    req_id = getattr(request.state, "request_id", "")
    if exc.status_code >= 500:
        log.error("http_5xx", extra={"request_id": req_id, "method": request.method, "path": request.url.path, "status": exc.status_code})
        return JSONResponse({"error": "internal", "request_id": req_id}, status_code=500)
    return JSONResponse(exc.detail if isinstance(exc.detail, dict) else {"error": str(exc.detail)}, status_code=exc.status_code)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.loop = asyncio.get_running_loop()
    yield
    app.state.db.close_all()


def create_app(cfg: Settings, db: Database) -> FastAPI:
    app = FastAPI(title="Kalolsavam", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.cfg = cfg
    app.state.db = db
    app.state.subscribers = {}

    expected_origin = urlparse(cfg.public_origin)
    cors_origins = list(dict.fromkeys(
        [cfg.public_origin] + [o.strip().rstrip("/") for o in cfg.allowed_origins.split(",") if o.strip()]
    ))
    allowed_netlocs = {urlparse(o).netloc for o in cors_origins if urlparse(o).netloc}
    pages_preview_re = (
        re.compile(r"^https://([a-z0-9-]+\.)?" + re.escape(expected_origin.netloc) + r"$")
        if expected_origin.scheme == "https" and expected_origin.netloc.endswith(".pages.dev")
        else None
    )

    def _origin_allowed(origin_val: str, host_hdr: str) -> bool:
        o = urlparse(origin_val)
        allowed = allowed_netlocs | ({host_hdr} if host_hdr else set())
        return o.netloc in allowed or bool(pages_preview_re and pages_preview_re.match(origin_val.rstrip("/")))

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex[:12]
        start = time.perf_counter()
        clean_path = request.url.path.rstrip("/")

        if clean_path in ("/api/v1/auth/register", "/auth/register"):
            return JSONResponse({"error": "registration_disabled"}, status_code=403)

        if request.method == "POST" and clean_path in ("/api/v1/auth/login", "/auth/login"):
            try:
                check_rate_limit(request, "login", 15, 60)
            except HTTPException as exc:
                return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("origin")
            host_hdr = request.headers.get("host", "")
            using_bearer = request.headers.get("authorization", "").lower().startswith("bearer ")
            if origin and not _origin_allowed(origin, host_hdr):
                return JSONResponse({"error": "origin_mismatch"}, status_code=403)
            if not origin and not using_bearer:
                referer = request.headers.get("referer")
                if referer and not _origin_allowed(referer, host_hdr):
                    return JSONResponse({"error": "origin_mismatch"}, status_code=403)

        resp = await call_next(request)
        for k, v in SEC_HEADERS.items():
            resp.headers.setdefault(k, v)
        resp.headers["X-Request-ID"] = request.state.request_id
        if request.url.path.startswith(("/api/v1/admin/", "/api/v1/live/", "/api/v1/auth/")) or request.url.path in ("/healthz", "/readyz"):
            resp.headers["Cache-Control"] = "no-store"

        dur = int((time.perf_counter() - start) * 1000)
        log.info("req", extra={"request_id": request.state.request_id, "method": request.method, "path": request.url.path, "status": resp.status_code, "duration_ms": dur})
        return resp

    @app.get("/")
    async def root():
        return {"service": "kalolsavam", "ok": True}

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    @app.get("/readyz")
    async def readyz():
        try:
            db.one("SELECT 1 AS x")
            return {"ok": True, "version": __version__}
        except Exception:
            return JSONResponse({"ok": False}, status_code=503)

    from .routes.admin import internal_router
    from .routes.admin import router as admin_router
    from .routes.live import router as live_router
    from .routes.photos import router as photos_router
    from .routes.public import router as public_router

    app.include_router(auth_router, prefix="/api/v1/auth")
    app.include_router(public_router, prefix="/api/v1/public")
    app.include_router(live_router, prefix="/api/v1/live")
    app.include_router(admin_router, prefix="/api/v1/admin")
    app.include_router(photos_router, prefix="/api/v1/photos")
    app.include_router(internal_router, prefix="/api/v1/internal")

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def not_found(full_path: str):
        return JSONResponse({"error": "not_found"}, status_code=404)

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=pages_preview_re.pattern if pages_preview_re else None,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Idempotency-Key", "Authorization"],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )
    app.add_exception_handler(HTTPException, _http_error)
    return app
