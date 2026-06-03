"""
Gateway Sync Service
Periodically polls Hermes Gateway's state.db for new messages and sessions.
Broadcasts full message content and session data to all connected WebSocket clients.
"""
import asyncio
import sqlite3
import json
import time
from pathlib import Path


class GatewaySync:
    def __init__(self, broadcast_fn, db_module):
        self.broadcast = broadcast_fn
        self.db = db_module
        self.last_message_id: int = 0       # Track by max message rowid
        self.last_session_ids: set[str] = set()
        self.last_active_session: str | None = None
        self.running = False
        self._task = None

    def _get_gateway_db_path(self) -> Path | None:
        path = Path.home() / ".hermes" / "state.db"
        return path if path.exists() else None

    def _get_max_message_id(self) -> int:
        """Get the highest message ID from gateway DB."""
        gateway_db = self._get_gateway_db_path()
        if not gateway_db:
            return 0
        try:
            conn = sqlite3.connect(str(gateway_db))
            row = conn.execute(
                """
                SELECT MAX(m.rowid) FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE s.source = 'weixin' AND m.role IN ('user', 'assistant')
                """
            ).fetchone()
            conn.close()
            return row[0] if row and row[0] else 0
        except Exception:
            return 0

    def _get_session_ids(self) -> set[str]:
        gateway_db = self._get_gateway_db_path()
        if not gateway_db:
            return set()
        try:
            conn = sqlite3.connect(str(gateway_db))
            rows = conn.execute(
                "SELECT id FROM sessions WHERE source = 'weixin'"
            ).fetchall()
            conn.close()
            return {r[0] for r in rows}
        except Exception:
            return set()

    def _get_session_details(self, session_id: str) -> dict | None:
        """Fetch session metadata from gateway DB."""
        gateway_db = self._get_gateway_db_path()
        if not gateway_db:
            return None
        try:
            conn = sqlite3.connect(str(gateway_db))
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT id, title, started_at FROM sessions WHERE id = ?",
                (session_id,)
            ).fetchone()
            conn.close()
            if row:
                return {
                    "id": row["id"],
                    "title": row["title"] or f"微信-{row['id'][:8]}",
                    "createdAt": int(row["started_at"] * 1000) if row["started_at"] else int(time.time() * 1000),
                }
            return None
        except Exception:
            return None

    def _get_new_messages(self, after_id: int, limit: int = 50) -> list[dict]:
        """Fetch messages with rowid > after_id from gateway DB."""
        gateway_db = self._get_gateway_db_path()
        if not gateway_db:
            return []
        try:
            conn = sqlite3.connect(str(gateway_db))
            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                """
                SELECT m.rowid, m.id, m.session_id, m.role, m.content, m.timestamp, m.tool_calls
                FROM messages m
                JOIN sessions s ON m.session_id = s.id
                WHERE s.source = 'weixin' AND m.role IN ('user', 'assistant')
                  AND m.rowid > ?
                ORDER BY m.rowid ASC
                LIMIT ?
                """,
                (after_id, limit)
            ).fetchall()

            messages = []
            for r in rows:
                msg = {
                    "id": f"gateway-{r['id']}",
                    # Always route gateway messages to the consolidated wechat-session
                    # This prevents creating duplicate sessions in the frontend sidebar
                    "session_id": "wechat-session",
                    "raw_session_id": r["session_id"],  # Original gateway session for active tracking
                    "role": r["role"],
                    "content": r["content"] or "",
                    "timestamp": int(r["timestamp"] * 1000) if r["timestamp"] else int(time.time() * 1000),
                    "source": "gateway",
                }
                if r["tool_calls"]:
                    try:
                        raw_tool_calls = json.loads(r["tool_calls"])
                        tool_calls = []
                        for tc in raw_tool_calls:
                            tool_call = {
                                "name": tc.get("function", {}).get("name", "unknown"),
                                "status": "completed",
                            }
                            args = tc.get("function", {}).get("arguments", "")
                            if args:
                                try:
                                    args_obj = json.loads(args)
                                    tool_call["result"] = json.dumps(args_obj, indent=2, ensure_ascii=False)
                                except Exception:
                                    tool_call["result"] = args
                            tool_calls.append(tool_call)
                        msg["toolCalls"] = tool_calls
                    except Exception as e:
                        print(f"[GatewaySync] Failed to parse tool_calls: {e}")
                messages.append(msg)

            conn.close()
            return messages

        except Exception as e:
            print(f"[GatewaySync] Error reading new messages: {e}")
            return []

    async def start(self):
        """Start the background sync loop."""
        if self.running:
            return
        self.running = True
        # Initialize baselines
        self.last_message_id = self._get_max_message_id()
        self.last_session_ids = self._get_session_ids()
        # Initialize active session from the session with the most recent message
        self._init_active_session()
        self._task = asyncio.create_task(self._sync_loop())
        print(f"[GatewaySync] Started (baseline: msg_id={self.last_message_id}, {len(self.last_session_ids)} sessions)")

    def _init_active_session(self):
        """Set active gateway session to the one with the most recent message."""
        gateway_db = self._get_gateway_db_path()
        if not gateway_db:
            return
        try:
            conn = sqlite3.connect(str(gateway_db))
            row = conn.execute(
                "SELECT session_id FROM messages m "
                "JOIN sessions s ON m.session_id = s.id "
                "WHERE s.source = 'weixin' AND m.role IN ('user', 'assistant') "
                "ORDER BY m.timestamp DESC LIMIT 1"
            ).fetchone()
            conn.close()
            if row:
                self.last_active_session = row[0]
                self.db.set_active_gateway_session(row[0])
                print(f"[GatewaySync] Initial active session: {row[0][:16]}...")
        except Exception as e:
            print(f"[GatewaySync] Failed to init active session: {e}")

    async def stop(self):
        """Stop the background sync loop."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _sync_loop(self):
        """Poll Gateway DB every 5 seconds for changes."""
        while self.running:
            try:
                await asyncio.sleep(5)
                await self._check_for_updates()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[GatewaySync] Error: {e}")

    async def _check_for_updates(self):
        """Check if Gateway DB has new data and broadcast if so."""
        # ── Check new sessions ──
        current_session_ids = self._get_session_ids()
        new_session_ids = current_session_ids - self.last_session_ids
        if new_session_ids:
            print(f"[GatewaySync] New gateway sessions: {new_session_ids}")
            self.last_session_ids = current_session_ids
            # Don't broadcast session_created or mirror to local DB.
            # Gateway sessions are consolidated into the single "wechat-session" view.
            # Real-time messages are already routed to "wechat-session" via _get_new_messages.
            # Trigger a session list refresh so the UI stays in sync.
            await self.broadcast({
                "type": "gateway_sessions_updated",
            })

        # ── Check new messages ──
        current_max_id = self._get_max_message_id()
        if current_max_id > self.last_message_id:
            new_messages = self._get_new_messages(self.last_message_id, limit=50)
            if new_messages:
                print(f"[GatewaySync] New gateway messages: +{len(new_messages)} (max_id: {current_max_id})")
                # Track active session (the one with the newest message)
                newest_session = new_messages[-1].get("raw_session_id")
                if newest_session and newest_session != self.last_active_session:
                    self.last_active_session = newest_session
                    self.db.set_active_gateway_session(newest_session)
                    await self.broadcast({
                        "type": "gateway_active_session_changed",
                        "session_id": newest_session,
                    })
                    print(f"[GatewaySync] Active session changed: {newest_session[:16]}...")
                # Broadcast messages
                for msg in new_messages:
                    await self.broadcast({
                        "type": "new_message",
                        "session_id": msg["session_id"],
                        "message_id": msg["id"],
                        "role": msg["role"],
                        "content": msg["content"],
                        "timestamp": msg["timestamp"],
                        "source": msg.get("source", "gateway"),
                        "gateway_session_id": msg.get("raw_session_id", ""),
                    })
            self.last_message_id = current_max_id
