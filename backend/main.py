"""
Hermes Desktop - Python Backend Server
Runs in WSL, communicates with Electron frontend via WebSocket
"""
import json
import uuid
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import HOST, PORT
from services import database as db
from services.hermes_service import HermesService
from services.model_config import model_config_manager
from services.env_manager import env_manager
from services.memory_manager import memory_manager
from services.auth import init_auth_token, get_auth_token, auth_middleware
from services.wechat_gateway import router as wechat_router
from services.gateway_sync import gateway_sync


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    token = init_auth_token()
    print(f"[AUTH] Authentication token initialized: {token[:8]}...")
    print("[DB] Database initialized")
    
    print("[WeChat] 使用 Hermes Gateway 集成模式")
    status = gateway_sync.get_weixin_status()
    if status.get("gateway_running"):
        print(f"[WeChat] Gateway 运行中，微信状态: {status.get('connected', False)}")
    else:
        print("[WeChat] Gateway 未运行，请先启动: hermes gateway run")
    
    yield


app = FastAPI(title="Hermes Desktop Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8765",
        "http://127.0.0.1:8765",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "file://",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.middleware("http")(auth_middleware)

hermes_service = HermesService()

# ── Session Locks and Unified Queue Management ───────────────────
session_locks: dict[str, asyncio.Lock] = {}
active_websockets: list[WebSocket] = []
unified_session_queues: dict[str, list] = {}  # Global unified queue
active_chats_global: dict[str, asyncio.Task] = {}  # Global active chats
waiting_sessions_global: list[str] = []  # Global waiting sessions

async def get_session_lock(session_id: str) -> asyncio.Lock:
    """Get or create a lock for a session."""
    if session_id not in session_locks:
        session_locks[session_id] = asyncio.Lock()
    return session_locks[session_id]

async def broadcast_to_all(message: dict):
    """Broadcast message to all connected WebSocket clients."""
    disconnected = []
    for ws in active_websockets[:]:
        try:
            await ws.send_text(json.dumps(message))
        except:
            disconnected.append(ws)
    
    # Remove disconnected clients
    for ws in disconnected:
        if ws in active_websockets:
            active_websockets.remove(ws)

async def enqueue_message_global(session_id: str, content: str, user_msg_id: str, source: str = "desktop"):
    """
    Unified message enqueue function (used by both WebSocket and WeChat).
    This is the global entry point for all message processing.
    """
    # Get session lock
    lock = await get_session_lock(session_id)
    
    # Initialize queue if needed
    if session_id not in unified_session_queues:
        unified_session_queues[session_id] = []
    
    # Add message to queue
    unified_session_queues[session_id].append((content, user_msg_id, source))
    queue_length = len(unified_session_queues[session_id])
    
    # Notify all clients about queue update
    if queue_length > 1:
        await broadcast_to_all({
            "type": "queue_updated",
            "session_id": session_id,
            "queue_length": queue_length,
            "queue_items": [
                {"user_msg_id": msg_id, "content_preview": c[:50], "source": s}
                for c, msg_id, s in unified_session_queues[session_id]
            ]
        })
    
    # Check if session is already active
    if session_id in active_chats_global:
        return  # Already processing
    
    # Check concurrent limit
    MAX_CONCURRENT = 10
    if len(active_chats_global) >= MAX_CONCURRENT:
        if session_id not in waiting_sessions_global:
            waiting_sessions_global.append(session_id)
            await broadcast_to_all({
                "type": "session_waiting",
                "session_id": session_id,
                "reason": f"并发会话数已达上限 ({MAX_CONCURRENT})，等待中..."
            })
        return
    
    # Start processing
    task = asyncio.create_task(process_session_queue_global(session_id))
    active_chats_global[session_id] = task

async def process_session_queue_global(session_id: str):
    """Process messages in session queue sequentially (global version)."""
    if session_id not in unified_session_queues:
        return
    
    queue = unified_session_queues[session_id]
    lock = await get_session_lock(session_id)
    
    while queue:
        # Get next message
        content, user_msg_id, source = queue.pop(0)
        
        # Acquire lock
        async with lock:
            try:
                # Notify user message
                await broadcast_to_all({
                    "type": "user_message",
                    "session_id": session_id,
                    "message_id": user_msg_id,
                    "content": content,
                    "source": source
                })
                
                # Notify queue status
                remaining = len(queue)
                if remaining > 0:
                    await broadcast_to_all({
                        "type": "queue_updated",
                        "session_id": session_id,
                        "queue_length": remaining,
                        "queue_items": [
                            {"user_msg_id": msg_id, "content_preview": c[:50], "source": s}
                            for c, msg_id, s in queue
                        ]
                    })
                
                # Process with Hermes
                async for chunk in hermes_service.chat(session_id, content, user_msg_id):
                    chunk["session_id"] = session_id
                    chunk["source"] = source
                    await broadcast_to_all(chunk)
                
                await broadcast_to_all({
                    "type": "message_done",
                    "session_id": session_id,
                    "message_id": user_msg_id
                })
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                await broadcast_to_all({
                    "type": "error",
                    "session_id": session_id,
                    "message": str(e)
                })
    
    # Cleanup
    if session_id in active_chats_global:
        del active_chats_global[session_id]
    
    await broadcast_to_all({
        "type": "queue_updated",
        "session_id": session_id,
        "queue_length": 0,
        "queue_items": []
    })
    
    # Start next waiting session
    if waiting_sessions_global:
        next_session_id = waiting_sessions_global.pop(0)
        if next_session_id in unified_session_queues and unified_session_queues[next_session_id]:
            task = asyncio.create_task(process_session_queue_global(next_session_id))
            active_chats_global[next_session_id] = task

# ── Register WeChat Router ───────────────────────────────────────
app.include_router(wechat_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "hermes-desktop-backend"}


# ── Auth API ────────────────────────────────────────────────────

@app.get("/api/auth/token")
async def get_auth_token_endpoint():
    """Get authentication token for current session."""
    token = get_auth_token()
    if not token:
        return {"error": "Token not initialized"}
    return {"token": token}


@app.get("/api/config")
async def get_config():
    """Get current model configuration."""
    # Get Hermes default model from config.yaml
    hermes_default = db.get_hermes_default_model()
    hermes_provider = db.get_hermes_session_id(db.get_config("model", hermes_default)) or "deepseek"
    
    return {
        "model": db.get_config("model", hermes_default),
        "provider": db.get_config("provider", hermes_provider),
        "temperature": float(db.get_config("temperature", "0.7")),
        "maxTokens": int(db.get_config("maxTokens", "2048")),
    }


@app.post("/api/config")
async def update_config(request: dict):
    """Update model configuration."""
    for key in ["model", "provider", "temperature", "maxTokens"]:
        if key in request:
            db.set_config(key, str(request[key]))
    return {"status": "ok"}


# ── DeepSeek Settings APIs ────────────────────────────────────

@app.get("/api/deepseek/settings")
async def get_deepseek_settings():
    """Get DeepSeek thinking/reasoning settings."""
    return {
        "thinking": db.get_config("deepseek_thinking", "false") == "true",
        "reasoningEffort": db.get_config("deepseek_reasoning_effort", "high"),
    }


@app.post("/api/deepseek/settings")
async def update_deepseek_settings(request: dict):
    """Update DeepSeek thinking/reasoning settings."""
    if "thinking" in request:
        db.set_config("deepseek_thinking", str(request["thinking"]).lower())
    if "reasoningEffort" in request:
        db.set_config("deepseek_reasoning_effort", str(request["reasoningEffort"]))
    return {"status": "ok"}


# ── Model Management APIs ─────────────────────────────────────

@app.get("/api/models")
async def get_models():
    """Get all available models from config.yaml"""
    models = model_config_manager.get_available_models()
    
    # Check if each model has API key configured
    for model in models:
        model['configured'] = env_manager.has_api_key(
            model['id'], 
            model.get('api_key_env')
        )
    
    return {"models": models}


@app.get("/api/models/{model_id}")
async def get_model(model_id: str):
    """Get specific model configuration"""
    model = model_config_manager.get_model_config(model_id)
    
    if not model:
        return {"error": "Model not found"}
    
    # Get API key (masked)
    api_key = env_manager.get_api_key(model_id, model.get('api_key_env'))
    model['apiKey'] = env_manager.mask_api_key(api_key) if api_key else ""
    model['hasApiKey'] = bool(api_key)
    model['configured'] = bool(api_key)
    
    return model


@app.post("/api/models/{model_id}")
async def update_model(model_id: str, request: dict):
    """Update or add a model configuration"""
    model_config = {
        'id': model_id,
        'name': request.get('name', model_id),
        'provider': request.get('provider', 'custom'),
        'api_base_url': request.get('apiBaseUrl', ''),
        'api_key_env': request.get('apiKeyEnv', f"{model_id.upper().replace('-', '_')}_API_KEY"),
        'temperature': request.get('temperature', 0.7),
        'max_tokens': request.get('maxTokens', 2048),
    }
    
    # Save to config.yaml
    success = model_config_manager.add_custom_model(model_config)
    
    # Save API key to .env if provided
    if 'apiKey' in request and request['apiKey']:
        env_manager.set_api_key(
            model_id, 
            request['apiKey'],
            model_config['api_key_env']
        )
    
    return {"status": "ok" if success else "error"}


@app.delete("/api/models/{model_id}")
async def delete_model(model_id: str):
    """Delete a custom model completely"""
    # Get model config first to get api_key_env
    model = model_config_manager.get_model_config(model_id)
    api_key_env = model.get('api_key_env') if model else None
    
    # Delete from config.yaml
    success = model_config_manager.delete_custom_model(model_id)
    
    # Delete API Key from .env
    env_manager.delete_api_key(model_id, api_key_env)
    
    # Clear from database if it's current model
    current_model = db.get_config("model", "")
    if current_model == model_id:
        db.set_config("model", "")
        db.set_config("apiBaseUrl", "")
    
    return {"status": "ok" if success else "error"}


@app.post("/api/model/switch")
async def switch_model(request: dict):
    """Switch to a different model and sync URL/API Key"""
    model_id = request.get('model')
    
    if not model_id:
        return {"error": "Model ID required"}
    
    # Get model config
    model = model_config_manager.get_model_config(model_id)
    
    if not model:
        return {"error": "Model not found"}
    
    # Save to database
    db.set_config("model", model_id)
    db.set_config("provider", model.get('provider', 'custom'))
    
    # Set as default model in Hermes Agent config
    model_config_manager.set_default_model(model_id)
    
    # Check if API key exists
    has_api_key = env_manager.has_api_key(model_id, model.get('api_key_env'))
    
    return {
        "status": "ok",
        "model": model_id,
        "provider": model.get('provider', 'custom'),
        "hasApiKey": has_api_key,
        "needsApiKey": not has_api_key
    }


# ── Environment Variables Management ───────────────────────────

@app.get("/api/env")
async def get_env():
    """Get environment variables (masked)"""
    env_vars = env_manager.read_env()
    
    # Mask all values
    masked = {}
    for key, value in env_vars.items():
        masked[key] = env_manager.mask_api_key(value)
    
    return {"env": masked}


@app.post("/api/env")
async def update_env(request: dict):
    """Update environment variables"""
    env_manager.write_env(request)
    return {"status": "ok"}


@app.get("/api/env/check/{model_id}")
async def check_api_key(model_id: str):
    """Check if API key exists for a model"""
    # Get model config to get api_key_env
    model = model_config_manager.get_model_config(model_id)
    api_key_env = model.get('api_key_env') if model else None
    
    has_key = env_manager.has_api_key(model_id, api_key_env)
    api_key = env_manager.get_api_key(model_id, api_key_env)
    
    return {
        "model": model_id,
        "hasApiKey": has_key,
        "apiKey": env_manager.mask_api_key(api_key) if api_key else ""
    }


@app.post("/api/env/set")
async def set_api_key(request: dict):
    """Set API key for a model"""
    model_id = request.get('model')
    api_key = request.get('apiKey')
    api_key_env = request.get('apiKeyEnv')  # Optional
    
    if not model_id or not api_key:
        return {"error": "Model ID and API Key required"}
    
    env_manager.set_api_key(model_id, api_key, api_key_env)
    return {"status": "ok"}


# ── Test Connection ────────────────────────────────────────────

@app.post("/api/test-connection")
async def test_connection(request: dict):
    """Test API connection for a model"""
    import httpx
    
    model_id = request.get('model')
    api_base_url = request.get('apiBaseUrl')
    
    # Get model config for api_key_env
    model = model_config_manager.get_model_config(model_id)
    api_key_env = model.get('api_key_env') if model else None
    
    api_key = env_manager.get_api_key(model_id, api_key_env)
    
    if not api_key:
        return {"status": "error", "message": "API Key not configured"}
    
    if not api_base_url:
        return {"status": "error", "message": "API Base URL not configured"}
    
    try:
        # Test connection with a simple request
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Try to list models or send a minimal request
            test_url = f"{api_base_url.rstrip('/')}/models"
            
            response = await client.get(test_url, headers=headers)
            
            if response.status_code in [200, 401, 403]:
                # 401/403 means endpoint exists but auth issue
                if response.status_code == 200:
                    return {"status": "ok", "message": "Connection successful"}
                else:
                    return {"status": "error", "message": "Authentication failed"}
            else:
                return {"status": "error", "message": f"HTTP {response.status_code}"}
    
    except httpx.TimeoutException:
        return {"status": "error", "message": "Connection timeout"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ── Memory Management APIs ─────────────────────────────────────

@app.get("/api/memories")
async def get_memories():
    """Get list of memory types"""
    return {"memories": memory_manager.get_memory_types()}


# ── SQLite Database Memory APIs (must be before generic memory routes) ──

@app.get("/api/memories/database/entries")
async def get_db_entries(category: str = None, limit: int = 100, offset: int = 0):
    """Get entries from SQLite memory database"""
    entries = memory_manager.get_db_entries(category, limit, offset)
    return {"entries": entries}


@app.get("/api/memories/database/categories")
async def get_db_categories():
    """Get all categories with count"""
    categories = memory_manager.get_db_categories()
    return {"categories": categories}


@app.post("/api/memories/database/entries")
async def add_db_entry(request: dict):
    """Add a new entry to SQLite memory database"""
    content = request.get("content", "")
    category = request.get("category", "general")
    importance = request.get("importance", 1)
    tags = request.get("tags", [])
    
    if not content:
        return {"error": "Content is required"}
    
    entry_id = memory_manager.add_db_entry(content, category, importance, tags)
    if entry_id:
        return {"status": "ok", "id": entry_id}
    return {"error": "Failed to add entry"}


@app.put("/api/memories/database/entries/{entry_id}")
async def update_db_entry(entry_id: int, request: dict):
    """Update an entry in SQLite memory database"""
    success = memory_manager.update_db_entry(
        entry_id,
        content=request.get("content"),
        category=request.get("category"),
        importance=request.get("importance"),
        tags=request.get("tags")
    )
    return {"status": "ok" if success else "error"}


@app.delete("/api/memories/database/entries/{entry_id}")
async def delete_db_entry(entry_id: int):
    """Delete an entry from SQLite memory database"""
    success = memory_manager.delete_db_entry(entry_id)
    return {"status": "ok" if success else "error"}


# ── Generic Memory Routes ────────────────────────────────────────

@app.get("/api/memories/{memory_id}")
async def get_memory(memory_id: str):
    """Get content of a memory"""
    content = memory_manager.get_memory_content(memory_id)
    if content is None:
        return {"error": "Memory not found"}
    return {"id": memory_id, "content": content}


@app.get("/api/memories/{memory_id}/entries")
async def get_memory_entries(memory_id: str):
    """Get memory entries (split by § separator)"""
    entries = memory_manager.get_memory_entries(memory_id)
    return {"id": memory_id, "entries": entries}


@app.delete("/api/memories/{memory_id}/entries/{entry_index}")
async def delete_memory_entry(memory_id: str, entry_index: int):
    """Delete a single memory entry"""
    success = memory_manager.delete_memory_entry(memory_id, entry_index)
    return {"status": "ok" if success else "error"}


@app.put("/api/memories/{memory_id}")
async def update_memory(memory_id: str, request: dict):
    """Update memory content"""
    content = request.get("content", "")
    success = memory_manager.update_memory_content(memory_id, content)
    return {"status": "ok" if success else "error"}


@app.delete("/api/memories/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a memory"""
    success = memory_manager.delete_memory(memory_id)
    return {"status": "ok" if success else "error"}


# ── Main Database Management APIs ───────────────────────────────

@app.get("/api/database/tables")
async def get_database_tables():
    """Get list of tables in main database"""
    try:
        with db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = []
            for (table_name,) in cursor.fetchall():
                # Get row count
                count_cursor = conn.execute(f"SELECT COUNT(*) FROM [{table_name}]")
                count = count_cursor.fetchone()[0]
                # Get column info
                col_cursor = conn.execute(f"PRAGMA table_info([{table_name}])")
                columns = [row[1] for row in col_cursor.fetchall()]
                tables.append({
                    "name": table_name,
                    "count": count,
                    "columns": columns
                })
            return {"tables": tables}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/database/tables/{table_name}")
async def get_table_data(table_name: str, limit: int = 100, offset: int = 0):
    """Get data from a specific table"""
    # Whitelist validation - only allow specific tables
    allowed_tables = {
        'sessions': {'pk': 'id', 'order': 'created_at DESC'},
        'messages': {'pk': 'id', 'order': 'timestamp DESC'}, 
        'config': {'pk': 'key', 'order': 'key ASC'},
        'wechat_connections': {'pk': 'user_id', 'order': 'connected_at DESC'}
    }
    
    if table_name not in allowed_tables:
        return {"error": "Table not allowed"}
    
    # Validate pagination params
    if limit < 1 or limit > 1000:
        limit = 100
    if offset < 0:
        offset = 0
    
    order_by = allowed_tables[table_name]['order']
    
    try:
        with db.get_connection() as conn:
            # Get total count
            count_cursor = conn.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            total = count_cursor.fetchone()[0]
            
            # Get rows with ordering and pagination
            cursor = conn.execute(
                f"SELECT * FROM [{table_name}] ORDER BY {order_by} LIMIT ? OFFSET ?",
                (limit, offset)
            )
            rows = cursor.fetchall()
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            
            # Convert to list of dicts
            data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Convert bytes to string
                    if isinstance(value, bytes):
                        value = value.decode('utf-8', errors='replace')
                    row_dict[col] = value
                data.append(row_dict)
            
            return {
                "table": table_name,
                "columns": columns,
                "rows": data,
                "total": total,
                "limit": limit,
                "offset": offset,
                "primaryKey": allowed_tables[table_name]['pk']
            }
    except Exception as e:
        return {"error": str(e)}


@app.delete("/api/database/tables/{table_name}/{row_id}")
async def delete_table_row(table_name: str, row_id: str):
    """Delete a row from a table"""
    # Whitelist validation with primary key mapping
    allowed_tables = {
        'sessions': 'id',
        'messages': 'id',
        'config': 'key',
        'wechat_connections': 'user_id'
    }
    
    if table_name not in allowed_tables:
        return {"error": "Table not allowed", "status": "error"}
    
    pk_column = allowed_tables[table_name]
    
    try:
        with db.get_connection() as conn:
            conn.execute(
                f"DELETE FROM [{table_name}] WHERE [{pk_column}] = ?",
                (row_id,)
            )
            conn.commit()
            return {"status": "ok"}
    except Exception as e:
        return {"error": str(e), "status": "error"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    print("[WS] Client connected")
    
    # Active chat tasks and message queues per session
    active_chats = {}
    session_queues = {}
    waiting_sessions = []
    MAX_CONCURRENT_SESSIONS = 10

    def validate_message(msg: dict, required_fields: list, max_size: int = 10000) -> bool:
        """Validate message has required fields with correct types and size."""
        # Check message size
        try:
            msg_str = json.dumps(msg)
            if len(msg_str) > max_size:
                return False
        except:
            return False
        
        # Check required fields
        for field in required_fields:
            if field not in msg:
                return False
            # Check field types
            if field in ['session_id', 'content', 'title'] and not isinstance(msg[field], str):
                return False
        
        return True

    async def process_session_queue(session_id: str):
        """Process messages in session queue sequentially."""
        if session_id not in session_queues:
            return
        
        queue = session_queues[session_id]
        lock = await get_session_lock(session_id)
        
        while queue:
            # Get next message from queue
            content, user_msg_id, source = queue.pop(0)
            
            # Acquire lock for this session
            async with lock:
                try:
                    # Notify client to display user message
                    await broadcast_to_all({
                        "type": "user_message",
                        "session_id": session_id,
                        "message_id": user_msg_id,
                        "content": content,
                        "source": source
                    })
                    
                    # Notify client about remaining queue (after removing current message)
                    remaining = len(queue)
                    if remaining > 0:
                        await broadcast_to_all({
                            "type": "queue_updated",
                            "session_id": session_id,
                            "queue_length": remaining,
                            "queue_items": [
                                {"user_msg_id": msg_id, "content_preview": c[:50], "source": s}
                                for c, msg_id, s in queue
                            ]
                        })
                    
                    # Process with Hermes
                    async for chunk in hermes_service.chat(session_id, content, user_msg_id):
                        chunk["session_id"] = session_id
                        chunk["source"] = source
                        await broadcast_to_all(chunk)
                    
                    await broadcast_to_all({
                        "type": "message_done",
                        "session_id": session_id,
                        "message_id": user_msg_id
                    })
                    
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    await broadcast_to_all({
                        "type": "error",
                        "session_id": session_id,
                        "message": str(e)
                    })
        
        # Remove from active chats when queue is empty
        if session_id in active_chats:
            del active_chats[session_id]
        
        # Notify queue is empty
        await broadcast_to_all({
            "type": "queue_updated",
            "session_id": session_id,
            "queue_length": 0,
            "queue_items": []
        })
        
        # Start next waiting session if any
        if waiting_sessions:
            next_session_id = waiting_sessions.pop(0)
            if next_session_id in session_queues and session_queues[next_session_id]:
                task = asyncio.create_task(process_session_queue(next_session_id))
                active_chats[next_session_id] = task

    async def remove_from_queue(session_id: str, user_msg_id: str):
        """Remove a message from session queue."""
        if session_id not in session_queues:
            return
        
        # Find and remove the message
        for i, (content, msg_id, source) in enumerate(session_queues[session_id]):
            if msg_id == user_msg_id:
                session_queues[session_id].pop(i)
                break
        
        # Notify client about updated queue
        queue_length = len(session_queues[session_id])
        await broadcast_to_all({
            "type": "queue_updated",
            "session_id": session_id,
            "queue_length": queue_length,
            "queue_items": [
                {"user_msg_id": msg_id, "content_preview": content[:50], "source": s}
                for content, msg_id, s in session_queues[session_id]
            ]
        })

    async def enqueue_message(session_id: str, content: str, user_msg_id: str, source: str = "desktop"):
        """Add message to session queue and start processing if not already active."""
        try:
            # Get session lock to prevent concurrent access
            lock = await get_session_lock(session_id)
            
            # Initialize queue if needed
            if session_id not in session_queues:
                session_queues[session_id] = []
            
            # Add message to queue with source info
            session_queues[session_id].append((content, user_msg_id, source))
            queue_length = len(session_queues[session_id])
            
            # Notify all clients about queue update
            if queue_length > 1:
                await broadcast_to_all({
                    "type": "queue_updated",
                    "session_id": session_id,
                    "queue_length": queue_length,
                    "queue_items": [
                        {"user_msg_id": msg_id, "content_preview": c[:50], "source": s}
                        for c, msg_id, s in session_queues[session_id]
                    ]
                })
            
            # Check if session is already active
            if session_id in active_chats:
                return  # Already processing, message will be handled in queue
            
            # Check concurrent limit
            if len(active_chats) >= MAX_CONCURRENT_SESSIONS:
                # Add to waiting queue
                if session_id not in waiting_sessions:
                    waiting_sessions.append(session_id)
                    await websocket.send_text(json.dumps({
                        "type": "session_waiting",
                        "session_id": session_id,
                        "reason": f"并发会话数已达上限 ({MAX_CONCURRENT_SESSIONS})，等待中..."
                    }))
                return
            
            # Start processing
            task = asyncio.create_task(process_session_queue(session_id))
            active_chats[session_id] = task
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "session_id": session_id,
                    "message": f"Failed to enqueue message: {str(e)}"
                }))
            except:
                pass

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))
                continue
            
            msg_type = message.get("type")
            if not msg_type or not isinstance(msg_type, str):
                continue

            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            elif msg_type == "load_sessions":
                sessions = db.list_sessions()
                await websocket.send_text(json.dumps({
                    "type": "sessions_loaded",
                    "sessions": sessions,
                }))

            elif msg_type == "load_messages":
                if not validate_message(message, ["session_id"]):
                    continue
                session_id = message["session_id"]
                messages = db.get_session_messages(session_id)
                await websocket.send_text(json.dumps({
                    "type": "messages_loaded",
                    "session_id": session_id,
                    "messages": messages,
                }))

            elif msg_type == "create_session":
                session_id = message.get("session_id", str(uuid.uuid4()))
                title = message.get("title", "新对话")
                session = db.create_session(session_id, title)
                await websocket.send_text(json.dumps({
                    "type": "session_created",
                    "session": session,
                }))

            elif msg_type == "delete_session":
                if not validate_message(message, ["session_id"]):
                    continue
                session_id = message["session_id"]
                db.delete_session(session_id)
                await websocket.send_text(json.dumps({
                    "type": "session_deleted",
                    "session_id": session_id,
                }))

            elif msg_type == "rename_session":
                if not validate_message(message, ["session_id", "title"]):
                    continue
                session_id = message["session_id"]
                title = message["title"]
                db.update_session_title(session_id, title)
                await websocket.send_text(json.dumps({
                    "type": "session_renamed",
                    "session_id": session_id,
                    "title": title,
                }))

            elif msg_type == "stop_generation":
                if not validate_message(message, ["session_id"]):
                    continue
                session_id = message["session_id"]
                await hermes_service.stop_generation(session_id)
                await websocket.send_text(json.dumps({
                    "type": "generation_stopped",
                    "session_id": session_id,
                }))

            elif msg_type == "remove_from_queue":
                if not validate_message(message, ["session_id", "user_msg_id"]):
                    continue
                session_id = message["session_id"]
                user_msg_id = message["user_msg_id"]
                await remove_from_queue(session_id, user_msg_id)

            elif msg_type == "chat":
                if not validate_message(message, ["content"]):
                    continue
                session_id = message.get("session_id", str(uuid.uuid4()))
                content = message["content"]
                user_msg_id = message.get("message_id", str(uuid.uuid4()))

                # Use global unified queue
                await enqueue_message_global(session_id, content, user_msg_id, source="desktop")

    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)
        print("[WS] Client disconnected")
    except Exception as e:
        if websocket in active_websockets:
            active_websockets.remove(websocket)
        print(f"[WS] Error: {e}")
        try:
            await websocket.send_text(
                json.dumps({"type": "error", "message": "An internal error occurred"})
            )
        except Exception:
            pass
    finally:
        # Cancel all active chats
        for task in active_chats.values():
            task.cancel()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
