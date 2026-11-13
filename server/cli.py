"""Unified management CLI: python -m server <command>."""
from __future__ import annotations

import asyncio
import json
import logging
import secrets
import sqlite3
import time as _t
from pathlib import Path

import typer

app = typer.Typer(help="Kalolsavam management CLI", no_args_is_help=False)
log = logging.getLogger("kalolsavam")

FALLBACK_STAGES = [
    {"n": 1, "name": "St. Antony's HSS Ground", "slug": "stage-1", "kind": "stage"},
    {"n": 2, "name": "HS Hall", "slug": "stage-2", "kind": "stage"},
    {"n": 3, "name": "GLPS Mala", "slug": "stage-3", "kind": "stage"},
    {"n": 4, "name": "HSS A1 B1 Classes", "slug": "stage-4", "kind": "stage"},
    {"n": 5, "name": "HSS Seminar Hall", "slug": "stage-5", "kind": "stage"},
    {"n": 6, "name": "Vyaapaara Bhavan", "slug": "stage-6", "kind": "stage"},
    {"n": 7, "name": "HSS 1st Floor Class", "slug": "stage-7", "kind": "stage"},
    {"n": 8, "name": "HS 9E Class", "slug": "stage-8", "kind": "stage"},
    {"n": 9, "name": "HS Arabic Class", "slug": "stage-9", "kind": "stage"},
]


