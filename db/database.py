import sqlite3
import os
import json
import uuid
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "analyst.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def create_dataset(filename: str, schema_info: str, dataset_id: str | None = None) -> str:
    """Registers a new dataset with an explicit id (used by the /upload endpoint,
    where the caller wants the id before it saves the file to disk)."""
    dataset_id = dataset_id or str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        "INSERT INTO datasets (id, filename, uploaded_at, schema_json) VALUES (?, ?, ?, ?)",
        (dataset_id, filename, datetime.now(timezone.utc).isoformat(), json.dumps({"raw": schema_info})),
    )
    conn.commit()
    conn.close()
    return dataset_id


def upsert_dataset(filename: str, schema_info: str) -> str:
    """Registers a dataset (idempotent per filename) and returns its id.
    Used by run_slice.py, where the same sample CSV is reused across runs."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM datasets WHERE filename = ?", (filename,))
    row = cur.fetchone()
    conn.close()
    if row:
        return row["id"]
    return create_dataset(filename, schema_info)


def get_dataset(dataset_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_run(run_id: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_runs(dataset_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM runs WHERE dataset_id = ? ORDER BY created_at DESC", (dataset_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_attempts(run_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM run_attempts WHERE run_id = ? ORDER BY attempt_number", (run_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_run(dataset_id: str, question: str) -> str:
    run_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        "INSERT INTO runs (id, dataset_id, question, plan, final_code, chart_path, "
        "summary, retry_count, status, created_at) VALUES (?, ?, ?, '', '', '', '', 0, 'running', ?)",
        (run_id, dataset_id, question, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()
    return run_id


def log_attempt(run_id: str, attempt_number: int, code: str, error: str | None, succeeded: bool):
    conn = get_connection()
    conn.execute(
        "INSERT INTO run_attempts (id, run_id, attempt_number, code, error, succeeded) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), run_id, attempt_number, code, error, succeeded),
    )
    conn.commit()
    conn.close()


def finalize_run(run_id: str, plan: str, final_code: str, chart_path: str | None,
                  summary: str, retry_count: int, status: str):
    conn = get_connection()
    conn.execute(
        "UPDATE runs SET plan = ?, final_code = ?, chart_path = ?, summary = ?, "
        "retry_count = ?, status = ? WHERE id = ?",
        (plan, final_code, chart_path or "", summary, retry_count, status, run_id),
    )
    conn.commit()
    conn.close()
