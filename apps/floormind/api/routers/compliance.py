"""Compliance API endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.schemas import AllergenRow, BatchTrace, ComplianceScores, TemperatureReading
from modules.compliance import (
    generate_audit_summary,
    get_allergen_matrix,
    get_compliance_score,
    get_temperature_excursions,
    trace_batch,
)

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


def _df_to_list(df) -> list[dict[str, Any]]:
    if df is None or (hasattr(df, "empty") and df.empty):
        return []
    return df.to_dict(orient="records")


@router.get("/scores")
async def compliance_scores(user: dict = Depends(get_current_user)) -> ComplianceScores:
    """Return compliance scores (Temperature Control, Traceability, Overall)."""
    return ComplianceScores(scores=get_compliance_score())


@router.get("/trace/{batch_code}")
async def trace(batch_code: str, user: dict = Depends(get_current_user)) -> BatchTrace:
    """Trace a batch code through raw materials, production, and orders."""
    result = trace_batch(batch_code)
    return BatchTrace(
        batch_code=batch_code,
        raw_materials=_df_to_list(result.get("raw_materials")),
        production=_df_to_list(result.get("production")),
        orders=_df_to_list(result.get("orders")),
    )


@router.get("/allergens", response_model=list[AllergenRow])
async def allergens(user: dict = Depends(get_current_user)) -> list[AllergenRow]:
    """Return the allergen matrix for all products."""
    df = get_allergen_matrix()
    rows = _df_to_list(df)
    return [AllergenRow(product=r.get("product", ""), allergens=r.get("allergens", "")) for r in rows]


@router.get("/temperature", response_model=list[TemperatureReading])
async def temperature_excursions(
    days: int = 7,
    user: dict = Depends(get_current_user),
) -> list[TemperatureReading]:
    """Return temperature excursions for the last N days."""
    df = get_temperature_excursions(days)
    rows = _df_to_list(df)
    return [
        TemperatureReading(
            location=r.get("location", ""),
            reading_time=str(r.get("reading_time", "")),
            temp_celsius=r.get("temp_celsius", 0.0),
            in_range=r.get("in_range", True),
            recorded_by=r.get("recorded_by", ""),
        )
        for r in rows
    ]


@router.get("/audit")
async def audit_report(
    days: int = 30,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    """Generate a BRC/HACCP audit summary."""
    report = generate_audit_summary(days)
    return {
        "generated_at": report.get("generated_at"),
        "period_days": report.get("period_days"),
        "compliance_scores": report.get("compliance_scores"),
        "temperature_excursions_count": len(report.get("temperature_excursions", [])),
        "products_tracked": len(report.get("production_summary", [])),
    }