@app.command()
def serve(
    host: str | None = typer.Option(None, "--host", "-h", help="Bind host"),
    port: int | None = typer.Option(None, "--port", "-p", help="Bind port"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for dev"),
) -> None:
    """Run the FastAPI + Uvicorn server (schema is upgraded to head first)."""
    import uvicorn

    from .app import create_app
    from .config import Settings
    from .db import Database
    from .logging_setup import setup as setup_logging
    from .schema import upgrade_to_head

    setup_logging()
    cfg = Settings()
    upgrade_to_head(cfg.db_path)
    db = Database(Path(cfg.db_path))
    app_instance = create_app(cfg, db)

    bind_host = host or cfg.server_host
    bind_port = port or cfg.server_port
    log.info("Binding %s:%s", bind_host, bind_port)
    uvicorn.run(
        app=app_instance,
        host=bind_host,
        port=bind_port,
        reload=reload,
        log_level="warning",
        proxy_headers=False,
    )


@app.command()
def migrate() -> None:
    """Run Alembic migrations to head."""
    from .config import Settings
    from .schema import upgrade_to_head

    upgrade_to_head(Settings().db_path)
    typer.echo("Database migrations applied successfully.")


async def _async_seed_admin(email: str, password: str | None) -> tuple[bool, str]:
    from argon2 import PasswordHasher
    from sqlmodel import select

    from .config import Settings
    from .database import make_engine, make_session_maker
    from .models import Role, User

    cfg = Settings()
    engine = make_engine(cfg.db_path)
    session_maker = make_session_maker(engine)
    ph = PasswordHasher()
    used_password = password or secrets.token_urlsafe(16)
    try:
        async with session_maker() as session:
            admin_role = (
                await session.execute(select(Role).where(Role.name == "admin"))
            ).scalar_one_or_none()
            if not admin_role:
                admin_role = Role(name="admin")
                session.add(admin_role)
            sm_role = (
                await session.execute(select(Role).where(Role.name == "stagemaster"))
            ).scalar_one_or_none()
            if not sm_role:
                session.add(Role(name="stagemaster"))
            await session.commit()
            await session.refresh(admin_role)

            clean_email = email.strip().lower()
            existing = (
                await session.execute(select(User).where(User.email == clean_email))
            ).scalar_one_or_none()
            if existing:
                return False, ""

            u = User(
                email=clean_email,
                hashed_password=ph.hash(used_password),
                is_active=True,
                is_verified=True,
                stages="[]",
            )
            u.roles.append(admin_role)
            session.add(u)
            await session.commit()
            return True, used_password
    finally:
        await engine.dispose()


@app.command()
def seed_admin(
    email: str = typer.Option(
        "admin@kalolsavam.example.com", "--email", "-e", help="Admin email"
    ),
    password: str | None = typer.Option(
        None, "--password", help="Admin password (generated if omitted)"
    ),
) -> None:
    """Seed initial admin and staff roles."""
    from .config import Settings
    from .schema import upgrade_to_head

    upgrade_to_head(Settings().db_path)
    created, final_pass = asyncio.run(_async_seed_admin(email, password))
    if not created:
        typer.echo(f"Admin user '{email}' already exists. Skipping.")
        return
    typer.echo("=" * 65)
    typer.echo(f"Admin user '{email}' created.")
    typer.echo(f"Temporary password: {final_pass}")
    typer.echo("Sign in at /admin/ and change password immediately.")
    typer.echo("=" * 65)


@app.command()
def seed_stages(
    stages_file: Path = typer.Option(
        Path("src/data/stages.json"), "--file", "-f", help="Path to stages.json"
    ),
) -> None:
    """Seed or update all 9 stages in the database from stages.json."""
    from .config import Settings
    from .db import Database
    from .schema import upgrade_to_head

    cfg = Settings()
    upgrade_to_head(cfg.db_path)
    db = Database(Path(cfg.db_path))

    data = None
    if stages_file.is_file():
        try:
            data = json.loads(stages_file.read_text(encoding="utf-8"))
        except Exception as e:
            typer.echo(f"Warning: could not read {stages_file} ({e}), using fallback stages.")
    items = data if isinstance(data, list) else FALLBACK_STAGES

    with db.transaction():
        for s in items:
            vid = int(s["n"])
            name = s["name"]
            slug = s.get("slug") or f"stage-{vid}"
            kind = s.get("kind") or "stage"
            db.ex(
                "INSERT INTO venues(id, name, kind, slug, active) VALUES (?,?,?,?,1) "
                "ON CONFLICT(id) DO UPDATE SET name = excluded.name, slug = excluded.slug",
                (vid, name, kind, slug),
            )
    typer.echo(f"Seeded/updated {len(items)} stages in database.")


@app.command()
def backup() -> None:
    """Create a hot online SQLite backup of kalolsavam.db."""
    from .config import Settings

    cfg = Settings()
    src = Path(cfg.db_path)
    if not src.exists():
        typer.echo(f"Database {src} does not exist.")
        raise typer.Exit(code=1)

    dst_dir = src.parent / "backups"
    dst_dir.mkdir(parents=True, exist_ok=True)
    ts = _t.strftime("%Y%m%d-%H%M%S")
    dst = dst_dir / f"{src.stem}-{ts}.db"

    src_con = sqlite3.connect(str(src))
    dst_con = sqlite3.connect(str(dst))
    try:
        src_con.backup(dst_con)
    finally:
        dst_con.close()
        src_con.close()

    existing = sorted(dst_dir.glob(f"{src.stem}-*.db"), key=lambda f: f.stat().st_mtime)
    for old in existing[:-24]:
        try:
            old.unlink()
        except OSError:
            pass
    typer.echo(f"Backup created: {dst}")


@app.command()
def check() -> None:
    """Check database health, tables, and settings (read-only)."""
    from .config import Settings
    from .db import Database

    cfg = Settings()
    db = Database(Path(cfg.db_path))
    tables = [
        r["name"]
        for r in db.q("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    ]
    typer.echo(f"DB Path: {cfg.db_path}")
    typer.echo(f"Tables present ({len(tables)}): {', '.join(tables)}")
    user_count = (
        db.one("SELECT COUNT(*) c FROM fullauth_users")["c"]
        if "fullauth_users" in tables
        else 0
    )
    typer.echo(f"Users registered: {user_count}")


# ── User management (invoked by ./kal admin *) ────────────────────────────
async def _async_list_users():
    from sqlmodel import select

    from .config import Settings
    from .database import make_engine, make_session_maker
    from .models import User

    cfg = Settings()
    engine = make_engine(cfg.db_path)
    session_maker = make_session_maker(engine)
    try:
        async with session_maker() as session:
            users = (
                await session.execute(select(User).order_by(User.email))
            ).scalars().all()
            return [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "active": u.is_active,
                    "roles": [r.name for r in u.roles],
                    "stages": u.stages,
                }
                for u in users
            ]
    finally:
        await engine.dispose()


@app.command()
def user_list(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """List all users."""
    users = asyncio.run(_async_list_users())
    if json_output:
        typer.echo(json.dumps(users, indent=2))
        return
    if not users:
        typer.echo("No users.")
        return
    for u in users:
        status = "active" if u["active"] else "disabled"
        roles = ",".join(u["roles"]) or "-"
        typer.echo(f"{u['email']:<40} {roles:<20} {status}")


async def _async_reset_password(email: str, password: str | None):
    from argon2 import PasswordHasher
    from sqlmodel import select

    from .config import Settings
    from .database import make_engine, make_session_maker
    from .models import User

    cfg = Settings()
    engine = make_engine(cfg.db_path)
    session_maker = make_session_maker(engine)
    ph = PasswordHasher()
    used = password or secrets.token_urlsafe(16)
    try:
        async with session_maker() as session:
            u = (
                await session.execute(
                    select(User).where(User.email == email.strip().lower())
                )
            ).scalar_one_or_none()
            if not u:
                return False, "not_found", None
            u.hashed_password = ph.hash(used)
            session.add(u)
            await session.commit()
            return True, None, used
    finally:
        await engine.dispose()


@app.command()
def user_reset_password(
    email: str = typer.Option(..., "--email", "-e"),
    password: str | None = typer.Option(None, "--password", "-p"),
) -> None:
    """Reset a user's password."""
    ok, err_msg, used = asyncio.run(_async_reset_password(email, password))
    if not ok:
        typer.echo(f"Failed: {err_msg}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Password reset for {email}.")
    if not password:
        typer.echo(f"New password: {used}")


async def _async_set_active(email: str, active: bool):
    from sqlmodel import select

    from .config import Settings
    from .database import make_engine, make_session_maker
    from .models import User

    cfg = Settings()
    engine = make_engine(cfg.db_path)
    session_maker = make_session_maker(engine)
    try:
        async with session_maker() as session:
            u = (
                await session.execute(
                    select(User).where(User.email == email.strip().lower())
                )
            ).scalar_one_or_none()
            if not u:
                return False, "not_found"
            u.is_active = active
            session.add(u)
            await session.commit()
            return True, None
    finally:
        await engine.dispose()


@app.command()
def user_enable(email: str = typer.Option(..., "--email", "-e")) -> None:
    """Enable a user."""
    ok, err_msg = asyncio.run(_async_set_active(email, True))
    if not ok:
        typer.echo(f"Failed: {err_msg}", err=True)
        raise typer.Exit(1)
    typer.echo(f"User {email} enabled.")


@app.command()
def user_disable(email: str = typer.Option(..., "--email", "-e")) -> None:
    """Disable a user."""
    ok, err_msg = asyncio.run(_async_set_active(email, False))
    if not ok:
        typer.echo(f"Failed: {err_msg}", err=True)
        raise typer.Exit(1)
    typer.echo(f"User {email} disabled.")


async def _async_delete_user(email: str):
    from sqlmodel import select

    from .config import Settings
    from .database import make_engine, make_session_maker
    from .models import User

    cfg = Settings()
    engine = make_engine(cfg.db_path)
    session_maker = make_session_maker(engine)
    try:
        async with session_maker() as session:
            u = (
                await session.execute(
                    select(User).where(User.email == email.strip().lower())
                )
            ).scalar_one_or_none()
            if not u:
                return False, "not_found"
            await session.delete(u)
            await session.commit()
            return True, None
    finally:
        await engine.dispose()


@app.command()
def user_delete(
    email: str = typer.Option(..., "--email", "-e"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a user."""
    if not yes:
        if not typer.confirm(f"Delete user {email}?"):
            typer.echo("Cancelled.")
            raise typer.Exit(0)
    ok, err_msg = asyncio.run(_async_delete_user(email))
    if not ok:
        typer.echo(f"Failed: {err_msg}", err=True)
        raise typer.Exit(1)
    typer.echo(f"User {email} deleted.")


@app.callback(invoke_without_command=True)
def default_main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        serve()


if __name__ == "__main__":
    app()
