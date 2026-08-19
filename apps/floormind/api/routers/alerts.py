"""Alerts API endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.schemas import Alert
from modules.alerts import check_all_alerts

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[Alert])
async def get_alerts(user: dict = Depends(get_current_user)) -> list[Alert]:
    """Return all active smart alerts."""
    raw = check_all_alerts()
    return [
        Alert(
            level=a.get("level", "info"),
            icon=a.get("icon", ""),
            title=a.get("title", ""),
            message=a.get("message", ""),
            category=a.get("category", ""),
        )
        for a in raw
    ]
