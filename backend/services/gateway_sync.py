"""
Gateway Sync Service.
Syncs messages from Hermes Gateway's state.db to Desktop.
"""
import asyncio
import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime


class GatewaySync:
    """Sync messages from Hermes Gateway to Desktop."""
    
    def __init__(self, hermes_home: Optional[Path] = None):
        self.hermes_home = hermes_home or (Path.home() / ".hermes")
        self.state_db_path = self.hermes_home / "state.db"
        self.gateway_state_path = self.hermes_home / "gateway_state.json"
        self._running = False
        self._last_session_check = 0.0
        self._last_message_check = 0.0
        self._known_sessions: set = set()
        self._known_messages: set = set()
        
    def is_gateway_running(self) -> bool:
        """Check if Gateway is running."""
        if not self.gateway_state_path.exists():
            return False
        try:
            with open(self.gateway_state_path, "r") as f:
                state = json.load(f)
            return state.get("gateway_state") == "running"
        except Exception:
            return False
    
    def get_weixin_status(self) -> Dict[str, Any]:
        """Get Weixin connection status from Gateway."""
        if not self.gateway_state_path.exists():
            return {"connected": False, "error": "Gateway state file not found"}
        try:
            with open(self.gateway_state_path, "r") as f:
                state = json.load(f)
            platforms = state.get("platforms", {})
            weixin = platforms.get("weixin", {})
            return {
                "connected": weixin.get("state") == "connected",
                "error_code": weixin.get("error_code"),
                "error_message": weixin.get("error_message"),
                "updated_at": weixin.get("updated_at"),
                "gateway_running": state.get("gateway_state") == "running"
            }
        except Exception as e:
            return {"connected": False, "error": str(e)}
    
    def get_weixin_account(self) -> Optional[Dict[str, str]]:
        """Get current Weixin account info."""
        accounts_dir = self.hermes_home / "weixin" / "accounts"
        if not accounts_dir.exists():
            return None
        
        for account_file in accounts_dir.glob("*.bot.json"):
            try:
                with open(account_file, "r") as f:
                    return json.load(f)
            except Exception:
                continue
        return None
    
    def get_sessions(self, source: str = "weixin", limit: int = 50) -> List[Dict[str, Any]]:
        """Get sessions from Gateway state.db."""
        if not self.state_db_path.exists():
            return []
        
        try:
            conn = sqlite3.connect(str(self.state_db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT id, source, user_id, model, title, message_count, 
                       started_at, ended_at, end_reason
                FROM sessions
                WHERE source = ?
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (source, limit)
            )
            
            sessions = []
            for row in cursor.fetchall():
                sessions.append({
                    "id": row["id"],
                    "source": row["source"],
                    "user_id": row["user_id"],
                    "model": row["model"],
                    "title": row["title"],
                    "message_count": row["message_count"],
                    "started_at": row["started_at"],
                    "ended_at": row["ended_at"],
                    "end_reason": row["end_reason"]
                })
            
            conn.close()
            return sessions
        except Exception as e:
            print(f"[GatewaySync] Error getting sessions: {e}")
            return []
    
    def get_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get messages for a session from Gateway state.db."""
        if not self.state_db_path.exists():
            return []
        
        try:
            conn = sqlite3.connect(str(self.state_db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT id, session_id, role, content, created_at, 
                       input_tokens, output_tokens, tool_calls
                FROM messages
                WHERE session_id = ?
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (session_id, limit)
            )
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                    "input_tokens": row["input_tokens"],
                    "output_tokens": row["output_tokens"],
                    "tool_calls": row["tool_calls"]
                })
            
            conn.close()
            return messages
        except Exception as e:
            print(f"[GatewaySync] Error getting messages: {e}")
            return []
    
    def get_recent_messages(self, since_timestamp: float = 0.0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent messages across all Weixin sessions."""
        if not self.state_db_path.exists():
            return []
        
        try:
            conn = sqlite3.connect(str(self.state_db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT m.id, m.session_id, m.role, m.content, m.created_at,
                       m.input_tokens, m.output_tokens, s.title as session_title,
                       s.source as session_source
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE s.source = 'weixin' AND m.created_at > ?
                ORDER BY m.created_at DESC
                LIMIT ?
                """,
                (since_timestamp, limit)
            )
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "id": row["id"],
                    "session_id": row["session_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "created_at": row["created_at"],
                    "input_tokens": row["input_tokens"],
                    "output_tokens": row["output_tokens"],
                    "session_title": row["session_title"],
                    "session_source": row["session_source"]
                })
            
            conn.close()
            return messages
        except Exception as e:
            print(f"[GatewaySync] Error getting recent messages: {e}")
            return []


gateway_sync = GatewaySync()
