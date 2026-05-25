"""
WeChat command processing for Hermes Desktop.
Integrates with Hermes Gateway for Weixin message handling.
"""
import uuid
import asyncio
import threading
import re
import os
from pathlib import Path
from fastapi import APIRouter, Request
from services import database as db
from services.gateway_sync import gateway_sync

router = APIRouter(prefix="/api/wechat", tags=["wechat"])

# QR login state
qr_login_state = {
    "qrcode_url": None,
    "status": "idle",  # idle, pending, confirmed, expired
    "token": None,
    "account_id": None,
    "user_id": None,
    "polling_restarted": False,
}
qr_login_lock = threading.Lock()


# ── WeChat Connection Management ────────────────────────────────

@router.get("/qr-login")
async def get_wechat_qr_login():
    """Start WeChat QR login."""
    global qr_login_state
    global qr_login_lock
    
    with qr_login_lock:
        if qr_login_state["status"] == "pending":
            return qr_login_state
        
        # Reset state
        qr_login_state = {
            "qrcode_url": None,
            "status": "pending",
            "token": None,
            "account_id": None,
            "user_id": None,
            "polling_restarted": False,
        }
    
    # Run QR login in thread pool
    loop = asyncio.get_event_loop()
    future = loop.run_in_executor(None, _run_qr_login_sync)
    
    # Wait for qrcode_url to be populated (max 15 seconds)
    for i in range(30):
        await asyncio.sleep(0.5)
        with qr_login_lock:
            if qr_login_state["qrcode_url"]:
                print(f"[QR Login API] Got QR code URL: {qr_login_state['qrcode_url']}")
                return qr_login_state
            if qr_login_state["status"] == "confirmed" and not qr_login_state.get("polling_restarted"):
                # QR login success - restart polling service
                try:
                    from services.weixin_polling import weixin_service
                    await weixin_service.stop()
                    await weixin_service.start()
                    qr_login_state["polling_restarted"] = True
                    print(f"[QR Login API] Restarted polling service")
                except Exception as e:
                    print(f"[QR Login API] Failed to restart polling: {e}")
                return qr_login_state
            if qr_login_state["status"] == "error":
                return qr_login_state
    
    # Timeout
    with qr_login_lock:
        if not qr_login_state["qrcode_url"]:
            qr_login_state["status"] = "error"
        
        return qr_login_state


