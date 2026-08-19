"""Waste & yield analysis API endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.schemas import WastePrediction, WasteSummary, YieldByProduct
from modules.waste_predictor import (
    get_ai_waste_analysis,
    get_waste_summary,
    get_yield_by_product,
    get_yield_trends,
    predict_waste,
)

router = APIRouter(prefix="/api/waste", tags=["waste"])


def _df_to_list(df) -> list[dict[str, Any]]:
    if df is None or (hasattr(df, "empty") and df.empty):
        return []
    return df.to_dict(orient="records")


@router.get("/summary")
async def waste_summary(
    days: int = 7,
    user: dict = Depends(get_current_user),
) -> list[WasteSummary]:
    """Return waste breakdown by type for the last N days."""
    df = get_waste_summary(days)
    rows = _df_to_list(df)
    return [
        WasteSummary(
            waste_type=r.get("waste_type", ""),
            total_kg=r.get("total_kg", 0.0),
            total_cost=r.get("total_cost", 0.0),
        )
        for r in rows
    ]


@router.get("/yield")
async def yield_by_product(
    days: int = 30,
    user: dict = Depends(get_current_user),
) -> list[YieldByProduct]:
    """Return average yield per product over the last N days."""
    df = get_yield_by_product(days)
    rows = _df_to_list(df)
    return [
        YieldByProduct(
            product=r.get("product", r.get("name", "")),
            avg_yield=r.get("avg_yield", 0.0),
            waste_cost_gbp=r.get("waste_cost_gbp", 0.0),
        )
        for r in rows
    ]


@router.get("/trends")
async def yield_trends(
    days: int = 30,
    product: str | None = None,
    user: dict = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Return yield trend data for charting."""
    df = get_yield_trends(days, product if product else None)
    return _df_to_list(df)


@router.get("/predict", response_model=WastePrediction | None)
async def waste_prediction(
    product: str = "Product A",
    input_kg: float = 500.0,
    user: dict = Depends(get_current_user),
) -> WastePrediction | None:
    """Predict waste for a given product and input quantity."""
    result = predict_waste(product, input_kg)
    if result is None:
        return None
    return WastePrediction(
        product=result.get("product", product),
        input_kg=result.get("input_kg", input_kg),
        expected_output_kg=result.get("expected_output_kg", 0.0),
        expected_waste_kg=result.get("expected_waste_kg", 0.0),
        expected_yield_pct=result.get("expected_yield_pct", 0.0),
    )


@router.get("/analysis")
async def waste_analysis(
    days: int = 7,
    user: dict = Depends(get_current_user),
) -> dict[str, str]:
    """Generate AI-powered waste analysis and recommendations."""
    analysis = get_ai_waste_analysis(days)
    return {"analysis": analysis}
