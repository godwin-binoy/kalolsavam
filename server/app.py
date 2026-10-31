"""FastAPI application factory: security headers, CSRF double-submit,
rate limiting (keyed on the real visitor IP from CF-Connecting-IP), public
dashboard static hosting (inert shells — all protection lives in the auth'd
APIs), and dependency-based auth guards."""
from __future__ import annotations

import hmac
import os
import threading
import time

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Config
from .db import Database
from .auth import TokenIssuer

REFRESH_COOKIE = "kal_rt"
CSRF_COOKIE = "kal_csrf"
CSRF_HEADER = "x-csrf-token"

# ---------------------------------------------------------------- rate limit
class TokenBucket:
    """Fixed-window-free token bucket, per key (real visitor IP).

    A background sweeper drops idle buckets so a flood of unique spoofed IPs
    can never grow this dict into a memory-exhaustion DoS.
    """

    _IDLE_SEC = 600          # forget buckets untouched for 10 minutes
    _MAX_KEYS = 50_000       # hard ceiling; oldest evicted beyond it

    def __init__(self, rate_per_min: int, burst: int):
        self.rate = rate_per_min / 60.0
        self.burst = burst
        self._buckets: dict[str, list[float]] = {}
        self._lock = threading.Lock()
        cleaner = threading.Thread(target=self._sweep, daemon=True)
        cleaner.start()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            b = self._buckets.get(key)
            if b is None:
                if len(self._buckets) >= self._MAX_KEYS:
                    # evict ~quarter of the stalest entries instead of growing
                    for k, _ in sorted(self._buckets.items(),
                                       key=lambda kv: kv[1][1])[:self._MAX_KEYS // 4]:
                        self._buckets.pop(k, None)
                b = [float(self.burst), now]
            tokens = min(self.burst, b[0] + (now - b[1]) * self.rate)
            if tokens < 1:
                b[0], b[1] = tokens, now
                self._buckets[key] = b
                return False
            b[0], b[1] = tokens - 1, now
            self._buckets[key] = b
            return True

    def _sweep(self) -> None:
        while True:
            time.sleep(60)
            cutoff = time.time() - self._IDLE_SEC
            with self._lock:
                for k in [k for k, v in self._buckets.items() if v[1] < cutoff]:
                    self._buckets.pop(k, None)


SEC_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cross-Origin-Resource-Policy": "same-origin",
}

DASH_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; connect-src 'self'; font-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
)


