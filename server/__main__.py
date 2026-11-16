"""Unified entry point & management CLI: python -m server <command>."""
from __future__ import annotations

import json
import logging
import secrets
import sqlite3
import time as _t
from pathlib import Path

import typer

from .auth import ph
from .config import Settings
from .db import Database

app = typer.Typer(help="Kalolsavam management CLI", no_args_is_help=False)
log = logging.getLogger("kalolsavam")

FALLBACK_STAGES = [
    {"n": i, "name": name}
    for i, name in enumerate([
        "St. Antony's HSS Ground", "HS Hall", "GLPS Mala",
        "HSS A1 B1 Classes", "HSS Seminar Hall", "Vyaapaara Bhavan",
        "HSS 1st Floor Class", "HS 9E Class", "HS Arabic Class",
    ], start=1)
]


def _init_db() -> tuple[Settings, Database]:
    cfg = Settings()
    db = Database(Path(cfg.db_path))
    db.init_schema()
    return cfg, db


@app.command()
def serve(
    host: str | None = typer.Option(None, "--host", "-h"),
    port: int | None = typer.Option(None, "--port", "-p"),
    reload: bool = typer.Option(False, "--reload"),
) -> None:
    """Run the FastAPI + Uvicorn server."""
    import uvicorn

    from .app import create_app, setup_logging

    setup_logging()
    cfg, db = _init_db()
    uvicorn.run(
        app=create_app(cfg, db),
        host=host or cfg.server_host,
        port=port or cfg.server_port,
        reload=reload,
        log_level="warning",
        proxy_headers=False,
    )


@app.command()
def migrate() -> None:
    """Ensure SQLite schema is initialized and up to date."""
    _cfg, db = _init_db()
    db.close_all()
    typer.echo("Database schema initialized.")


@app.command()
def seed_admin(
    email: str = typer.Option("admin@kalolsavam.example.com", "--email", "-e"),
    password: str | None = typer.Option(None, "--password"),
) -> None:
    """Seed initial admin user if missing."""
    _cfg, db = _init_db()
    clean_email = email.strip().lower()
    if db.one("SELECT id FROM users WHERE email = ?", (clean_email,)):
        typer.echo(f"Admin user '{email}' already exists. Skipping.")
        return
    used_pw = password or secrets.token_urlsafe(16)
    db.ex(
        "INSERT INTO users(email, password_hash, role, stages, is_active, token_version, created_at) VALUES (?,?,?,?,1,1,?)",
        (clean_email, ph.hash(used_pw), "admin", "[]", db.now()),
    )
    typer.echo(f"Admin user '{email}' created.")
    typer.echo("Password: (provided via --password)" if password else f"Temporary password: {used_pw}")


