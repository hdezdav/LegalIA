"""Usage service for querying token quota and pipeline telemetry."""

from __future__ import annotations

import datetime
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models.usage import UsageLog

logger = get_logger(__name__)

# Default monthly allocation (15M tokens)
DEFAULT_MONTHLY_TOKEN_BUDGET = 15_000_000
DEFAULT_RPM_LIMIT = 120


async def get_token_quota(
    session: Session | None = None,
    user_id: Any | None = None,
) -> dict[str, Any]:
    """Fetch live token consumption and quota metrics from database telemetry.
    
    Aggregates token consumption (prompt, completion, and verifier passes)
    for the active billing/calendar month.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    start_of_month = datetime.datetime(now.year, now.month, 1, tzinfo=datetime.timezone.utc)
    
    # Calculate days remaining in the current month
    if now.month == 12:
        next_month = datetime.datetime(now.year + 1, 1, 1, tzinfo=datetime.timezone.utc)
    else:
        next_month = datetime.datetime(now.year, now.month + 1, 1, tzinfo=datetime.timezone.utc)
    days_remaining = max(1, (next_month - now).days)

    total_tokens = DEFAULT_MONTHLY_TOKEN_BUDGET
    used_tokens = 0
    prompt_tokens = 0
    completion_tokens = 0
    request_count = 0

    if session is not None:
        try:
            # Query sum of tokens for current month
            query = select(
                func.coalesce(func.sum(UsageLog.input_tokens), 0),
                func.coalesce(func.sum(UsageLog.output_tokens), 0),
                func.coalesce(func.sum(UsageLog.verifier_input_tokens), 0),
                func.coalesce(func.sum(UsageLog.verifier_output_tokens), 0),
                func.count(UsageLog.id),
            ).where(UsageLog.created_at >= start_of_month)

            if user_id:
                query = query.where(UsageLog.user_id == user_id)

            row = session.execute(query).first()
            if row:
                inp, outp, v_inp, v_outp, count = row
                prompt_tokens = int(inp + v_inp)
                completion_tokens = int(outp + v_outp)
                used_tokens = prompt_tokens + completion_tokens
                request_count = int(count)
        except Exception as exc:
            logger.warning("Failed to aggregate usage logs from database", extra={"error": str(exc)})

    remaining_tokens = max(0, total_tokens - used_tokens)
    remaining_pct = round((remaining_tokens / total_tokens) * 100, 1) if total_tokens > 0 else 0.0

    return {
        "total_tokens": total_tokens,
        "used_tokens": used_tokens,
        "remaining_tokens": remaining_tokens,
        "remaining_percent": float(remaining_pct),
        "total_millions": round(total_tokens / 1_000_000, 2),
        "remaining_millions": round(remaining_tokens / 1_000_000, 2),
        "used_millions": round(used_tokens / 1_000_000, 2),
        "status": "active",
        "days_remaining": days_remaining,
        "rpm_limit": DEFAULT_RPM_LIMIT,
        "requests_remaining": max(0, 1000 - request_count),
        "request_count_month": request_count,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cache_read_tokens": 0,
    }
