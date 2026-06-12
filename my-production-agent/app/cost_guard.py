"""
Cost Guard — Budget $MONTHLY_BUDGET_USD / tháng / user.

Lưu spending trong Redis (key: budget:<user_id>:<YYYY-MM>) với TTL 32 ngày
nên tự "reset" đầu tháng. Fallback in-memory nếu không có Redis.
"""
import time
from fastapi import HTTPException

from app.config import settings
from app import storage

PRICE_PER_1K_INPUT_TOKENS = 0.00015   # gpt-4o-mini input
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006   # gpt-4o-mini output
MONTH_TTL_SECONDS = 32 * 24 * 3600


def _budget_key(user_id: str) -> str:
    month = time.strftime("%Y-%m")
    return f"budget:{user_id}:{month}"


def check_budget(user_id: str) -> None:
    """Raise HTTPException(402) nếu user đã vượt budget tháng này."""
    spent = storage.get_float(_budget_key(user_id))
    if spent >= settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded",
                "spent_usd": round(spent, 6),
                "budget_usd": settings.monthly_budget_usd,
                "resets_at": "1st of next month (UTC)",
            },
        )


def record_usage(user_id: str, input_tokens: int, output_tokens: int) -> float:
    """Ghi nhận usage sau khi gọi LLM. Return tổng cost tháng này."""
    cost = (input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS \
        + (output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
    return storage.incr_float(_budget_key(user_id), cost, MONTH_TTL_SECONDS)


def get_usage(user_id: str) -> dict:
    spent = storage.get_float(_budget_key(user_id))
    return {
        "user_id": user_id,
        "month": time.strftime("%Y-%m"),
        "spent_usd": round(spent, 6),
        "budget_usd": settings.monthly_budget_usd,
        "remaining_usd": round(max(0.0, settings.monthly_budget_usd - spent), 6),
    }
