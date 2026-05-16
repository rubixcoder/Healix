import os
import sys
from typing import Any

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents import memory


class FakeCursor:
    def __init__(self):
        self.executed = []
        self._rows = []

    def execute(self, query: str, params: tuple | None = None):
        self.executed.append((query.strip(), params))
        if query.strip().startswith("INSERT INTO incident_history"):
            self._rows = [(1,)]
        elif query.strip().startswith("INSERT INTO fix_history"):
            self._rows = [(2,)]
        else:
            self._rows = []

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return [
            {
                "id": 1,
                "created_at": "2026-05-16T00:00:00Z",
                "error_type": "IndexError",
                "message": "list index out of range",
                "file_path": "demo_app/logic.py",
                "line_number": 2,
                "service_name": "demo_app",
                "logs": "IndexError: list index out of range",
            }
        ]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self, row_factory=None):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_initialize_database_executes_schema_creation(monkeypatch):
    fake_cursor = FakeCursor()
    fake_conn = FakeConnection(fake_cursor)

    monkeypatch.setattr(memory, "_get_connection", lambda: fake_conn)

    memory.initialize_database()

    assert any("CREATE EXTENSION IF NOT EXISTS vector" in query for query, _ in fake_cursor.executed)
    assert any("CREATE TABLE IF NOT EXISTS incident_history" in query for query, _ in fake_cursor.executed)
    assert any("CREATE TABLE IF NOT EXISTS fix_history" in query for query, _ in fake_cursor.executed)


def test_save_incident_returns_id(monkeypatch):
    fake_cursor = FakeCursor()
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(memory, "_get_connection", lambda: fake_conn)

    event = {
        "error_type": "IndexError",
        "message": "list index out of range",
        "file": "demo_app/logic.py",
        "line": 2,
        "stacktrace": "",
        "service_name": "demo_app",
    }

    incident_id = memory.save_incident(event, "logs", "code", {"python_version": "3.12"})
    assert incident_id == 1
    assert any("INSERT INTO incident_history" in query for query, _ in fake_cursor.executed)


def test_save_fix_result_returns_id(monkeypatch):
    fake_cursor = FakeCursor()
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(memory, "_get_connection", lambda: fake_conn)

    fix_id = memory.save_fix_result(1, "fix", "passed", "stdout", "patch")
    assert fix_id == 2
    assert any("INSERT INTO fix_history" in query for query, _ in fake_cursor.executed)


def test_get_similar_incidents_returns_list(monkeypatch):
    fake_cursor = FakeCursor()
    fake_conn = FakeConnection(fake_cursor)
    monkeypatch.setattr(memory, "_get_connection", lambda: fake_conn)

    results = memory.get_similar_incidents("IndexError", "demo_app", limit=1)
    assert isinstance(results, list)
    assert results[0]["error_type"] == "IndexError"
