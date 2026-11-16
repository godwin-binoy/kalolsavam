"""Unified management CLI: python -m server <command>."""
from __future__ import annotations

import asyncio
import json
import logging
import secrets
import sqlite3
import time as _t
from contextlib import asynccontextmanager
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


@asynccontextmanager
async def _auth_session():
    from .config import Settings
    from .database import make_engine, make_session_maker

    engine = make_engine(Settings().db_path)
    try:
        async with make_session_maker(engine)() as session:
            yield session
    finally:
        await engine.dispose()


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

    from .models import Role, User

    ph = PasswordHasher()
    used_password = password or secrets.token_urlsafe(16)
    async with _auth_session() as session:
        for rname in ("admin", "stagemaster", "dataworker"):
            if not (await session.execute(select(Role).where(Role.name == rname))).scalar_one_or_none():
                session.add(Role(name=rname))
        await session.commit()

        clean_email = email.strip().lower()
        if (await session.execute(select(User).where(User.email == clean_email))).scalar_one_or_none():
            return False, ""

        admin_role = (await session.execute(select(Role).where(Role.name == "admin"))).scalar_one()
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


@app.command()
def seed_admin(
    email: str = typer.Option("admin@kalolsavam.example.com", "--email", "-e", help="Admin email"),
    password: str | None = typer.Option(None, "--password", help="Admin password (generated if omitted)"),
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
    if password:
        typer.echo("Password: (provided via --password / ADMIN_PASSWORD)")
    else:
        typer.echo(f"Temporary password: {final_pass}")
        typer.echo("Sign in at /admin/ and change password immediately.")
    typer.echo("=" * 65)


@app.command()
def seed_stages(
    stages_file: Path = typer.Option(Path("src/data/stages.json"), "--file", "-f", help="Path to stages.json"),
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
            db.ex(
                "INSERT INTO venues(id, name, kind, slug, active) VALUES (?,?,?,?,1) "
                "ON CONFLICT(id) DO UPDATE SET name = excluded.name, slug = excluded.slug",
                (vid, s["name"], s.get("kind") or "stage", s.get("slug") or f"stage-{vid}"),
            )
    typer.echo(f"Seeded/updated {len(items)} stages in database.")


@app.command()
def backup() -> None:
    """Create a hot online SQLite backup of kalolsavam.db."""
    from .config import Settings

    src = Path(Settings().db_path)
    if not src.exists():
        typer.echo(f"Database {src} does not exist.")
        raise typer.Exit(code=1)

    dst_dir = src.parent / "backups"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"{src.stem}-{_t.strftime('%Y%m%d-%H%M%S')}.db"

    src_con = sqlite3.connect(str(src))
    dst_con = sqlite3.connect(str(dst))
    try:
        src_con.backup(dst_con)
    finally:
        dst_con.close()
        src_con.close()

    for old in sorted(dst_dir.glob(f"{src.stem}-*.db"), key=lambda f: f.stat().st_mtime)[:-24]:
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
    tables = [r["name"] for r in db.q("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    typer.echo(f"DB Path: {cfg.db_path}")
    typer.echo(f"Tables present ({len(tables)}): {', '.join(tables)}")
    user_count = db.one("SELECT COUNT(*) c FROM fullauth_users")["c"] if "fullauth_users" in tables else 0
    typer.echo(f"Users registered: {user_count}")


async def _async_list_users():
    from sqlmodel import select

    from .models import User

    async with _auth_session() as session:
        users = (await session.execute(select(User).order_by(User.email))).scalars().all()
        return [
            {"id": str(u.id), "email": u.email, "active": u.is_active, "roles": [r.name for r in u.roles], "stages": u.stages}
            for u in users
        ]


async def _async_create_user(email: str, password: str, role_name: str, stages: list[int]):
    from argon2 import PasswordHasher
    from sqlmodel import select

    from .models import Role, User

    ph = PasswordHasher()
    async with _auth_session() as session:
        clean_email = email.strip().lower()
        if (await session.execute(select(User).where(User.email == clean_email))).scalar_one_or_none():
            return False, "email_taken", None
        role = (await session.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
        if not role:
            role = Role(name=role_name)
            session.add(role)
            await session.commit()
            await session.refresh(role)
        u = User(
            email=clean_email,
            hashed_password=ph.hash(password),
            is_active=True,
            is_verified=True,
            stages=json.dumps(stages or []),
        )
        u.roles.append(role)
        session.add(u)
        await session.commit()
        return True, None, str(u.id)


@app.command()
def user_create(
    email: str = typer.Option(..., "--email", "-e"),
    password: str = typer.Option(..., "--password", "-p"),
    role: str = typer.Option("admin", "--role", help="admin, stagemaster, or dataworker"),
    stages: str = typer.Option("[]", "--stages", help="JSON array of stage numbers"),
) -> None:
    """Create a staff user with a given role and assigned stages."""
    from .config import Settings
    from .schema import upgrade_to_head

    if role not in ("admin", "stagemaster", "dataworker"):
        typer.echo(f"Invalid role: {role}", err=True)
        raise typer.Exit(1)
    try:
        stage_ids = [int(x) for x in json.loads(stages)] if stages else []
    except Exception:
        typer.echo(f"Invalid --stages JSON: {stages!r}", err=True)
        raise typer.Exit(1) from None

    upgrade_to_head(Settings().db_path)
    ok, err_msg, uid = asyncio.run(_async_create_user(email, password, role, stage_ids))
    if not ok:
        typer.echo(f"Failed: {err_msg}", err=True)
        raise typer.Exit(1)
    typer.echo(f"User '{email}' created (id={uid}, role={role}).")


@app.command()
def user_list(json_output: bool = typer.Option(False, "--json", help="Output JSON")) -> None:
    """List all users."""
    users = asyncio.run(_async_list_users())
    if json_output:
        typer.echo(json.dumps(users, indent=2))
        return
    if not users:
        typer.echo("No users.")
        return
    for u in users:
        typer.echo(f"{u['email']:<40} {','.join(u['roles']) or '-':<20} {'active' if u['active'] else 'disabled'}")


async def _async_mutate_user(email: str, op_name: str, value=None):
    from argon2 import PasswordHasher
    from sqlmodel import select

    from .models import User

    async with _auth_session() as session:
        u = (await session.execute(select(User).where(User.email == email.strip().lower()))).scalar_one_or_none()
        if not u:
            return False, "not_found", None
        if op_name == "password":
            used = value or secrets.token_urlsafe(16)
            u.hashed_password = PasswordHasher().hash(used)
            session.add(u)
            await session.commit()
            return True, None, used
        if op_name == "active":
            u.is_active = bool(value)
            session.add(u)
            await session.commit()
            return True, None, None
        if op_name == "delete":
            await session.delete(u)
            await session.commit()
            return True, None, None
        return False, "unknown_op", None


@app.command()
def user_reset_password(
    email: str = typer.Option(..., "--email", "-e"),
    password: str | None = typer.Option(None, "--password", "-p"),
) -> None:
    """Reset a user's password."""
    ok, err_msg, used = asyncio.run(_async_mutate_user(email, "password", password))
    if not ok:
        typer.echo(f"Failed: {err_msg}", err=True)
        raise typer.Exit(1)
    typer.echo(f"Password reset for {email}.")
    if not password:
        typer.echo(f"New password: {used}")


@app.command()
def user_enable(email: str = typer.Option(..., "--email", "-e")) -> None:
    """Enable a user."""
    ok, err_msg, _ = asyncio.run(_async_mutate_user(email, "active", True))
    if not ok:
        typer.echo(f"Failed: {err_msg}", err=True)
        raise typer.Exit(1)
    typer.echo(f"User {email} enabled.")


@app.command()
def user_disable(email: str = typer.Option(..., "--email", "-e")) -> None:
    """Disable a user."""
    ok, err_msg, _ = asyncio.run(_async_mutate_user(email, "active", False))
    if not ok:
        typer.echo(f"Failed: {err_msg}", err=True)
        raise typer.Exit(1)
    typer.echo(f"User {email} disabled.")


@app.command()
def user_delete(
    email: str = typer.Option(..., "--email", "-e"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    """Delete a user."""
    if not yes and not typer.confirm(f"Delete user {email}?"):
        typer.echo("Cancelled.")
        raise typer.Exit(0)
    ok, err_msg, _ = asyncio.run(_async_mutate_user(email, "delete"))
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
