import secrets
from typing import Optional
from fastapi import Request, HTTPException

_auth_token: Optional[str] = None
_auth_enabled: bool = False  # Disabled by default for Electron desktop app


def init_auth_token() -> str:
    """Initialize and return a new authentication token."""
    global _auth_token
    _auth_token = secrets.token_urlsafe(32)
    return _auth_token


def enable_auth(enabled: bool = True):
    """Enable or disable authentication."""
    global _auth_enabled
    _auth_enabled = enabled


def get_auth_token() -> Optional[str]:
    """Get the current authentication token."""
    return _auth_token


def verify_token(token: str) -> bool:
    """Verify if the provided token matches the auth token."""
    if _auth_token is None:
        return False
    return secrets.compare_digest(token, _auth_token)


async def auth_middleware(request: Request, call_next):
    """Middleware to verify authentication token (optional for Electron app)."""
    # Skip auth if disabled (default for Electron desktop app)
    if not _auth_enabled:
        return await call_next(request)
    
    # Whitelist: health check, root, auth token endpoint, and WebSocket
    if request.url.path in ["/health", "/", "/api/auth/token"]:
        return await call_next(request)
    
    if request.url.path.startswith("/ws"):
        return await call_next(request)
    
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Missing authentication token")
    
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authentication format")
    
    token = auth_header.replace("Bearer ", "")
    if not verify_token(token):
        raise HTTPException(status_code=403, detail="Invalid authentication token")
    
    return await call_next(request)
