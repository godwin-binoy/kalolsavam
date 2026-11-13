"""FastAPI app factory. FullAuth, Astro dist mount, SSE bus."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import logging
from pathlib import Path
import time
from urllib.parse import urlparse
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel

from .auth import create_auth
from .config import Settings
from .db import Database
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
    async with app.state.auth_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    await app.state.auth_engine.dispose()


def create_app(cfg: Settings, db: Database) -> FastAPI:
    app = FastAPI(
        title="Kalolsavam", lifespan=lifespan,
        docs_url=None, redoc_url=None, openapi_url=None,
    )
    app.state.cfg = cfg
    app.state.db = db
    app.state.subscribers = {}

    fullauth, auth_engine, auth_session_maker = create_auth(cfg)
    fullauth.init_app(app)
    app.state.fullauth = fullauth
    app.state.auth_engine = auth_engine
    app.state.auth_session_maker = auth_session_maker

    expected_origin = urlparse(cfg.public_origin)

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex[:12]
        start = time.perf_counter()

        if request.url.path.rstrip("/") == "/api/v1/auth/register":
            return JSONResponse({"error": "registration_disabled"}, status_code=403)

        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("origin")
            if origin:
                o = urlparse(origin)
                host_hdr = request.headers.get("host", "")
                allowed = {expected_origin.netloc}
                if host_hdr:
                    allowed.add(host_hdr)
                if o.netloc not in allowed:
                    return JSONResponse({"error": "origin_mismatch"}, status_code=403)

        resp = await call_next(request)
        for k, v in SEC_HEADERS.items():
            resp.headers.setdefault(k, v)
        resp.headers["X-Request-ID"] = request.state.request_id
        path = request.url.path
        if path.startswith(("/admin", "/stagemaster", "/dashboard")):
            resp.headers["Cache-Control"] = "no-store"
        elif path.startswith("/assets/js/"):
            resp.headers["Cache-Control"] = "public, max-age=300, must-revalidate"
        elif path.startswith("/assets/"):
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif path.startswith("/api/v1/admin/"):
            resp.headers["Cache-Control"] = "no-store"
        elif path.startswith("/api/v1/live/"):
            resp.headers["Cache-Control"] = "no-store"
        elif path in ("/healthz", "/readyz"):
            resp.headers["Cache-Control"] = "no-store"
        elif path == "/sw.js":
            # Force revalidation every load so SW updates land immediately.
            resp.headers["Cache-Control"] = "no-cache, must-revalidate"
        else:
            # HTML pages: always revalidate. FileResponse supplies ETag, so
            # revalidation is a cheap 304 when unchanged. setdefault preserves
            # any Cache-Control a route already set (e.g. public API TTLs).
            if "text/html" in resp.headers.get("content-type", ""):
                resp.headers.setdefault(
                    "Cache-Control", "public, max-age=0, must-revalidate"
                )
        dur = int((time.perf_counter() - start) * 1000)
        log.info("req", extra={
            "request_id": request.state.request_id, "method": request.method,
            "path": path, "status": resp.status_code, "duration_ms": dur,
        })
        return resp

    srv = Path(__file__).resolve().parent
    pub = srv.parent / "public"
    dist = Path(cfg.dist_path)

    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
    if (dist / "pages").exists():
        app.mount("/pages", StaticFiles(directory=dist / "pages"), name="pages")
    dashboard_dir = dist / "dashboard" if (dist / "dashboard").exists() else srv / "dashboard"
    if dashboard_dir.exists():
        app.mount("/dashboard", StaticFiles(directory=dashboard_dir, html=True), name="dashboard")

    @app.get("/healthz")
    async def healthz():
        return {"ok": True}

    @app.get("/readyz")
    async def readyz():
        try:
            db.one("SELECT 1 AS x")
            return {"ok": True, "version": "4.0.0"}
        except Exception:
            return JSONResponse({"ok": False}, status_code=503)

    @app.get("/robots.txt")
    async def robots():
        f = dist / "robots.txt"
        return FileResponse(f, media_type="text/plain") if f.exists() else JSONResponse({}, status_code=404)

    @app.get("/manifest.json")
    async def manifest():
        f = dist / "manifest.json"
        return FileResponse(f, media_type="application/json") if f.exists() else JSONResponse({}, status_code=404)

    @app.get("/sw.js")
    async def sw():
        f = dist / "sw.js"
        return FileResponse(f, media_type="application/javascript") if f.exists() else JSONResponse({}, status_code=404)

    from .routes.public import router as public_router
    from .routes.live import router as live_router
    from .routes.admin import router as admin_router
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
        clean_path = full_path.lstrip("/")
        if (
            clean_path in ("api", "assets", "dashboard", "pages")
            or clean_path.startswith(("api/", "assets/", "dashboard/", "pages/"))
        ):
            return JSONResponse({"error": "not_found"}, status_code=404)

        if clean_path in ("admin/", "admin/index.html"):
            admin_html = dist / "admin" / "index.html"
            if admin_html.is_file():
                return FileResponse(admin_html)
            pub_admin = pub / "admin" / "index.html"
            if pub_admin.is_file():
                return FileResponse(pub_admin)

        if clean_path in ("stagemaster/", "stagemaster/index.html"):
            sm_html = dist / "stagemaster" / "index.html"
            if sm_html.is_file():
                return FileResponse(sm_html)
            pub_sm = pub / "stagemaster" / "index.html"
            if pub_sm.is_file():
                return FileResponse(pub_sm)

        if not dist.exists():
            gate = srv / "static" / "gate.html"
            return FileResponse(gate)

        dist_root = dist.resolve()

        def _safe(p: Path) -> bool:
            try:
                p.resolve().relative_to(dist_root)
                return True
            except ValueError:
                return False

        # 1. Exact file match (sandboxed under dist_root)
        target = dist / full_path
        if _safe(target) and target.is_file():
            return FileResponse(target)

        # 2. Directory with index.html (e.g. venues -> dist/venues/index.html)
        target_html = dist / full_path / "index.html"
        if _safe(target_html) and target_html.is_file():
            return FileResponse(target_html)

        # 3. File with .html appended
        target_ext = dist / f"{full_path}.html"
        if _safe(target_ext) and target_ext.is_file():
            return FileResponse(target_ext)

        # 4. Default root index (SPA fallback)
        index = dist / "index.html"
        if index.exists():
            return FileResponse(index)
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    app.add_exception_handler(HTTPException, http_error)
    return app
