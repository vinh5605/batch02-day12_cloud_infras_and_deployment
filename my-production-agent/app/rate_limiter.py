"""
Rate limiting — Sliding window counter.

Lưu timestamps trong Redis sorted set (key: ratelimit:<user_id>) nếu có Redis,
nên hoạt động đúng dù nhiều instance dùng chung Redis (stateless).
Fallback in-memory nếu không có Redis.
"""
import time
from fastapi import HTTPException

from app.config import settings
from app import storage

WINDOW_SECONDS = 60


def check_rate_limit(user_id: str) -> dict:
    """
    Kiểm tra user có vượt `RATE_LIMIT_PER_MINUTE` không.
    Raise HTTPException(429) nếu vượt. Trả về thông tin còn lại nếu OK.
    """
    now = time.time()
    key = f"ratelimit:{user_id}"

    # Bỏ các timestamps ngoài window
    storage.zremove_older_than(key, now - WINDOW_SECONDS)

    count = storage.zcount_since(key, now - WINDOW_SECONDS)
    if count >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": settings.rate_limit_per_minute,
                "window_seconds": WINDOW_SECONDS,
            },
            headers={
                "X-RateLimit-Limit": str(settings.rate_limit_per_minute),
                "X-RateLimit-Remaining": "0",
                "Retry-After": str(WINDOW_SECONDS),
            },
        )

    storage.zadd_now(key, member=str(now), score=now, ttl_seconds=WINDOW_SECONDS)

    return {
        "limit": settings.rate_limit_per_minute,
        "remaining": settings.rate_limit_per_minute - count - 1,
    }
