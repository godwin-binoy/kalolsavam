"""FastAPI application factory: security headers, CSRF double-submit,
rate limiting (keyed on the real visitor IP from CF-Connecting-IP), public
dashboard static hosting (inert shells — all
protection lives in the auth'd APIs), and dependency-based auth guards."""
from __future__ import annotations

import hmac
import os
import secrets
import time

from fastapi import Depends, FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Config
from .db import Database
from .auth import TokenIssuer
from .events import BUS

REFRESH_COOKIE = "kal_rt"
CSRF_COOKIE = "kal_csrf"
CSRF_HEADER = "x-csrf-token"

# ---------------------------------------------------------------- rate limit
class TokenBucket:
    def __init__(self, rate_per_min: int, burst: int):
        self.rate = rate_per_min / 60.0
        self.burst = burst
        self._buckets: dict[str, tuple[float, float]] = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        tokens, last = self._buckets.get(key, (self.burst, now))
        tokens = min(self.burst, tokens + (now - last) * self.rate)
        if tokens < 1:
            self._buckets[key] = (tokens, now)
            return False
        self._buckets[key] = (tokens - 1, now)
        return True


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
        sid_row = db.one("SELECT * FROM sessions WHERE sid=?", (claims["sid"],))
        if not sid_row or sid_row["revoked"]:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "session_revoked")
        user = db.one("SELECT * FROM users WHERE id=?", (int(claims["sub"]),))
        if not user or user["disabled"]:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user_disabled")
        # idle lock enforcement
        idle = cfg.idle_lock_min * 60
        if db.now() - sid_row["last_seen"] > idle:
            db.execute("UPDATE sessions SET revoked=1 WHERE sid=?", (claims["sid"],))
            db.execute("UPDATE refresh_tokens SET revoked=1 WHERE jti=?",
                       (sid_row["current_jti"],))
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "idle_locked")
        db.execute("UPDATE sessions SET last_seen=? WHERE sid=?",
                   (db.now(), claims["sid"]))
        claims["user_row"] = dict(user)
        return claims

    def require_role(role: str):
        def dep(claims: dict = Depends(get_access)) -> dict:
            if claims["role"] != role and claims["role"] != "admin":
                raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient_role")
            return claims
        return dep

    app.state.get_access = get_access
    app.state.require_role = require_role

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
            return FileResponse(gate, headers={"Cache-Control": "no-store"})
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

    @app.exception_handler(HTTPException)
    async def hide_errors(request: Request, exc: HTTPException):
        # never leak internals; map 5xx to generic
        if exc.status_code >= 500:
            return JSONResponse({"detail": "internal_error"}, status_code=500)
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)

    return app