def _run_qr_login_sync():
    """Run QR login in thread (synchronous)."""
    global qr_login_state
    global qr_login_lock
    import sys
    import re
    import subprocess
    
    print("[QR Login Task] Starting...")
    
    try:
        use_wsl = sys.platform == "win32"
        
        # Create QR login script using Hermes Gateway
        qr_script = '''
import asyncio
import sys
import os

sys.path.insert(0, os.path.expanduser("~/.hermes/hermes-agent"))

from gateway.platforms.weixin import qr_login
from pathlib import Path

async def main():
    try:
        result = await qr_login(Path.home() / ".hermes")
        if result:
            print("SUCCESS:", result.get("token"), result.get("account_id"))
        else:
            print("FAILED: timeout or cancelled")
    except Exception as e:
        print("ERROR:", e)

asyncio.run(main())
'''
        
        # Write script to temp file
        script_path = "/tmp/hermes_qr_login.py"
        
        print(f"[QR Login Task] Writing script to {script_path}")
        
        if use_wsl:
            # Write script in WSL
            subprocess.run(
                ["wsl", "-e", "bash", "-c", f"cat > {script_path} << 'EOF'\n{qr_script}\nEOF"],
                capture_output=True
            )
            print(f"[QR Login Task] Script written (WSL)")
            
            # Run script and capture output in real-time
            print(f"[QR Login Task] Starting process...")
            process = subprocess.Popen(
                ["wsl", "-e", "bash", "-c", f"~/.hermes/hermes-agent/venv/bin/python -u {script_path}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
        else:
            with open(script_path, 'w') as f:
                f.write(qr_script)
            
            process = subprocess.Popen(
                ["bash", "-c", f"~/.hermes/hermes-agent/venv/bin/python -u {script_path}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
        
        print(f"[QR Login Task] Process started, reading output...")
        
        # Read output line by line
        for line in iter(process.stdout.readline, ''):
            if not line:
                break
            
            line_str = line.strip()
            print(f"[QR Login] {line_str}")
            
            # Extract QR code URL
            qr_match = re.search(r'https://liteapp\.weixin\.qq\.com/[^\s]+', line_str)
            if qr_match:
                qr_url = qr_match.group(0)
                print(f"[QR Login Task] Found QR URL: {qr_url}")
                with qr_login_lock:
                    qr_login_state["qrcode_url"] = qr_url
                print(f"[QR Login Task] Updated state")
            
            # Check for success
            if "SUCCESS:" in line_str:
                parts = line_str.split("SUCCESS:")[1].strip().split()
                if len(parts) >= 2:
                    token = parts[0]
                    account_id = parts[1]
                    
                    try:
                        # Update .env file with new token
                        env_file = Path.home() / ".hermes" / ".env"
                        if env_file.exists():
                            with open(env_file, "r") as f:
                                env_content = f.read()
                            
                            env_content = re.sub(
                                r'^WEIXIN_TOKEN=.*$',
                                f'WEIXIN_TOKEN={token}',
                                env_content,
                                flags=re.MULTILINE
                            )
                            env_content = re.sub(
                                r'^WEIXIN_ACCOUNT_ID=.*$',
                                f'WEIXIN_ACCOUNT_ID={account_id}',
                                env_content,
                                flags=re.MULTILINE
                            )
                            
                            with open(env_file, "w") as f:
                                f.write(env_content)
                            
                            print(f"[QR Login Task] Updated .env with new token")
                        
                        # Update environment variables for current process
                        os.environ["WEIXIN_TOKEN"] = token
                        os.environ["WEIXIN_ACCOUNT_ID"] = account_id
                        print(f"[QR Login Task] Updated environment variables")
                        
                        # Delete all existing connections first (singleton mode)
                        existing = db.get_wechat_connections()
                        for conn in existing:
                            db.delete_wechat_connection(conn["user_id"])
                            print(f"[QR Login Task] Deleted old connection: {conn['user_id']}")
                        
                        # Save new connection
                        db.save_wechat_connection(
                            user_id=account_id,
                            nickname="微信用户",
                            avatar=""
                        )
                        print(f"[QR Login Task] Saved new connection: {account_id}")
                        
                        # Set status to confirmed AFTER all updates are done
                        with qr_login_lock:
                            qr_login_state["status"] = "confirmed"
                            qr_login_state["token"] = token
                            qr_login_state["account_id"] = account_id
                        
                    except Exception as e:
                        print(f"[QR Login Task] Failed to save connection: {e}")
                        with qr_login_lock:
                            qr_login_state["status"] = "error"
                break
            
            # Check for failure
            if "FAILED" in line_str or "ERROR" in line_str:
                with qr_login_lock:
                    qr_login_state["status"] = "expired"
                break
        
        process.wait()
        print(f"[QR Login Task] Process finished")
        
    except Exception as e:
        print(f"[QR Login Task] Exception: {e}")
        import traceback
        traceback.print_exc()
        with qr_login_lock:
            qr_login_state["status"] = "error"
            qr_login_state["qrcode_url"] = None


async def _run_qr_login():
    """Run QR login process in background (async wrapper)."""
    _run_qr_login_sync()


@router.get("/qr-status")
async def get_qr_login_status():
    """Check QR login status."""
    global qr_login_state
    
    # If just confirmed, restart polling service
    if qr_login_state["status"] == "confirmed" and qr_login_state.get("token") and not qr_login_state.get("polling_restarted"):
        try:
            # Restart polling service with new token
            from services.weixin_polling import weixin_service
            await weixin_service.stop()
            await weixin_service.start()
            print(f"[QR Status API] Restarted polling service")
            
            # Mark as restarted
            qr_login_state["polling_restarted"] = True
        except Exception as e:
            print(f"[QR Status API] Failed to restart polling: {e}")
    
    return qr_login_state


@router.post("/qr-cancel")
async def cancel_qr_login():
    """Cancel QR login."""
    global qr_login_state
    qr_login_state["status"] = "idle"
    qr_login_state["qrcode_url"] = None
    return {"status": "cancelled"}


@router.get("/connections")
async def get_wechat_connections():
    """Get all connected WeChat accounts."""
    connections = db.get_wechat_connections()
    return {"connections": connections}


@router.post("/connect")
async def wechat_connect(request: Request):
    """WeChat scan authorization success callback (singleton mode - replaces old connection)."""
    data = await request.json()
    user_id = data.get("user_id")
    nickname = data.get("nickname", "微信用户")
    avatar = data.get("avatar", "")
    
    if not user_id:
        return {"error": "user_id required"}
    
    # 单例模式：删除所有旧连接，保存新连接
    existing_connections = db.get_wechat_connections()
    for conn in existing_connections:
        db.delete_wechat_connection(conn["user_id"])
        print(f"[WeChat] Deleted old connection: {conn['user_id']}")
    
    # 保存新连接
    db.save_wechat_connection(user_id, nickname, avatar)
    print(f"[WeChat] New connection saved: {user_id}")
    
    from main import broadcast_to_all
    await broadcast_to_all({
        "type": "wechat_connected",
        "user_id": user_id,
        "nickname": nickname,
        "avatar": avatar
    })
    
    return {"status": "ok", "message": f"微信账号 {nickname} 已连接"}


@router.post("/disconnect")
async def wechat_disconnect(request: Request):
    """Disconnect a WeChat account."""
    data = await request.json()
    user_id = data.get("user_id")
    
    if not user_id:
        return {"error": "user_id required"}
    
    db.disconnect_wechat(user_id)
    
    from main import broadcast_to_all
    await broadcast_to_all({
        "type": "wechat_disconnected",
        "user_id": user_id
    })
    
    return {"status": "ok"}


# ── WeChat Message Callback (for manual webhook) ───────────────────

@router.post("/callback")
async def wechat_message_callback(request: Request):
    """
    Manual webhook callback (optional).
    Direct iLink integration is preferred (automatic polling).
    """
    data = await request.json()
    print(f"[WeChat Callback] Received: {data}")
    
    user_id = data.get("user_id")
    content = data.get("content", "").strip()
    msg_type = data.get("msg_type", "text")
    
    if not user_id or not content:
        return {"error": "user_id and content required"}
    
    result = await process_wechat_command(user_id, content)
    
    from main import broadcast_to_all
    await broadcast_to_all({
        "type": "wechat_message",
        "user_id": user_id,
        "data": result
    })
    
    return {"reply": result.get("reply", "处理完成")}


# ── Session Sync (Disabled - direct integration) ───────────────────
# Sessions are managed by desktop client, shared with WeChat via iLink API


# ── Command Processing ──────────────────────────────────────────

async def process_wechat_command(user_id: str, content: str):
    """Process WeChat command and return result."""
    from main import broadcast_to_all, enqueue_message_global, session_locks
    
    # Extract command prefix (支持 / 或 无前缀)
    is_command = content.startswith("/")
    command_content = content[1:] if is_command else content
    
    # Check if it's a known command
    known_commands = ["会话列表", "新会话", "切换会话", "发送", "状态", "帮助", "help", "?"]
    
    if not is_command and command_content.split()[0] not in known_commands:
        # Regular message - send to current session
        current_session_id = db.get_wechat_current_session(user_id)
        
        if current_session_id:
            session = next((s for s in db.list_sessions() if s["id"] == current_session_id), None)
            
            if not session:
                return {"reply": "❌ 当前会话不存在，请使用 /切换会话 重新选择"}
            
            session_id = current_session_id
            
            # Check if session is locked
            if session_id in session_locks and session_locks[session_id].locked():
                return {"reply": f"⚠️ 会话正在处理中，消息已排队..."}
            
            user_msg_id = str(uuid.uuid4())
            db.add_message(user_msg_id, session_id, "user", content, source="wechat")
            await enqueue_message_global(session_id, content, user_msg_id, source="wechat")
            
            return {
                "reply": f"✅ 已发送到 {session['title'][:20]}\n\n正在生成回复...",
                "command": "chat",
                "session_id": session_id
            }
        
        # No current session
        return {"reply": "💡 请先使用 /切换会话 选择会话，或输入 /帮助 查看命令"}
    
    # Process command (remove / prefix if present)
    content = command_content
    
    if content == "会话列表":
        sessions = db.list_sessions()
        reply = format_session_list(sessions, session_locks)
        return {
            "reply": reply,
            "command": "session_list",
            "sessions": sessions
        }
    
    elif content == "新会话":
        session_id = str(uuid.uuid4())
        db.create_session(session_id, "新会话")
        
        await broadcast_to_all({
            "type": "session_created",
            "session": {
                "id": session_id,
                "title": "新会话",
                "createdAt": int(__import__("time").time() * 1000)
            }
        })
        
        return {
            "reply": f"✅ 已创建新会话\nID: {session_id[:8]}...\n\n💡 使用以下命令发送消息:\n发送 {session_id[:8]} 你的消息内容",
            "command": "new_session",
            "session_id": session_id
        }
    
    elif content.startswith("切换会话"):
        parts = content.split(" ", 1)
        if len(parts) > 1:
            partial_id = parts[1].strip()
            
            sessions = db.list_sessions()
            matching = [s for s in sessions if s["id"].startswith(partial_id)]
            
            if not matching:
                return {"reply": f"❌ 未找到以 {partial_id} 开头的会话"}
            
            if len(matching) > 1:
                reply = f"❌ 找到多个匹配的会话:\n"
                for s in matching[:5]:
                    reply += f"• {s['id'][:8]}... - {s['title'][:20]}\n"
                return {"reply": reply}
            
            session = matching[0]
            session_id = session["id"]
            messages = db.get_session_messages(session_id)
            
            # Save current session
            db.set_wechat_current_session(user_id, session_id)
            
            # Check if session is currently active
            is_active = session_id in session_locks and session_locks[session_id].locked()
            
            reply = f"✅ 已切换到: {session['title']}\n"
            reply += f"历史消息: {len(messages)} 条\n"
            if is_active:
                reply += "⚠️ 会话正在处理中...\n"
            reply += "\n"
            reply += "💡 直接发送消息即可，无需再指定会话ID\n\n"
            
            if messages:
                reply += "最近消息:\n"
                for msg in messages[-3:]:
                    role = "👤" if msg["role"] == "user" else "🤖"
                    reply += f"{role} {msg['content'][:30]}...\n"
            
            return {
                "reply": reply,
                "command": "switch_session",
                "session_id": session_id,
                "messages": messages,
                "is_active": is_active
            }
        
        return {"reply": "❌ 格式错误\n\n示例: 切换会话 abc12345"}
    
    elif content.startswith("发送"):
        parts = content.split(" ", 2)
        if len(parts) >= 3:
            partial_id = parts[1].strip()
            message_content = parts[2].strip()
            
            sessions = db.list_sessions()
            matching = [s for s in sessions if s["id"].startswith(partial_id)]
            
            if not matching:
                return {"reply": f"❌ 未找到以 {partial_id} 开头的会话"}
            
            session = matching[0]
            session_id = session["id"]
            
            # Check if session is locked
            if session_id in session_locks and session_locks[session_id].locked():
                return {
                    "reply": f"⚠️ 会话 {session['title'][:20]} 正在处理中\n\n消息已加入队列，请稍候..."
                }
            
            user_msg_id = str(uuid.uuid4())
            
            # Save user message immediately
            db.add_message(user_msg_id, session_id, "user", message_content, source="wechat")
            
            # Enqueue to unified message queue (shared with desktop)
            await enqueue_message_global(session_id, message_content, user_msg_id, source="wechat")
            
            return {
                "reply": f"✅ 消息已发送到会话 {session['title'][:20]}\n\n正在生成回复...",
                "command": "chat",
                "session_id": session_id
            }
        
        return {"reply": "❌ 格式错误\n\n示例: 发送 abc12345 你好"}
    
    elif content == "状态":
        # Show session status
        sessions = db.list_sessions()
        active_sessions = [sid for sid in session_locks if session_locks[sid].locked()]
        
        reply = "📊 系统状态:\n\n"
        reply += f"总会话数: {len(sessions)}\n"
        reply += f"活跃会话: {len(active_sessions)}\n\n"
        
        if active_sessions:
            reply += "正在处理的会话:\n"
            for sid in active_sessions[:5]:
                session = next((s for s in sessions if s['id'] == sid), None)
                if session:
                    reply += f"• {session['title'][:20]}\n"
        
        return {"reply": reply}
    
    elif content in ["帮助", "help", "?"]:
        return {
            "reply": """📱 Hermes 微信助手

会话与桌面客户端实时同步，共享同一会话空间。

📋 会话管理:
• 会话列表 - 查看所有会话
• 新会话 - 创建新会话
• 切换会话 [ID] - 切换会话

💬 消息发送:
• [消息内容] - 发送到当前会话
• 发送 [ID] [内容] - 发送到指定会话

ℹ️ 其他:
• 状态 - 查看系统状态
• 帮助 - 查看此帮助

💡 提示:
• 命令可省略 / 前缀
• 会话ID只需输入前8位
• 桌面端实时同步显示"""
        }
    
    # Unknown command
    return {"reply": f"❓ 未知命令: /{content}\n\n输入 /帮助 查看可用命令"}


def format_session_list(sessions: list, session_locks: dict) -> str:
    """Format session list for WeChat display."""
    if not sessions:
        return "📭 暂无会话\n\n💡 输入 '新会话' 创建一个新会话"
    
    lines = ["📋 会话列表:\n"]
    for i, s in enumerate(sessions[:10], 1):
        is_active = s['id'] in session_locks and session_locks[s['id']].locked()
        status = " ⏳" if is_active else ""
        lines.append(f"{i}. {s['title'][:20]}{status}")
        lines.append(f"   ID: {s['id'][:8]}...\n")
    
    if len(sessions) > 10:
        lines.append(f"\n... 还有 {len(sessions) - 10} 个会话")
    
    lines.append("\n💡 使用 '切换会话 [ID]' 切换")
    return "\n".join(lines)


@router.get("/gateway/status")
async def get_gateway_status():
    """Get Hermes Gateway status."""
    status = gateway_sync.get_weixin_status()
    account = gateway_sync.get_weixin_account()
    
    return {
        "gateway_running": status.get("gateway_running", False),
        "weixin_connected": status.get("connected", False),
        "error_code": status.get("error_code"),
        "error_message": status.get("error_message"),
        "account": account
    }


@router.get("/gateway/sessions")
async def get_gateway_sessions(limit: int = 50):
    """Get Weixin sessions from Gateway."""
    sessions = gateway_sync.get_sessions(source="weixin", limit=limit)
    return {"sessions": sessions}


@router.get("/gateway/sessions/{session_id}/messages")
async def get_gateway_session_messages(session_id: str, limit: int = 100):
    """Get messages for a Gateway session."""
    messages = gateway_sync.get_messages(session_id, limit=limit)
    return {"messages": messages}


@router.post("/gateway/event")
async def gateway_event_callback(request: Request):
    """Receive Gateway events from hook."""
    data = await request.json()
    event_type = data.get("event_type")
    context = data.get("context", {})
    
    print(f"[Gateway Event] {event_type}: {context}")
    
    from main import broadcast_to_all
    await broadcast_to_all({
        "type": "gateway_event",
        "event_type": event_type,
        "data": context
    })
    
    return {"status": "ok"}
