"""
My Production Agent — Final Project (Day 12)

Kết hợp tất cả concepts:
  - Config từ environment variables (12-Factor)
  - Structured JSON logging
  - API Key authentication
  - Rate limiting (sliding window, Redis-backed)
  - Cost guard (monthly budget, Redis-backed)
  - Conversation history (stateless — Redis)
  - Health check + readiness probe
  - Graceful shutdown (SIGTERM)
  - Security headers + CORS
"""
import time
import json
import signal
import logging
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

from app.config import settings
from app import storage
from app.auth import verify_api_key
from app.rate_limiter import check_rate_limit
from app.cost_guard import check_budget, record_usage, get_usage
from utils.mock_llm import ask as llm_ask

# ──────────────────────────────────────────────────────────
# Structured JSON logging
# ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0


# ──────────────────────────────────────────────────────────
# Lifespan — startup / graceful shutdown
# ──────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "instance": settings.instance_id,
        "storage": "redis" if storage.USE_REDIS else "in-memory",
    }))
    time.sleep(0.1)  # simulate init (load model, warm cache, ...)
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown_start"}))
    time.sleep(0.1)  # cho request hiện tại hoàn thành
    logger.info(json.dumps({"event": "shutdown_complete"}))


def _handle_sigterm(*_args):
    logger.info(json.dumps({"event": "sigterm_received"}))


signal.signal(signal.SIGTERM, _handle_sigterm)


# ──────────────────────────────────────────────────────────
# App
# ──────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    """Security headers + structured access log."""
    global _request_count
    _request_count += 1
    start = time.time()

    response: Response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    del response.headers["server"]

    logger.info(json.dumps({
        "event": "request",
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "ms": round((time.time() - start) * 1000, 1),
    }))
    return response


# ──────────────────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None  # None = tạo conversation mới


class AskResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    turn: int
    model: str
    served_by: str
    timestamp: str


# ──────────────────────────────────────────────────────────
# Conversation history (stateless — Redis-backed)
# ──────────────────────────────────────────────────────────
def _append_history(session_id: str, role: str, content: str) -> list:
    session = storage.get_json(f"session:{session_id}") or {}
    history = session.get("history", [])
    history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    history = history[-20:]  # giữ tối đa 10 turns
    session["history"] = history
    storage.set_json(f"session:{session_id}", session)
    return history


# ──────────────────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────────────────
@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "instance": settings.instance_id,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "history": "GET /chat/{session_id}/history",
            "usage": "GET /me/usage (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    user_id: str = Depends(verify_api_key),
):
    """
    Gửi câu hỏi tới agent. Yêu cầu header `X-API-Key`.

    Truyền `session_id` để tiếp tục cuộc trò chuyện (multi-turn, stateless).
    """
    # 1. Rate limit
    check_rate_limit(user_id)

    # 2. Budget check
    check_budget(user_id)

    # 3. Lấy/tạo session + history (Redis — bất kỳ instance nào đều đọc được)
    session_id = body.session_id or str(uuid.uuid4())
    _append_history(session_id, "user", body.question)

    # 4. Gọi LLM (mock)
    answer = llm_ask(body.question)
    history = _append_history(session_id, "assistant", answer)

    # 5. Ghi nhận cost
    input_tokens = len(body.question.split()) * 2
    output_tokens = len(answer.split()) * 2
    record_usage(user_id, input_tokens, output_tokens)

    return AskResponse(
        session_id=session_id,
        question=body.question,
        answer=answer,
        turn=len([m for m in history if m["role"] == "user"]),
        model=settings.llm_model if settings.openai_api_key else "mock",
        served_by=settings.instance_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/chat/{session_id}/history", tags=["Agent"])
def get_history(session_id: str, _user_id: str = Depends(verify_api_key)):
    session = storage.get_json(f"session:{session_id}")
    if not session:
        raise HTTPException(404, f"Session {session_id} not found or expired")
    return {
        "session_id": session_id,
        "messages": session.get("history", []),
        "served_by": settings.instance_id,
    }


@app.get("/me/usage", tags=["Agent"])
def my_usage(user_id: str = Depends(verify_api_key)):
    return get_usage(user_id)


# ──────────────────────────────────────────────────────────
# Health / Readiness / Metrics
# ──────────────────────────────────────────────────────────
@app.get("/health", tags=["Operations"])
def health():
    """Liveness probe — platform restart container nếu fail."""
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "instance": settings.instance_id,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "storage": "redis" if storage.USE_REDIS else "in-memory",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    """Readiness probe — 503 nếu chưa init xong hoặc Redis (nếu dùng) down."""
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    if settings.redis_url and not storage.ping():
        raise HTTPException(503, "Redis not available")
    return {"ready": True, "instance": settings.instance_id}


@app.get("/metrics", tags=["Operations"])
def metrics(_user_id: str = Depends(verify_api_key)):
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "instance": settings.instance_id,
        "storage": "redis" if storage.USE_REDIS else "in-memory",
    }


if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
