"""Test fixtures: isolated SQLite DB and FastAPI test client."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.auth import _RATE_BUCKETS
from server.config import Settings
from server.db import Database


@pytest.fixture
def client(tmp_path, monkeypatch):
    _RATE_BUCKETS.clear()
    db_path = tmp_path / "test_kalolsavam.db"

    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("PUBLIC_ORIGIN", "http://testserver")
    monkeypatch.setenv("ALLOWED_ORIGINS", "")
    monkeypatch.setenv("SESSION_TTL_MIN", "60")
    monkeypatch.setenv("SECRET_KEY", "super-secret-test-key-01234567890123456789")

    cfg = Settings()
    db = Database(db_path)
    db.init_schema()
    app = create_app(cfg, db)

    try:
        with TestClient(app) as c:
            yield c
    finally:
        _RATE_BUCKETS.clear()