@app.command()
def seed_stages(stages_file: Path = typer.Option(Path("src/data/stages.json"), "--file", "-f")) -> None:
    """Seed or update stages from stages.json."""
    _cfg, db = _init_db()
    items = FALLBACK_STAGES
    if stages_file.is_file():
        try:
            loaded = json.loads(stages_file.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                items = loaded
        except Exception as exc:
            typer.echo(f"Warning: {stages_file} unreadable ({exc}); using defaults.")
    with db.transaction():
        for s in items:
            vid = int(s["n"])
            db.ex(
                "INSERT INTO venues(id, name, kind, slug, active) VALUES (?,?,?,?,1) "
                "ON CONFLICT(id) DO UPDATE SET name = excluded.name, slug = excluded.slug",
                (vid, s["name"], s.get("kind") or "stage", s.get("slug") or f"stage-{vid}"),
            )
    typer.echo(f"Seeded/updated {len(items)} stages.")


@app.command()
def backup() -> None:
    """Create a hot online SQLite backup."""
    src = Path(Settings().db_path)
    if not src.exists():
        typer.echo(f"Database {src} does not exist.")
        raise typer.Exit(1)
    dst_dir = src.parent / "backups"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"{src.stem}-{_t.strftime('%Y%m%d-%H%M%S')}.db"
    src_con, dst_con = sqlite3.connect(str(src)), sqlite3.connect(str(dst))
    try:
        src_con.backup(dst_con)
    finally:
        dst_con.close()
        src_con.close()
    for old in sorted(dst_dir.glob(f"{src.stem}-*.db"), key=lambda f: f.stat().st_mtime)[:-24]:
        old.unlink(missing_ok=True)
    typer.echo(f"Backup created: {dst}")


@app.command()
def check() -> None:
    """Inspect database tables and registered users."""
    cfg, db = _init_db()
    tables = [r["name"] for r in db.q("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    users = db.one("SELECT COUNT(*) c FROM users")["c"]
    typer.echo(f"DB: {cfg.db_path} ({len(tables)} tables, {users} users)")


@app.command()
def user_create(
    email: str = typer.Option(..., "--email", "-e"),
    password: str = typer.Option(..., "--password", "-p"),
    role: str = typer.Option("admin", "--role"),
    stages: str = typer.Option("[]", "--stages"),
) -> None:
    if role not in ("admin", "stagemaster", "dataworker"):
        typer.echo(f"Invalid role: {role}", err=True)
        raise typer.Exit(1)
    try:
        stage_ids = [int(x) for x in json.loads(stages)] if stages else []
    except Exception:
        typer.echo(f"Invalid --stages JSON: {stages!r}", err=True)
        raise typer.Exit(1) from None
    _cfg, db = _init_db()
    clean_email = email.strip().lower()
    if db.one("SELECT id FROM users WHERE email = ?", (clean_email,)):
        typer.echo("Failed: email_taken", err=True)
        raise typer.Exit(1)
    cur = db.ex(
        "INSERT INTO users(email, password_hash, role, stages, is_active, token_version, created_at) VALUES (?,?,?,?,1,1,?)",
        (clean_email, ph.hash(password), role, json.dumps(stage_ids), db.now()),
    )
    typer.echo(f"User '{email}' created (id={cur.lastrowid}, role={role}).")


@app.command()
def user_list(json_output: bool = typer.Option(False, "--json")) -> None:
    _cfg, db = _init_db()
    rows = [dict(r) for r in db.q("SELECT id, email, role, stages, is_active FROM users ORDER BY email")]
    if json_output:
        typer.echo(json.dumps(rows, indent=2))
        return
    for u in rows:
        typer.echo(f"{u['email']:<40} {u['role']:<20} {'active' if u['is_active'] else 'disabled'}")


@app.command()
def user_reset_password(email: str = typer.Option(..., "--email", "-e"), password: str | None = typer.Option(None, "--password", "-p")) -> None:
    _cfg, db = _init_db()
    used = password or secrets.token_urlsafe(16)
    res = db.ex("UPDATE users SET password_hash = ?, token_version = token_version + 1 WHERE email = ?", (ph.hash(used), email.strip().lower()))
    if not res.rowcount:
        typer.echo("Failed: not_found", err=True)
        raise typer.Exit(1)
    typer.echo(f"Password reset for {email}.")
    if not password:
        typer.echo(f"New password: {used}")


def _set_active(email: str, active: bool) -> None:
    _cfg, db = _init_db()
    bump = "" if active else ", token_version = token_version + 1"
    if not db.ex(f"UPDATE users SET is_active = ?{bump} WHERE email = ?", (int(active), email.strip().lower())).rowcount:  # noqa: S608
        typer.echo("Failed: not_found", err=True)
        raise typer.Exit(1)
    typer.echo(f"User {email} {'enabled' if active else 'disabled'}.")


@app.command()
def user_enable(email: str = typer.Option(..., "--email", "-e")) -> None:
    _set_active(email, True)


@app.command()
def user_disable(email: str = typer.Option(..., "--email", "-e")) -> None:
    _set_active(email, False)


@app.command()
def user_delete(email: str = typer.Option(..., "--email", "-e"), yes: bool = typer.Option(False, "--yes", "-y")) -> None:
    if not yes and not typer.confirm(f"Delete user {email}?"):
        raise typer.Exit(0)
    _cfg, db = _init_db()
    if not db.ex("DELETE FROM users WHERE email = ?", (email.strip().lower(),)).rowcount:
        typer.echo("Failed: not_found", err=True)
        raise typer.Exit(1)
    typer.echo(f"User {email} deleted.")


@app.callback(invoke_without_command=True)
def default_main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        serve()


if __name__ == "__main__":
    app()
