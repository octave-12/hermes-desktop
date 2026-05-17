"""
Hermes Agent Service - Bridge between Desktop UI and Hermes Agent SDK
"""
import asyncio
import os
import re
import uuid
from typing import AsyncGenerator, Optional

from config import HERMES_BIN, HERMES_VENV_DIR
from services import database as db
from services.model_config import model_config_manager
from services.env_manager import env_manager


class HermesService:
    """Service that communicates with Hermes Agent."""

    def __init__(self):
        self._hermes_bin = HERMES_BIN
        self._env = os.environ.copy()
        venv_bin = os.path.join(HERMES_VENV_DIR, "bin")
        self._env["PATH"] = venv_bin + ":" + self._env.get("PATH", "")
        self._env["VIRTUAL_ENV"] = HERMES_VENV_DIR

    def _parse_hermes_output(self, raw: str) -> tuple[str, Optional[str]]:
        """
        Parse hermes CLI output to extract:
        - The actual AI response content (without CLI decorations)
        - The hermes session ID (for --resume multi-turn support)
        """
        lines = raw.split("\n")
        content_lines: list[str] = []
        hermes_session_id: Optional[str] = None
        in_content = False
        content_ended = False

        for line in lines:
            stripped = line.strip()

            # Extract hermes session id from "hermes --resume <id>"
            resume_match = re.search(r"hermes\s+--resume\s+(\S+)", line)
            if resume_match:
                hermes_session_id = resume_match.group(1)
                content_ended = True
                continue

            if content_ended:
                continue

            if stripped.startswith("Resume this session with"):
                content_ended = True
                continue

            if not in_content:
                # Skip pre-content metadata
                if stripped.startswith("Query:"):
                    continue
                if stripped in ("Initializing agent...", ""):
                    continue
                # Skip resume message: "↻ Resumed session ..."
                if stripped.startswith("↻") or stripped.startswith("Resumed session"):
                    continue
                # Hermes header line: "─ ✦ Hermes ─"
                if "Hermes" in line and ("─" in line or "━" in line or "✦" in line):
                    in_content = True
                    continue
                # Pure separator line
                if stripped and all(c in "─━═—─" for c in stripped):
                    continue
                # Actual content started without header (simpler format)
                if stripped:
                    in_content = True
                    content_lines.append(line)
                continue

            # Inside content: check for end separator
            if stripped and len(stripped) > 5 and all(c in "─━═—─" for c in stripped):
                content_ended = True
                continue

            content_lines.append(line)

        # Trim leading/trailing blank lines
        while content_lines and not content_lines[0].strip():
            content_lines.pop(0)
        while content_lines and not content_lines[-1].strip():
            content_lines.pop()

        return "\n".join(content_lines), hermes_session_id

    async def chat(
        self, session_id: str, user_message: str, user_msg_id: str
    ) -> AsyncGenerator[dict, None]:
        """
        Send message to Hermes Agent and stream back the response.
        Uses --resume for multi-turn conversation context.
        """
        # Persist user message
        db.add_message(user_msg_id, session_id, "user", user_message)

        # Update session title from first user message
        messages = db.get_session_messages(session_id)
        user_messages = [m for m in messages if m["role"] == "user"]
        if len(user_messages) == 1:
            title = user_message[:30] or "新对话"
            db.update_session_title(session_id, title)
            yield {"type": "session_title", "session_id": session_id, "title": title}

        # Get hermes session id for multi-turn resume
        hermes_sid = db.get_hermes_session_id(session_id)

        # Get model configuration
        model = model_config_manager.get_model_config(db.get_config("model", db.get_hermes_default_model()))
        model_id = model.get('id', 'deepseek-chat') if model else 'deepseek-chat'
        api_key_env = model.get('api_key_env') if model else None
        
        api_key = env_manager.get_api_key(model_id, api_key_env)
        api_base_url = db.get_config("apiBaseUrl", model.get('api_base_url', '') if model else '')
        temperature = db.get_config("temperature", "0.7")
        max_tokens = db.get_config("maxTokens", "2048")

        # Build command
        if hermes_sid:
            cmd = [self._hermes_bin, "--resume", hermes_sid, "chat", "-q", user_message]
        else:
            cmd = [self._hermes_bin, "chat", "-q", user_message]

        # Add model configuration as environment variables
        env = self._env.copy()
        if api_key:
            env["OPENAI_API_KEY"] = api_key
        if api_base_url:
            env["OPENAI_API_BASE"] = api_base_url
        env["HERMES_MODEL"] = model_id
        env["HERMES_TEMPERATURE"] = temperature
        env["HERMES_MAX_TOKENS"] = max_tokens

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            # Collect full output then parse (need full text to separate content from metadata)
            stdout_bytes = await process.stdout.read()
            raw_output = stdout_bytes.decode("utf-8")

            await process.wait()

            if process.returncode != 0:
                stderr_bytes = await process.stderr.read()
                error_msg = stderr_bytes.decode("utf-8")
                yield {"type": "error", "message": f"Hermes error: {error_msg}"}
                return

            # Parse output
            content, new_hermes_sid = self._parse_hermes_output(raw_output)

            # Save hermes session id for future --resume calls
            if new_hermes_sid:
                db.set_hermes_session_id(session_id, new_hermes_sid)

            # Send parsed content
            if content:
                yield {"type": "token", "content": content}

            # Persist assistant response
            assistant_msg_id = str(uuid.uuid4())
            db.add_message(assistant_msg_id, session_id, "assistant", content)

        except FileNotFoundError:
            yield {
                "type": "error",
                "message": f"Hermes binary not found at: {self._hermes_bin}. "
                "Set HERMES_VENV_DIR env variable to your hermes-agent venv path.",
            }
        except Exception as e:
            yield {"type": "error", "message": f"Unexpected error: {str(e)}"}
