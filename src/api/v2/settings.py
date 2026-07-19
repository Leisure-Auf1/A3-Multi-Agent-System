"""
Phase 4.0 — Settings API (v2)

User LLM configuration endpoints.

Endpoints:
  GET  /api/v2/settings/llm   — Get current LLM configuration
  POST /api/v2/settings/llm   — Save LLM configuration
  POST /api/v2/settings/test  — Test LLM connection
"""

from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.config.llm_config import (
    load_llm_config,
    save_llm_config,
    LLMConfig,
    SUPPORTED_PROVIDERS,
)
from src.core.provider_factory import _build_from_config

router = APIRouter(prefix="/api/v2/settings", tags=["settings"])


# ── Request / Response models ──────────────

class LLMSettingsResponse(BaseModel):
    """Current LLM configuration (API key hidden)."""
    provider: str
    model: str
    configured: bool
    supported: list[str] = Field(default_factory=lambda: sorted(SUPPORTED_PROVIDERS))


class LLMSettingsRequest(BaseModel):
    """Request to update LLM configuration."""
    provider: str = Field(..., description="Provider name: deepseek, openai, spark, mock, rule")
    model: str = Field(default="", description="Model name (optional)")
    api_key: str = Field(default="", description="API key for the provider")


class TestConnectionResponse(BaseModel):
    """Result of LLM connection test."""
    success: bool
    provider: str
    model: str
    latency: float = 0.0
    error: str = ""


# ── Endpoints ──────────────────────────────

@router.get("/llm", response_model=LLMSettingsResponse)
def get_llm_settings() -> LLMSettingsResponse:
    """
    Get current LLM configuration.

    Returns provider, model, and configured status.
    API key is never returned.
    """
    cfg = load_llm_config()
    return LLMSettingsResponse(
        provider=cfg.provider,
        model=cfg.model,
        configured=cfg.is_configured,
        supported=sorted(SUPPORTED_PROVIDERS),
    )


@router.post("/llm", response_model=LLMSettingsResponse)
def update_llm_settings(req: LLMSettingsRequest) -> LLMSettingsResponse:
    """
    Save LLM configuration.

    Encrypts API key before storing.
    Returns updated configuration status.
    """
    # Validate provider
    if req.provider not in SUPPORTED_PROVIDERS:
        return LLMSettingsResponse(
            provider=req.provider,
            model=req.model,
            configured=False,
            supported=sorted(SUPPORTED_PROVIDERS),
        )

    # Build config and save
    cfg = LLMConfig(
        provider=req.provider,
        model=req.model,
        api_key=req.api_key,
    )
    save_llm_config(cfg)

    return LLMSettingsResponse(
        provider=cfg.provider,
        model=cfg.model,
        configured=cfg.is_configured,
        supported=sorted(SUPPORTED_PROVIDERS),
    )


@router.post("/test", response_model=TestConnectionResponse)
def test_llm_connection(req: Optional[LLMSettingsRequest] = None) -> TestConnectionResponse:
    """
    Test LLM connection using saved configuration or request body.

    If request body is provided, tests that configuration without saving.
    Otherwise tests the currently saved configuration.
    """
    # Determine config to test
    if req is not None and req.provider in SUPPORTED_PROVIDERS:
        cfg = LLMConfig(
            provider=req.provider,
            model=req.model,
            api_key=req.api_key,
        )
    else:
        cfg = load_llm_config()

    if not cfg.is_configured:
        return TestConnectionResponse(
            success=False,
            provider=cfg.provider,
            model=cfg.model,
            error="No API key configured. Please configure an LLM provider first.",
        )

    # Build provider and test
    t0 = time.time()
    try:
        provider = _build_from_config(cfg)
        if provider is None or not provider.is_available:
            return TestConnectionResponse(
                success=False,
                provider=cfg.provider,
                model=cfg.model,
                error=f"Provider '{cfg.provider}' is not available.",
            )

        # Simple connectivity test — attempt generate with minimal prompt
        response = provider.generate(
            prompt="ping",
            system_prompt="Reply with 'pong' only.",
            temperature=0.0,
            max_tokens=10,
        )
        latency = (time.time() - t0) * 1000

        if response.success:
            return TestConnectionResponse(
                success=True,
                provider=cfg.provider,
                model=cfg.model,
                latency=round(latency / 1000, 2),
            )
        else:
            return TestConnectionResponse(
                success=False,
                provider=cfg.provider,
                model=cfg.model,
                latency=round(latency / 1000, 2),
                error=response.error or "Provider returned an error.",
            )

    except Exception as e:
        latency = (time.time() - t0) * 1000
        return TestConnectionResponse(
            success=False,
            provider=cfg.provider,
            model=cfg.model,
            latency=round(latency / 1000, 2),
            error=str(e),
        )
