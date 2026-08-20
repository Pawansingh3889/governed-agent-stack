"""Pydantic models for API request/response schemas."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    username: str
    role: str


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    stream: bool = True


class ChatResponse(BaseModel):
    explanation: str
    sql: Optional[str] = None
    data: Optional[list[dict[str, Any]]] = None
    error: bool = False


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardStats(BaseModel):
    production_runs_7d: int = 0
    waste_kg_7d: float = 0.0
    waste_cost_7d: float = 0.0
    pending_orders: int = 0


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------

class Alert(BaseModel):
    level: str
    icon: str
    title: str
    message: str
    category: str


# ---------------------------------------------------------------------------
# Compliance
# ---------------------------------------------------------------------------

class ComplianceScores(BaseModel):
    scores: dict[str, float]


class BatchTrace(BaseModel):
    batch_code: str
    raw_materials: list[dict[str, Any]] = []
    production: list[dict[str, Any]] = []
    orders: list[dict[str, Any]] = []


class AllergenRow(BaseModel):
    product: str
    allergens: str


class TemperatureReading(BaseModel):
    location: str
    reading_time: str
    temp_celsius: float
    in_range: bool
    recorded_by: str


# ---------------------------------------------------------------------------
# Waste
# ---------------------------------------------------------------------------

class WasteSummary(BaseModel):
    waste_type: str
    total_kg: float
    total_cost: float


class YieldByProduct(BaseModel):
    product: str
    avg_yield: float
    waste_cost_gbp: float


class WastePrediction(BaseModel):
    product: str
    input_kg: float
    expected_output_kg: float
    expected_waste_kg: float
    expected_yield_pct: float


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class DocumentUploadResponse(BaseModel):
    filename: str
    chunk_count: int


class DocumentSearchResult(BaseModel):
    text: str
    score: float
    source: str
    category: str
    page: Optional[int] = None


class DocumentCount(BaseModel):
    count: int


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------

class AuditEvent(BaseModel):
    event_type: str
    timestamp: Optional[str] = None
    fields: dict[str, Any] = {}
