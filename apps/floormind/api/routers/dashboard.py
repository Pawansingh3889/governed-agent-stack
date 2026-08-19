"""Dashboard statistics API endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.schemas import DashboardStats
from modules.database import scalar
from modules.sql_dialect import days_ago

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(user: dict = Depends(get_current_user)) -> DashboardStats:
    """Return key factory metrics for the dashboard."""
    try:
        runs = scalar(f"SELECT COUNT(*) FROM production WHERE date >= {days_ago(7)}") or 0
        waste_kg = scalar(f"SELECT COALESCE(SUM(waste_kg), 0) FROM production WHERE date >= {days_ago(7)}") or 0
        waste_cost = scalar(
            f"SELECT COALESCE(SUM(p.waste_kg * pr.unit_cost_per_kg), 0) "
            f"FROM production p JOIN products pr ON p.product_id = pr.id "
            f"WHERE p.date >= {days_ago(7)}"
        ) or 0
        pending = scalar("SELECT COUNT(*) FROM orders WHERE status = 'pending'") or 0
    except Exception:
        return DashboardStats()

    return DashboardStats(
        production_runs_7d=int(runs),
        waste_kg_7d=float(waste_kg),
        waste_cost_7d=float(waste_cost),
        pending_orders=int(pending),
    )
