"""Test fixtures: isolated SQLite DB per test run, sync TestClient."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.config import Settings
from server.db import Database


def _write_stub_dist(dist_root):
    (dist_root / "admin").mkdir(parents=True, exist_ok=True)
    (dist_root / "admin" / "index.html").write_text(
        '<!doctype html><html><head><title>Admin</title></head>'
        '<body><h1>Admin Console</h1>'
        '<script src="/dashboard/js/admin.js"></script>'
        '</body></html>',
        encoding="utf-8",
    )
    (dist_root / "stagemaster").mkdir(parents=True, exist_ok=True)
    (dist_root / "stagemaster" / "index.html").write_text(
        '<!doctype html><html><head><title>Stage</title></head>'
        '<body><h1>Stage Control</h1>'
        '<script src="/dashboard/js/board.js"></script>'
        '</body></html>',
        encoding="utf-8",
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test_kalolsavam.db"
    dist_path = tmp_path / "dist"
    dist_path.mkdir()
    _write_stub_dist(dist_path)

    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("PUBLIC_ORIGIN", "http://testserver")
    monkeypatch.setenv("SESSION_TTL_MIN", "60")
    monkeypatch.setenv("SECRET_KEY", "super-secret-test-key-01234567890123456789")
    monkeypatch.setenv("DIST_PATH", str(dist_path))

    cfg = Settings()
    db = Database(db_path)
    app = create_app(cfg, db)
    with TestClient(app) as c:
        yield c
