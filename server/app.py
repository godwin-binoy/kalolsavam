"""FastAPI app factory: FullAuth, security middleware, GZip, SSE bus."""
from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from . import __version__
from .auth import create_auth
from .config import Settings
from .db import Database
from .deps import client_ip, hash_ip
from .errors import http_error

log = logging.getLogger("kalolsavam")

SEC_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.loop = asyncio.get_running_loop()
    yield
    if getattr(app.state, "auth_engine", None):
        await app.state.auth_engine.dispose()
    app.state.db.close_all()


def create_app(cfg: Settings, db: Database) -> FastAPI:
    app = FastAPI(
        title="Kalolsavam", lifespan=lifespan,
        docs_url=None, redoc_url=None, openapi_url=None,
    )
    app.state.cfg = cfg
    app.state.db = db
    app.state.subscribers = {}

    fullauth, auth_engine, auth_session_maker = create_auth(cfg)
    fullauth.init_app(app, include_routers=["auth", "profile", "sessions"])
    app.state.fullauth = fullauth
    app.state.auth_engine = auth_engine
    app.state.auth_session_maker = auth_session_maker

    expected_origin = urlparse(cfg.public_origin)
    cors_origins = [cfg.public_origin]
    if cfg.allowed_origins:
        cors_origins.extend(
            o.strip().rstrip("/") for o in cfg.allowed_origins.split(",") if o.strip()
        )
    cors_origins = list(dict.fromkeys(cors_origins))
    allowed_netlocs = {urlparse(o).netloc for o in cors_origins if urlparse(o).netloc}
    pages_preview_re = (
        re.compile(r"^https://([a-z0-9-]+\.)?" + re.escape(expected_origin.netloc) + r"$")
        if expected_origin.scheme == "https" and expected_origin.netloc.endswith(".pages.dev")
        else None
    )

    def _origin_allowed(origin_val: str, host_hdr: str) -> bool:
        o = urlparse(origin_val)
        allowed = set(allowed_netlocs)
        if host_hdr:
            allowed.add(host_hdr)
        preview_ok = bool(pages_preview_re and pages_preview_re.match(origin_val.rstrip("/")))
        return o.netloc in allowed or preview_ok

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex[:12]
        start = time.perf_counter()

        clean_path = request.url.path.rstrip("/")
        if clean_path in ("/api/v1/auth/register", "/auth/register"):
            return JSONResponse({"error": "registration_disabled"}, status_code=403)

        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("origin")
            host_hdr = request.headers.get("host", "")
            auth_hdr = request.headers.get("authorization", "")
            using_bearer = auth_hdr.lower().startswith("bearer ")

            if origin and not _origin_allowed(origin, host_hdr):
                return JSONResponse({"error": "origin_mismatch"}, status_code=403)
            elif not origin and not using_bearer:
                referer = request.headers.get("referer")
                if referer and not _origin_allowed(referer, host_hdr):
                    return JSONResponse({"error": "origin_mismatch"}, status_code=403)

        resp = await call_next(request)

        # Audit login attempts (best-effort; must never break the response)
        if request.method == "POST" and clean_path in ("/api/v1/auth/login", "/auth/login"):
            try:
                ip_h = hash_ip(client_ip(request), cfg.secret_key)
                now = db.now()
                if resp.status_code == 200:
                    db.ex(
                        "INSERT INTO auth_audit(ts, username, ip_hash, event, detail) VALUES (?,?,?,?,?)",
                        (now, "staff", ip_h, "login_ok", "status=200"),
                    )
                elif resp.status_code in (400, 401, 403, 429):
                    db.ex(
                        "INSERT INTO auth_audit(ts, username, ip_hash, event, detail) VALUES (?,?,?,?,?)",
                        (now, "unknown", ip_h, "login_fail", f"status={resp.status_code}"),
                    )
            except Exception as exc:
                log.warning("auth_audit_write_failed: %s", exc)

        for k, v in SEC_HEADERS.items():
            resp.headers.setdefault(k, v)
        resp.headers["X-Request-ID"] = request.state.request_id

        path = request.url.path
        if path.startswith(("/admin", "/stagemaster", "/dashboard")):
            resp.headers["Cache-Control"] = "no-store"
            resp.headers["X-Robots-Tag"] = "noindex, nofollow"
        elif path.startswith("/assets/js/"):
            resp.headers["Cache-Control"] = "public, max-age=300, must-revalidate"
        elif path.startswith("/assets/"):
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif path.startswith(("/api/v1/admin/", "/api/v1/live/", "/api/v1/auth/")):
            resp.headers["Cache-Control"] = "no-store"
        elif path in ("/healthz", "/readyz"):
            resp.headers["Cache-Control"] = "no-store"
        elif path == "/sw.js":
            resp.headers["Cache-Control"] = "no-cache, must-revalidate"
        else:
            if "text/html" in resp.headers.get("content-type", ""):
                resp.headers.setdefault("Cache-Control", "public, max-age=0, must-revalidate")

        dur = int((time.perf_counter() - start) * 1000)
        log.info("req", extra={
            "request_id": request.state.request_id, "method": request.method,
            "path": path, "status": resp.status_code, "duration_ms": dur,
        })
        return resp

    srv = Path(__file__).resolve().parent
    pub = srv.parent / "public"
    dist = Path(cfg.dist_path)

    assets_dir = next((p for p in (dist / "assets", pub / "assets") if p.exists()), None)
    if assets_dir is not None:
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    dashboard_dir = next((p for p in (dist / "dashboard", pub / "dashboard", srv / "dashboard") if p.exists()), None)
    if dashboard_dir is not None:
        app.mount("/dashboard", StaticFiles(directory=dashboard_dir, html=True), name="dashboard")

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

    @app.get("/robots.txt")
    async def robots():
        for f in (dist / "robots.txt", pub / "robots.txt"):
            if f.is_file():
                return FileResponse(f, media_type="text/plain")
        return JSONResponse({}, status_code=404)

    @app.get("/manifest.json")
    async def manifest():
        for f in (dist / "manifest.json", pub / "manifest.json"):
            if f.is_file():
                return FileResponse(f, media_type="application/json")
        return JSONResponse({}, status_code=404)

    @app.get("/sw.js")
    async def sw():
        f = dist / "sw.js"
        return FileResponse(f, media_type="application/javascript") if f.exists() else JSONResponse({}, status_code=404)

    from .routes.admin import router as admin_router
    from .routes.live import router as live_router
    from .routes.public import router as public_router
    app.include_router(public_router, prefix="/api/v1/public")
    app.include_router(live_router, prefix="/api/v1/live")
    app.include_router(admin_router, prefix="/api/v1/admin")

    @app.get("/admin", include_in_schema=False)
    async def admin_bare_redirect():
        return RedirectResponse(url="/admin/", status_code=307)

    @app.get("/stagemaster", include_in_schema=False)
    async def stagemaster_bare_redirect():
        return RedirectResponse(url="/stagemaster/", status_code=307)

    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        clean_path = full_path.strip("/")

        if clean_path == "favicon.ico":
            return Response(status_code=204)

        if (
            clean_path in ("api", "assets", "dashboard")
            or clean_path.startswith(("api/", "assets/", "dashboard/"))
        ):
            return JSONResponse({"error": "not_found"}, status_code=404)

        dist_root = dist.resolve()

        def _safe(rel: str):
            try:
                c = (dist / rel).resolve()
                if c.is_relative_to(dist_root) and c.is_file():
                    return c
            except (ValueError, OSError):
                pass
            return None

        candidates: list[str] = []
        if clean_path:
            candidates.append(clean_path)
            candidates.append(clean_path.rstrip("/") + "/index.html")
            if "." not in clean_path.rsplit("/", 1)[-1]:
                candidates.append(clean_path + ".html")
        else:
            candidates.append("index.html")

        for rel in candidates:
            path = _safe(rel)
            if path:
                return FileResponse(path)

        nf = _safe("404.html")
        if nf:
            return FileResponse(nf, status_code=404)

        if not clean_path:
            gate = srv / "static" / "gate.html"
            if gate.is_file():
                return FileResponse(gate)

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
    app.add_exception_handler(HTTPException, http_error)
    return app
