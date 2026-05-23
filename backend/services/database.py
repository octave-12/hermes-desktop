"""
SQLite persistence for sessions and messages.
"""
import sqlite3
import json
import time
from typing import Optional
from contextlib import contextmanager

from config import DB_PATH


@contextmanager
def get_connection():
    """Get database connection with automatic cleanup."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def _get_conn():
    """Legacy helper for non-contextmanager usage."""
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
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

            CREATE TABLE IF NOT EXISTS config (
                key     TEXT PRIMARY KEY,
                value   TEXT NOT NULL
            );

            -- Indexes for performance optimization
            
            -- Sessions table indexes
            CREATE INDEX IF NOT EXISTS idx_sessions_created_at
                ON sessions(created_at DESC);
            
            CREATE INDEX IF NOT EXISTS idx_sessions_hermes_sid
                ON sessions(hermes_session_id);
            
            -- Messages table indexes
            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id, timestamp);
            
            CREATE INDEX IF NOT EXISTS idx_messages_session_role
                ON messages(session_id, role);
            
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp
                ON messages(timestamp);
        """)
        # Migration: add hermes_session_id column if missing
        try:
            conn.execute("ALTER TABLE sessions ADD COLUMN hermes_session_id TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists


# ── Session operations ────────────────────────────────────────

def create_session(session_id: str, title: str = "新对话") -> dict:
    now = int(time.time() * 1000)
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions (id, title, created_at) VALUES (?, ?, ?)",
            (session_id, title, now),
        )
        conn.commit()
    return {"id": session_id, "title": title, "createdAt": now}


def list_sessions() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at FROM sessions ORDER BY created_at DESC"
        ).fetchall()
    return [{"id": r["id"], "title": r["title"], "createdAt": r["created_at"]} for r in rows]


def update_session_title(session_id: str, title: str):
    with get_connection() as conn:
        conn.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))
        conn.commit()


def delete_session(session_id: str):
    """Delete session and all its messages (CASCADE)."""
    with get_connection() as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()


# ── Message operations ────────────────────────────────────────

def add_message(
    message_id: str,
    session_id: str,
    role: str,
    content: str,
    tool_calls: Optional[list] = None,
    timestamp: Optional[int] = None,
):
    ts = timestamp or int(time.time() * 1000)
    tc_json = json.dumps(tool_calls) if tool_calls else None
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (id, session_id, role, content, tool_calls, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (message_id, session_id, role, content, tc_json, ts),
        )
        conn.commit()


def update_message_content(message_id: str, content: str, tool_calls: Optional[list] = None):
    tc_json = json.dumps(tool_calls) if tool_calls else None
    with get_connection() as conn:
        conn.execute(
            "UPDATE messages SET content = ?, tool_calls = ? WHERE id = ?",
            (content, tc_json, message_id),
        )
        conn.commit()


def get_session_messages(session_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, role, content, tool_calls, timestamp FROM messages "
            "WHERE session_id = ? ORDER BY timestamp ASC",
            (session_id,),
        ).fetchall()
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


def get_user_message_count(session_id: str) -> int:
    """Get count of user messages for a session (optimized for title update check)."""
    with get_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ? AND role = 'user'",
            (session_id,),
        ).fetchone()[0]
    return count


# ── Hermes session tracking ───────────────────────────────────

def get_hermes_session_id(session_id: str) -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT hermes_session_id FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
    return row["hermes_session_id"] if row else None


def set_hermes_session_id(session_id: str, hermes_session_id: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE sessions SET hermes_session_id = ? WHERE id = ?",
            (hermes_session_id, session_id),
        )
        conn.commit()


# ── Config operations ────────────────────────────────────────

def get_config(key: str, default: str = "") -> str:
    """Get a config value by key."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM config WHERE key = ?", (key,)
        ).fetchone()
    return row["value"] if row else default


def set_config(key: str, value: str):
    """Set a config value."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()


def get_all_config() -> dict:
    """Get all config as a dictionary."""
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM config").fetchall()
    return {r["key"]: r["value"] for r in rows}


def get_hermes_default_model() -> str:
    """Read default model from Hermes config.yaml."""
    import os
    import yaml
    
    hermes_config_path = os.path.expanduser("~/.hermes/config.yaml")
    
    try:
        if os.path.exists(hermes_config_path):
            with open(hermes_config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            # Try to get model from config
            if 'model' in config:
                model_config = config['model']
                # Return default model if exists
                if 'default' in model_config:
                    return model_config['default']
                # Return provider if no default specified
                if 'provider' in model_config:
                    return model_config['provider']
    except Exception as e:
        print(f"[Config] Failed to read Hermes config: {e}")
    
    # Fallback to default
    return "deepseek-v4-flash"
