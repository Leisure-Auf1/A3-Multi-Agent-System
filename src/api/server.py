"""
Phase 4.2.5 — FastAPI Server

Usage:
    uvicorn src.api.server:app --reload --port 8000

Or programmatically:
    from src.api import app
"""

from __future__ import annotations

import sys
import os

# Ensure project root is on path for src/ imports
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import HealthResponse
from src.api.routes import learning_router, runtime_router, auth_router  # Phase 9.1

# Phase 9.4 — Product API v2
from src.api.v2 import (
    chat_router, profile_router, learning_v2_router,
    resources_router, evaluation_router, settings_router,
    users_router, pipeline_router,  # Phase 9.5-B / 10.2
)


def _cors_settings() -> tuple[list[str], bool]:
    """Build a safe CORS policy from an explicit environment allowlist."""
    raw = os.environ.get(
        "A3_CORS_ORIGINS",
        "http://localhost:8501,http://127.0.0.1:8501",
    )
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    allow_credentials = "*" not in origins
    return origins or ["http://localhost:8501"], allow_credentials

app = FastAPI(
    title="A3 Multi-Agent Learning System — API",
    description=(
        "REST API for the A3 multi-agent learning pipeline. "
        "Submit learning goals and receive personalized plans, "
        "resource recommendations, and quality evaluations."
    ),
    version="2.0.0",
)

_cors_origins, _cors_credentials = _cors_settings()

# CORS — explicit local defaults; deployments can set A3_CORS_ORIGINS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──────────────────────────────────

app.include_router(learning_router)
app.include_router(runtime_router)  # Phase 5.0
app.include_router(auth_router)  # Phase 9.1

# Phase 9.4 — Product API v2
app.include_router(chat_router)
app.include_router(profile_router)
app.include_router(learning_v2_router)
app.include_router(resources_router)
app.include_router(evaluation_router)
app.include_router(settings_router)  # Phase 4.0 — User LLM settings
app.include_router(users_router)     # Phase 9.5-B — Multi-User Platform
app.include_router(pipeline_router)  # Phase 10.2 — Unified Pipeline


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok")
