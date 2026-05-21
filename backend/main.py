"""
Hermes Desktop - Python Backend Server
Runs in WSL, communicates with Electron frontend via WebSocket
"""
import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import HOST, PORT
from services import database as db
from services.hermes_service import HermesService
from services.model_config import model_config_manager
from services.env_manager import env_manager
from services.memory_manager import memory_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    print("[DB] Database initialized")
    yield


app = FastAPI(title="Hermes Desktop Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

hermes_service = HermesService()


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "hermes-desktop-backend"}


@app.get("/api/config")
async def get_config():
    """Get current model configuration."""
    # Get Hermes default model from config.yaml
    hermes_default = db.get_hermes_default_model()
    
    return {
        "model": db.get_config("model", hermes_default),
        "apiKey": db.get_config("apiKey", ""),
        "apiBaseUrl": db.get_config("apiBaseUrl", ""),
        "temperature": float(db.get_config("temperature", "0.7")),
        "maxTokens": int(db.get_config("maxTokens", "2048")),
    }


@app.post("/api/config")
async def update_config(request: dict):
    """Update model configuration."""
    for key in ["model", "apiKey", "apiBaseUrl", "temperature", "maxTokens"]:
        if key in request:
            db.set_config(key, str(request[key]))
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
    db.set_config("apiBaseUrl", model.get('api_base_url', ''))
    
    # Set as default model in Hermes Agent config
    model_config_manager.set_default_model(model_id)
    
    # Check if API key exists
    has_api_key = env_manager.has_api_key(model_id, model.get('api_key_env'))
    
    return {
        "status": "ok",
        "model": model_id,
        "apiBaseUrl": model.get('api_base_url', ''),
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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("[WS] Client connected")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")

            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            elif msg_type == "load_sessions":
                sessions = db.list_sessions()
                await websocket.send_text(json.dumps({
                    "type": "sessions_loaded",
                    "sessions": sessions,
                }))

            elif msg_type == "load_messages":
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
                session_id = message["session_id"]
                db.delete_session(session_id)
                await websocket.send_text(json.dumps({
                    "type": "session_deleted",
                    "session_id": session_id,
                }))

            elif msg_type == "rename_session":
                session_id = message["session_id"]
                title = message["title"]
                db.update_session_title(session_id, title)
                await websocket.send_text(json.dumps({
                    "type": "session_renamed",
                    "session_id": session_id,
                    "title": title,
                }))

            elif msg_type == "stop_generation":
                session_id = message["session_id"]
                hermes_service.stop_generation(session_id)
                await websocket.send_text(json.dumps({
                    "type": "generation_stopped",
                    "session_id": session_id,
                }))

            elif msg_type == "chat":
                session_id = message.get("session_id", str(uuid.uuid4()))
                content = message["content"]
                user_msg_id = message.get("message_id", str(uuid.uuid4()))

                async for chunk in hermes_service.chat(session_id, content, user_msg_id):
                    chunk["session_id"] = session_id
                    await websocket.send_text(json.dumps(chunk))

                await websocket.send_text(json.dumps({"type": "message_done", "session_id": session_id}))

    except WebSocketDisconnect:
        print("[WS] Client disconnected")
    except Exception as e:
        print(f"[WS] Error: {e}")
        try:
            await websocket.send_text(
                json.dumps({"type": "error", "message": str(e)})
            )
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
