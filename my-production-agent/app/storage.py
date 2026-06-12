"""
Shared storage — Redis nếu có (stateless, scale-ready), fallback in-memory
nếu không có Redis (chỉ dùng cho dev/test, KHÔNG scale được nhiều instance).

Dùng chung cho: conversation history, rate limiter, cost guard.
"""
import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)

try:
    import redis as _redis_lib
    _redis = _redis_lib.from_url(settings.redis_url or "redis://localhost:6379/0", decode_responses=True)
    _redis.ping()
    USE_REDIS = True
    logger.info("Connected to Redis — stateless mode")
except Exception:
    USE_REDIS = False
    _redis = None
    _memory: dict = {}
    logger.warning("Redis not available — using in-memory store (not scalable!)")


def get_json(key: str) -> dict | None:
    if USE_REDIS:
        raw = _redis.get(key)
        return json.loads(raw) if raw else None
    return _memory.get(key)


def set_json(key: str, value: dict, ttl_seconds: int = 3600) -> None:
    if USE_REDIS:
        _redis.setex(key, ttl_seconds, json.dumps(value))
    else:
        _memory[key] = value


def incr_float(key: str, amount: float, ttl_seconds: int) -> float:
    """Tăng giá trị float của key (tạo mới nếu chưa có) và set TTL."""
    if USE_REDIS:
        new_value = _redis.incrbyfloat(key, amount)
        _redis.expire(key, ttl_seconds)
        return float(new_value)
    current = _memory.get(key, 0.0) + amount
    _memory[key] = current
    return current


def get_float(key: str) -> float:
    if USE_REDIS:
        raw = _redis.get(key)
        return float(raw) if raw else 0.0
    return float(_memory.get(key, 0.0))


def zadd_now(key: str, member: str, score: float, ttl_seconds: int) -> None:
    """Sliding-window helper: thêm timestamp vào sorted set."""
    if USE_REDIS:
        _redis.zadd(key, {member: score})
        _redis.expire(key, ttl_seconds)
    else:
        window = _memory.setdefault(key, [])
        window.append(score)


def zcount_since(key: str, min_score: float) -> int:
    if USE_REDIS:
        return _redis.zcount(key, min_score, "+inf")
    window = _memory.get(key, [])
    return sum(1 for ts in window if ts >= min_score)


def zremove_older_than(key: str, min_score: float) -> None:
    if USE_REDIS:
        _redis.zremrangebyscore(key, "-inf", min_score)
    else:
        window = _memory.get(key, [])
        _memory[key] = [ts for ts in window if ts >= min_score]


def ping() -> bool:
    if not USE_REDIS:
        return False
    try:
        _redis.ping()
        return True
    except Exception:
        return False
