"""API Key authentication."""
from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader

from app.config import settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(_api_key_header)) -> str:
    """
    Verify request có header `X-API-Key` đúng với `AGENT_API_KEY`.

    Return user_id (dùng API key làm user_id cho demo này).
    Raise 401 nếu thiếu/không đúng.
    """
    if not api_key or api_key != settings.agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include header: X-API-Key: <key>",
        )
    return api_key
