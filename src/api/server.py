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

app = FastAPI(
    title="A3 Multi-Agent Learning System — API",
    description=(
        "REST API for the A3 multi-agent learning pipeline. "
        "Submit learning goals and receive personalized plans, "
        "resource recommendations, and quality evaluations."
    ),
    version="0.1.0",
)

# CORS — allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ──────────────────────────────────

app.include_router(learning_router)
app.include_router(runtime_router)  # Phase 5.0
app.include_router(auth_router)  # Phase 9.1


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok")
