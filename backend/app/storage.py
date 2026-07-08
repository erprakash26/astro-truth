"""SQLite persistence for computed charts (share links)."""

import json
import secrets
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "charts.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS charts (
            share_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL
        )
        """
    )
    return conn


def new_share_id() -> str:
    return secrets.token_urlsafe(8)


def save_chart(share_id: str, payload: dict) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO charts (share_id, payload) VALUES (?, ?)",
            (share_id, json.dumps(payload)),
        )


def load_chart(share_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT payload FROM charts WHERE share_id = ?", (share_id,)
        ).fetchone()
    if row is None:
        return None
    return json.loads(row[0])
