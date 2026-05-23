"""
Hermes Agent Service - Bridge between Desktop UI and Hermes Agent SDK
"""
import asyncio
import os
import re
import sys
import uuid
from typing import AsyncGenerator, Optional

from config import HERMES_VENV_DIR, HERMES_AGENT_DIR
from services import database as db
from services.model_config import model_config_manager
from services.env_manager import env_manager

try:
    # Add Hermes Agent site-packages to path
    hermes_site_packages = os.path.join(HERMES_VENV_DIR, "lib", "python3.11", "site-packages")
    if os.path.exists(hermes_site_packages) and hermes_site_packages not in sys.path:
        sys.path.insert(0, hermes_site_packages)
    
    from run_agent import AIAgent
    HERMES_API_AVAILABLE = True
    print("[OK] Hermes Agent API loaded successfully")
except ImportError as e:
    HERMES_API_AVAILABLE = False
    print(f"[WARNING] Hermes Agent API not available: {e}")
    print("[WARNING] Falling back to CLI mode")


class HermesService:
    """Service that communicates with Hermes Agent."""

    def __init__(self):
        self._hermes_bin = os.path.join(HERMES_VENV_DIR, "bin", "hermes")
        self._env = os.environ.copy()
        venv_bin = os.path.join(HERMES_VENV_DIR, "bin")
        self._env["PATH"] = venv_bin + ":" + self._env.get("PATH", "")
        self._env["VIRTUAL_ENV"] = HERMES_VENV_DIR
        self._active_tasks = {}
        self._tasks_lock = asyncio.Lock()

    async def stop_generation(self, session_id: str):
        """Stop active generation for a session."""
        async with self._tasks_lock:
            if session_id in self._active_tasks:
                del self._active_tasks[session_id]
                print(f"[INFO] Generation stopped for session {session_id}")

    async def is_generation_active(self, session_id: str) -> bool:
        """Check if generation is active for a session."""
        async with self._tasks_lock:
            return session_id in self._active_tasks

    def _get_agent(self, model_id: str, api_key: str, api_base_url: str, session_id: str = None) -> Optional['AIAgent']:
        """Create AIAgent instance for a model (no caching to avoid state pollution)."""
        if not HERMES_API_AVAILABLE:
            return None
        
        try:
            # Read DeepSeek thinking/reasoning settings from DB
            request_overrides = {}
            thinking = db.get_config("deepseek_thinking", "false")
            
            # Always set thinking type (enabled or disabled)
            if thinking == "true":
                # Get reasoning effort (low/medium -> high, high/max -> max)
                effort = db.get_config("deepseek_reasoning_effort", "high")
                # Map effort according to official spec
                if effort in ("low", "medium"):
                    reasoning_effort = "high"
                elif effort == "xhigh":
                    reasoning_effort = "max"
                else:
                    reasoning_effort = effort  # high or max
                
                # reasoning_effort is a top-level parameter
                request_overrides["reasoning_effort"] = reasoning_effort
                # thinking goes in extra_body
                request_overrides["extra_body"] = {
                    "thinking": {"type": "enabled"}
                }
            else:
                # Explicitly disable thinking
                request_overrides["extra_body"] = {
                    "thinking": {"type": "disabled"}
                }

            agent = AIAgent(
                model=model_id,
                api_key=api_key,
                base_url=api_base_url,
                session_id=session_id,
                request_overrides=request_overrides if request_overrides else None,
            )
            return agent
        except Exception as e:
            print(f"[ERROR] Failed to create AIAgent: {e}")
            return None

    async def chat(
        self, session_id: str, user_message: str, user_msg_id: str
    ) -> AsyncGenerator[dict, None]:
        """
        Send message to Hermes Agent and stream back the response.
        """
        # Validate message length
        MAX_MESSAGE_LENGTH = 100000  # 100KB
        if len(user_message) > MAX_MESSAGE_LENGTH:
            yield {
                "type": "error",
                "message": f"消息过长，最大支持 {MAX_MESSAGE_LENGTH} 字符"
            }
            return
        
        # Mark as active
        async with self._tasks_lock:
            self._active_tasks[session_id] = True
        
        try:
            # Persist user message
            db.add_message(user_msg_id, session_id, "user", user_message)

            # Update session title from first user message (optimized query)
            user_msg_count = db.get_user_message_count(session_id)
            if user_msg_count == 1:
                title = user_message[:30] or "新对话"
                db.update_session_title(session_id, title)
                yield {"type": "session_title", "session_id": session_id, "title": title}

            # Get model configuration
            configured_model_id = db.get_config("model", db.get_hermes_default_model())
            model = model_config_manager.get_model_config(configured_model_id)
            
            model_id = model.get('id', 'deepseek-v4-flash') if model else 'deepseek-v4-flash'
            api_key_env = model.get('api_key_env') if model else None
            
            api_key = env_manager.get_api_key(model_id, api_key_env)
            api_base_url = db.get_config("apiBaseUrl", model.get('api_base_url', '') if model else '')

            # Try using Python API first
            if HERMES_API_AVAILABLE and api_key:
                async for chunk in self._chat_via_api(session_id, user_message, model_id, api_key, api_base_url):
                    # Check if stopped
                    async with self._tasks_lock:
                        if session_id not in self._active_tasks:
                            break
                    yield chunk
            else:
                # Fallback to CLI
                async for chunk in self._chat_via_cli(session_id, user_message, model_id, api_key, api_base_url):
                    # Check if stopped
                    async with self._tasks_lock:
                        if session_id not in self._active_tasks:
                            break
                    yield chunk
        finally:
            # Remove from active tasks
            async with self._tasks_lock:
                if session_id in self._active_tasks:
                    del self._active_tasks[session_id]

    async def _chat_via_api(
        self, session_id: str, user_message: str, model_id: str, api_key: str, api_base_url: str
    ) -> AsyncGenerator[dict, None]:
        """Chat using Hermes Agent Python API (true streaming)."""
        agent = self._get_agent(model_id, api_key, api_base_url, session_id)
        if not agent:
            yield {"type": "error", "message": "Failed to initialize Hermes Agent"}
            return

        # Get conversation history
        messages = db.get_session_messages(session_id)
        history = []
        # Handle empty messages array safely
        if messages and len(messages) > 1:
            for msg in messages[:-1]:  # Exclude current user message
                if msg["role"] in ("user", "assistant"):
                    history.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

        # Use asyncio.Queue for real streaming
        queue = asyncio.Queue()
        content_parts = []
        done_event = asyncio.Event()
        
        # Get event loop in main thread
        loop = asyncio.get_event_loop()
        
        def stream_callback(delta: str):
            """Synchronous callback - puts delta into queue."""
            content_parts.append(delta)
            try:
                loop.call_soon_threadsafe(queue.put_nowait, delta)
            except Exception as e:
                print(f"[WARN] Failed to queue delta: {e}")
        
        async def run_agent():
            """Run agent in thread pool."""
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda: agent.run_conversation(
                        user_message=user_message,
                        conversation_history=history if history else None,
                        stream_callback=stream_callback,
                    )
                )
            except Exception as e:
                await queue.put(f"__ERROR__:{str(e)}")
            finally:
                done_event.set()
        
        # Start agent in background
        asyncio.create_task(run_agent())
        
        # Stream deltas from queue
        full_content = ""
        timeout_seconds = 300  # 5 minutes timeout
        start_time = asyncio.get_event_loop().time()
        
        try:
            while not done_event.is_set() or not queue.empty():
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout_seconds:
                    # Stop background task
                    done_event.set()
                    # Persist partial content on timeout
                    if full_content:
                        assistant_msg_id = str(uuid.uuid4())
                        db.add_message(assistant_msg_id, session_id, "assistant", full_content + "\n\n[超时中断]")
                    yield {"type": "error", "message": f"Timeout after {timeout_seconds} seconds"}
                    return
                
                try:
                    delta = await asyncio.wait_for(queue.get(), timeout=0.1)
                    if delta.startswith("__ERROR__:"):
                        # Persist partial content on error
                        if full_content:
                            assistant_msg_id = str(uuid.uuid4())
                            db.add_message(assistant_msg_id, session_id, "assistant", full_content + "\n\n[生成中断]")
                        yield {"type": "error", "message": delta[9:]}
                        return
                    full_content += delta
                    yield {"type": "token", "content": delta}
                except asyncio.TimeoutError:
                    continue
        except Exception as e:
            # Persist partial content on exception
            if full_content:
                assistant_msg_id = str(uuid.uuid4())
                db.add_message(assistant_msg_id, session_id, "assistant", full_content + "\n\n[异常中断]")
            yield {"type": "error", "message": str(e)}
            return
        
        # Persist assistant response
        if full_content:
            assistant_msg_id = str(uuid.uuid4())
            db.add_message(assistant_msg_id, session_id, "assistant", full_content)

    async def _chat_via_cli(
        self, session_id: str, user_message: str, model_id: str, api_key: str, api_base_url: str
    ) -> AsyncGenerator[dict, None]:
        """Chat using Hermes CLI (fallback, line streaming)."""
        hermes_sid = db.get_hermes_session_id(session_id)
        
        temperature = db.get_config("temperature", "0.7")
        max_tokens = db.get_config("maxTokens", "2048")

        if hermes_sid:
            cmd = [self._hermes_bin, "--resume", hermes_sid, "chat", "-q", user_message]
        else:
            cmd = [self._hermes_bin, "chat", "-q", user_message]

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

            content_lines = []
            hermes_session_id = None
            in_content = False
            
            # Timeout wrapper
            timeout_seconds = 300  # 5 minutes
            start_time = asyncio.get_event_loop().time()
            
            async def read_line(stream):
                line = await stream.readline()
                return line.decode('utf-8') if line else None
            
            while True:
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout_seconds:
                    # Clean up process properly
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        process.kill()
                        await process.wait()
                    # Persist partial content on timeout
                    if content_lines:
                        full_content = "".join(content_lines).strip()
                        if full_content:
                            assistant_msg_id = str(uuid.uuid4())
                            db.add_message(assistant_msg_id, session_id, "assistant", full_content + "\n\n[超时中断]")
                    yield {"type": "error", "message": f"Timeout after {timeout_seconds} seconds"}
                    return
                
                line = await read_line(process.stdout)
                if line is None:
                    break
                
                stripped = line.strip()
                
                resume_match = re.search(r"hermes\s+--resume\s+(\S+)", line)
                if resume_match:
                    hermes_session_id = resume_match.group(1)
                    break
                
                if stripped.startswith("Resume this session with"):
                    break
                
                if not in_content:
                    if stripped.startswith("Query:"):
                        continue
                    if stripped in ("Initializing agent...", ""):
                        continue
                    if stripped.startswith("↻") or stripped.startswith("Resumed session"):
                        continue
                    if "Hermes" in line and ("─" in line or "━" in line or "✦" in line):
                        in_content = True
                        continue
                    if stripped and all(c in "─━═—─" for c in stripped):
                        continue
                    if stripped:
                        in_content = True
                        content_lines.append(line)
                        yield {"type": "token", "content": line}
                    continue
                
                if stripped and len(stripped) > 5 and all(c in "─━═—─" for c in stripped):
                    break
                
                content_lines.append(line)
                yield {"type": "token", "content": line}
            
            await process.wait()
            
            if process.returncode != 0:
                stderr_bytes = await process.stderr.read()
                error_msg = stderr_bytes.decode("utf-8")
                yield {"type": "error", "message": f"Hermes error: {error_msg}"}
                return

            if hermes_session_id:
                db.set_hermes_session_id(session_id, hermes_session_id)

            full_content = "".join(content_lines).strip()
            assistant_msg_id = str(uuid.uuid4())
            db.add_message(assistant_msg_id, session_id, "assistant", full_content)

        except FileNotFoundError:
            yield {
                "type": "error",
                "message": "Hermes binary not found. Please check HERMES_VENV_DIR environment variable.",
            }
        except Exception as e:
            yield {"type": "error", "message": f"Unexpected error: {str(e)}"}
