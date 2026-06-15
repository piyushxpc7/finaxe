from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/costs")
async def get_costs() -> Dict[str, Any]:
    """
    Get LLM cost analytics.

    Returns:
        A dictionary with cost breakdown by time period, model, and purpose
    """
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    return {
        "timestamp": now.isoformat(),
        "today": {
            "total_cost_usd": 0.0,
            "total_calls": 0,
            "avg_latency_ms": 0,
        },
        "by_model": [],
        "by_purpose": [],
        "recent_calls": [],
    }
