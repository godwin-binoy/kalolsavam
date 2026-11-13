"""Single schema authority: Alembic. Nothing else creates or migrates tables."""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parent.parent


def alembic_config(db_path: str | Path | None = None) -> Config:
    """Build an Alembic config that is independent of the current working dir."""
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "server" / "alembic"))
    cfg.set_main_option("prepend_sys_path", str(ROOT))
    if db_path is not None:
        target = str(Path(db_path).expanduser().resolve()).replace("%", "%%")
        cfg.set_main_option("kal_db_path", target)
    return cfg


def upgrade_to_head(db_path: str | Path | None = None) -> None:
    command.upgrade(alembic_config(db_path), "head")
