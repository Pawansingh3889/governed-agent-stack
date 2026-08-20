"""FloorMind FastAPI application.

Serves the REST API + SSE streaming endpoints that power the Next.js
frontend and any external integrations.

Run locally:
    uvicorn api.main:app --reload --port 8000

Or via the Makefile:
    make api
"""
from __future__ import annotations

import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path so module imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import APP_NAME, VERSION
from modules.monitoring import init_sentry

init_sentry()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
log = logging.getLogger("floormind.api")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title=f"{APP_NAME} API",
    description="REST API for FloorMind — The AI Brain for Your Factory",
    version=VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow the Next.js dev server and any configured origins
_cors_origins = os.getenv(
    "FLOORMIND_CORS_ORIGINS",
    "http://localhost:3000,http://localhost:8501",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from api.auth import router as auth_router  # noqa: E402
from api.chat import router as chat_router  # noqa: E402
from api.routers.alerts import router as alerts_router  # noqa: E402
from api.routers.audit import router as audit_router  # noqa: E402
from api.routers.compliance import router as compliance_router  # noqa: E402
from api.routers.dashboard import router as dashboard_router  # noqa: E402
from api.routers.documents import router as documents_router  # noqa: E402
from api.routers.waste import router as waste_router  # noqa: E402

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(alerts_router)
app.include_router(compliance_router)
app.include_router(waste_router)
app.include_router(documents_router)
app.include_router(dashboard_router)
app.include_router(audit_router)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    """Health check endpoint for Docker and load balancers."""
    return {"status": "ok", "version": VERSION}


@app.get("/")
async def root() -> dict:
    """Root endpoint — API info."""
    return {
        "name": APP_NAME,
        "version": VERSION,
        "docs": "/docs",
        "health": "/health",
    }
