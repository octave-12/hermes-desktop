"""
SQLite persistence for sessions and messages.
"""
import sqlite3
import json
import time
from typing import Optional

from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id                  TEXT PRIMARY KEY,
            title               TEXT NOT NULL DEFAULT '新对话',
            hermes_session_id   TEXT,
            created_at          INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS messages (
            id          TEXT PRIMARY KEY,
            session_id  TEXT NOT NULL,
            role        TEXT NOT NULL,
            content     TEXT NOT NULL DEFAULT '',
            tool_calls  TEXT,
            timestamp   INTEGER NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id, timestamp);
    """)
    # Migration: add hermes_session_id column if missing
    try:
        conn.execute("ALTER TABLE sessions ADD COLUMN hermes_session_id TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    conn.close()


# ── Session operations ────────────────────────────────────────

def create_session(session_id: str, title: str = "新对话") -> dict:
    conn = get_connection()
    now = int(time.time() * 1000)
    conn.execute(
        "INSERT INTO sessions (id, title, created_at) VALUES (?, ?, ?)",
        (session_id, title, now),
    )
    conn.commit()
    conn.close()
    return {"id": session_id, "title": title, "createdAt": now}


def list_sessions() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, title, created_at FROM sessions ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [{"id": r["id"], "title": r["title"], "createdAt": r["created_at"]} for r in rows]


def update_session_title(session_id: str, title: str):
    conn = get_connection()
    conn.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))
    conn.commit()
    conn.close()


def delete_session(session_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()


# ── Message operations ────────────────────────────────────────

def add_message(
    message_id: str,
    session_id: str,
    role: str,
    content: str,
    tool_calls: Optional[list] = None,
    timestamp: Optional[int] = None,
):
    conn = get_connection()
    ts = timestamp or int(time.time() * 1000)
    tc_json = json.dumps(tool_calls) if tool_calls else None
    conn.execute(
        "INSERT INTO messages (id, session_id, role, content, tool_calls, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (message_id, session_id, role, content, tc_json, ts),
    )
    conn.commit()
    conn.close()


def update_message_content(message_id: str, content: str, tool_calls: Optional[list] = None):
    conn = get_connection()
    tc_json = json.dumps(tool_calls) if tool_calls else None
    conn.execute(
        "UPDATE messages SET content = ?, tool_calls = ? WHERE id = ?",
        (content, tc_json, message_id),
    )
    conn.commit()
    conn.close()


def get_session_messages(session_id: str) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, role, content, tool_calls, timestamp FROM messages "
        "WHERE session_id = ? ORDER BY timestamp ASC",
        (session_id,),
    ).fetchall()
    conn.close()
    messages = []
    for r in rows:
        msg = {
            "id": r["id"],
            "role": r["role"],
            "content": r["content"],
            "timestamp": r["timestamp"],
        }
        if r["tool_calls"]:
            msg["toolCalls"] = json.loads(r["tool_calls"])
        messages.append(msg)
    return messages


# ── Hermes session tracking ───────────────────────────────────

def get_hermes_session_id(session_id: str) -> Optional[str]:
    conn = get_connection()
    row = conn.execute(
        "SELECT hermes_session_id FROM sessions WHERE id = ?", (session_id,)
    ).fetchone()
    conn.close()
    return row["hermes_session_id"] if row else None


def set_hermes_session_id(session_id: str, hermes_session_id: str):
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET hermes_session_id = ? WHERE id = ?",
        (hermes_session_id, session_id),
    )
    conn.commit()
    conn.close()
