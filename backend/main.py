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

            elif msg_type == "chat":
                session_id = message.get("session_id", str(uuid.uuid4()))
                content = message["content"]
                user_msg_id = message.get("message_id", str(uuid.uuid4()))

                async for chunk in hermes_service.chat(session_id, content, user_msg_id):
                    await websocket.send_text(json.dumps(chunk))

                await websocket.send_text(json.dumps({"type": "message_done"}))

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
