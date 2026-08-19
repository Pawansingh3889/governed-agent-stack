"""Audit log API endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.schemas import AuditEvent
from modules.audit_log import tail

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/events", response_model=list[AuditEvent])
async def audit_events(
    limit: int = 50,
    user: dict = Depends(get_current_user),
) -> list[AuditEvent]:
    """Return the most recent audit log events."""
    raw = tail(n=limit)
    return [
        AuditEvent(
            event_type=e.get("event_type", "unknown"),
            timestamp=e.get("timestamp"),
            fields={k: v for k, v in e.items() if k not in ("event_type", "timestamp")},
        )
        for e in raw
    ]
