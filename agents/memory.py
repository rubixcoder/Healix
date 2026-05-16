import json
import os
from typing import Any, Iterable

try:
    import psycopg
except ImportError:  # pragma: no cover
    psycopg = None

DEFAULT_DATABASE_URL = "postgresql://healix:healix@localhost:5432/healix"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def _get_connection():
    if psycopg is None:
        raise RuntimeError("psycopg is required for memory database support. Install it with psycopg[binary].")
    return psycopg.connect(get_database_url(), autocommit=True)


def initialize_database() -> None:
    """Create the memory database schema and enable pgvector."""
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_history (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ DEFAULT now(),
                    error_type TEXT NOT NULL,
                    message TEXT,
                    file_path TEXT,
                    line_number INTEGER,
                    stacktrace TEXT,
                    service_name TEXT,
                    logs TEXT,
                    code_snapshot TEXT,
                    environment_metadata JSONB,
                    embedding vector(1536)
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS fix_history (
                    id SERIAL PRIMARY KEY,
                    incident_id INTEGER REFERENCES incident_history(id) ON DELETE CASCADE,
                    suggested_fix TEXT,
                    status TEXT,
                    test_results TEXT,
                    patch_diff TEXT,
                    created_at TIMESTAMPTZ DEFAULT now()
                );
                """
            )


def save_incident(
    error_input: dict[str, Any],
    logs: str,
    code_snapshot: str,
    environment_metadata: dict[str, Any],
    embedding: Iterable[float] | None = None,
) -> int:
    """Persist a new incident to the memory database."""
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO incident_history (
                    error_type,
                    message,
                    file_path,
                    line_number,
                    stacktrace,
                    service_name,
                    logs,
                    code_snapshot,
                    environment_metadata,
                    embedding
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    error_input.get("error_type"),
                    error_input.get("message"),
                    error_input.get("file"),
                    error_input.get("line"),
                    error_input.get("stacktrace"),
                    error_input.get("service_name"),
                    logs,
                    code_snapshot,
                    json.dumps(environment_metadata),
                    list(embedding) if embedding is not None else None,
                ),
            )
            incident_id = cur.fetchone()[0]
    return incident_id


def save_fix_result(
    incident_id: int,
    suggested_fix: str,
    status: str,
    test_results: str,
    patch_diff: str,
) -> int:
    """Persist a fix result associated with an incident."""
    with _get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO fix_history (
                    incident_id,
                    suggested_fix,
                    status,
                    test_results,
                    patch_diff
                ) VALUES (%s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (incident_id, suggested_fix, status, test_results, patch_diff),
            )
            fix_id = cur.fetchone()[0]
    return fix_id


def get_similar_incidents(error_type: str, service_name: str, limit: int = 5) -> list[dict[str, Any]]:
    """Retrieve recent incidents with matching error type or service name."""
    with _get_connection() as conn:
        if psycopg is not None:
            cursor = conn.cursor(row_factory=psycopg.rows.dict_row)
        else:
            cursor = conn.cursor()

        with cursor as cur:
            cur.execute(
                """
                SELECT id, created_at, error_type, message, file_path, line_number, service_name, logs
                FROM incident_history
                WHERE error_type = %s OR service_name = %s
                ORDER BY created_at DESC
                LIMIT %s;
                """,
                (error_type, service_name, limit),
            )
            return cur.fetchall()
