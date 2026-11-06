"""Test fixtures: isolated DB per test, sync TestClient."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.config import Settings
from server.db import Database


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("PUBLIC_ORIGIN", "http://testserver")
    monkeypatch.setenv("SESSION_TTL_MIN", "60")
    monkeypatch.setenv("IDLE_LOCK_MIN", "30")
    cfg = Settings()
    db = Database(db_path)
    app = create_app(cfg, db)
    with TestClient(app) as c:
        yield c