def client_ip(request: Request, cfg: Config) -> str:
    """Real visitor IP.

    With the Cloudflare tunnel (the normal setup) every request arrives from
    cloudflared on localhost, so the socket address is useless — the visitor's
    true IP is in CF-Connecting-IP (single value, set by Cloudflare). Trusted
    only when TRUST_PROXY is on; otherwise these headers are spoofable.
    """
    if cfg.trust_proxy:
        cf = request.headers.get("cf-connecting-ip", "")
        if cf:
            return cf.split(",")[0].strip()
        fwd = request.headers.get("x-forwarded-for", "")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def create_app(cfg: Config, db: Database) -> FastAPI:
    app = FastAPI(title="Kalolsavam backend", docs_url=None, redoc_url=None,
                  openapi_url=None)  # no API discovery surface in prod

    @app.on_event("startup")
    async def _wire_event_bus():
        """Give the bus the live event loop so worker-thread mutations can
        fan out to SSE subscribers via call_soon_threadsafe."""
        from .events import BUS
        import asyncio
        BUS.attach_loop(asyncio.get_running_loop())

    @app.on_event("startup")
    async def _start_housekeeping():
        """Periodically bound the housekeeping tables (changelog/audit/expired
        sessions) so a multi-day festival can never fill the disk."""
        import asyncio

        async def _loop():
            while True:
                try:
                    await asyncio.to_thread(db.prune_history)
                except Exception:
                    pass  # never let a prune error kill the server
                await asyncio.sleep(6 * 3600)

        app.state.housekeeping = asyncio.create_task(_loop())

    app.state.cfg = cfg
    app.state.db = db
    app.state.tokens = TokenIssuer(cfg.signing_seeds, cfg.active_kid,
                                   cfg.access_ttl_min)
    app.state.auth_bucket = TokenBucket(10, 20)     # per-IP auth attempts
    app.state.api_bucket = TokenBucket(120, 200)    # general API

    # ------------------------------------------------------ middleware -----
    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        path = request.url.path

        # rate limits
        if path.startswith("/api/auth") and \
                not app.state.auth_bucket.allow(client_ip(request, cfg)):
            return JSONResponse({"detail": "rate_limited"}, status_code=429)
        if path.startswith("/api/") and \
                not app.state.api_bucket.allow(client_ip(request, cfg)):
            return JSONResponse({"detail": "rate_limited"}, status_code=429)

        # CSRF double-submit for cookie-driven auth mutations.
        # /login is exempt: it runs BEFORE any session cookies exist and is
        # protected by rate limits, lockouts and uniform error responses.
        _CSRF_EXEMPT = ("/api/auth/login",)
        if request.method in ("POST", "PUT", "PATCH", "DELETE") and \
           path.startswith("/api/auth/") and path not in _CSRF_EXEMPT:
            tok_c = request.cookies.get(CSRF_COOKIE, "")
            tok_h = request.headers.get(CSRF_HEADER, "")
            if not tok_c or not hmac.compare_digest(tok_c, tok_h):
                return JSONResponse({"detail": "csrf_failed"}, status_code=403)

        resp = await call_next(request)
        for k, v in SEC_HEADERS.items():
            resp.headers.setdefault(k, v)
        dash = ("/stagemaster", "/admin")
        sfx = cfg.dash_suffix
        if sfx:
            dash += (f"/stagemaster{sfx}", f"/admin{sfx}")
        if path.startswith(dash):
            resp.headers["Content-Security-Policy"] = DASH_CSP
            resp.headers["Cache-Control"] = "no-store"
            # HSTS only makes sense when we actually serve HTTPS ourselves;
            # with the Cloudflare tunnel, TLS is terminated at CF's edge and
            # Strict-Transport-Security is configured in the CF dashboard.
            if cfg.force_tls:
                resp.headers["Strict-Transport-Security"] = "max-age=31536000"
        elif path.startswith("/api/"):
            # APIs are per-user/per-IP dynamic — never cacheable by shared
            # caches (prevents cross-visitor leakage of rate state/tokens).
            resp.headers["Cache-Control"] = "no-store"
            resp.headers["Content-Security-Policy"] = DASH_CSP
        return resp

    # ------------------------------------------------------------ guards --
    def get_access(request: Request, *, allow_enroll: bool = False) -> dict:
        authz = request.headers.get("authorization", "")
        if not authz.startswith("Bearer "):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing_token")
        try:
            claims = app.state.tokens.verify_access(authz[7:])
        except Exception:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid_token")
        if claims.get("scope") == "enroll":
            # TOTP-enrollment token: only /api/auth/totp/* may accept it.
            if not allow_enroll:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "enroll_only")
            return claims
        # Defense-in-depth: an enrollment-scoped or password-changed user must
        # never pass — re-check the live DB row on every authenticated call.
        user = db.one("SELECT * FROM users WHERE id=?", (int(claims["sub"]),))
        if not user or user["disabled"]:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user_disabled")
        sid_row = db.one("SELECT * FROM sessions WHERE sid=?", (claims["sid"],))
        if not sid_row or sid_row["revoked"]:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session_revoked")
        # idle lock enforcement
        idle = cfg.idle_lock_min * 60
        now = db.now()
        if now - sid_row["last_seen"] > idle:
            db.execute("UPDATE sessions SET revoked=1 WHERE sid=?", (claims["sid"],))
            db.execute("UPDATE refresh_tokens SET revoked=1 WHERE jti=?",
                       (sid_row["current_jti"],))
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "idle_locked")
        # Throttle the last_seen write to once per minute — every authenticated
        # API call used to cost a disk commit (SQLite WAL fsync), which is both
        # a performance drag and a needless wear on venue laptops.
        if now - sid_row["last_seen"] > 60:
            db.execute("UPDATE sessions SET last_seen=? WHERE sid=?", (now,
                                                                       claims["sid"]))
        claims["user_row"] = dict(user)
        return claims

    app.state.get_access = get_access

    # ------------------------------------------- dashboard static files ---
    # Dashboards live INSIDE server/ (server/stagemaster, server/admin) so they
    # are never part of the public site build. They are still served as plain
    # static files to anyone on the internet — security comes exclusively from
    # the protected APIs (password + JWT + TOTP + role checks + rate limits).
    # Nothing links to them from the public pages; staff type the URL directly.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root
    srv_root = os.path.dirname(os.path.abspath(__file__))               # server/
    for folder in ("stagemaster", "admin"):
        d = os.path.join(srv_root, folder)
        if os.path.isdir(d):
            app.mount(f"/{folder}{cfg.dash_suffix}",
                      StaticFiles(directory=d, html=True),
                      name=f"dash_{folder}")

    @app.get("/")
    async def index():
        # Server root serves ONLY a neutral gate page — no links to dashboards.
        gate = os.path.join(srv_root, "static", "gate.html")
        if os.path.exists(gate):
            return FileResponse(gate, headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": DASH_CSP})
        return JSONResponse({"status": "ok"})

    # ------------------------------------------------------- routers ------
    from .routes_auth import router as auth_router
    from .routes_public import router as public_router
    from .routes_live import router as live_router
    from .routes_admin import router as admin_router

    app.include_router(auth_router, prefix="/api/auth")
    app.include_router(public_router, prefix="/api/public")
    app.include_router(live_router, prefix="/api/live")
    app.include_router(admin_router, prefix="/api/admin")

    # Any 404 (typos, scanner probes for /wp-admin, /.env, old /manage URLs…)
    # lands on the same neutral gate page: zero information leakage.
    @app.exception_handler(404)
    async def not_found_gate(request: Request, exc):
        gate = os.path.join(srv_root, "static", "gate.html")
        if os.path.exists(gate):
            return FileResponse(gate, status_code=404, headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": DASH_CSP})
        return JSONResponse({"detail": "not_found"}, status_code=404)

    @app.exception_handler(HTTPException)
    async def hide_errors(request: Request, exc: HTTPException):
        # never leak internals; map 5xx to generic
        if exc.status_code >= 500:
            return JSONResponse({"detail": "internal_error"}, status_code=500)
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    return app
