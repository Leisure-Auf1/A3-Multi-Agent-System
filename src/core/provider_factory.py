"""
Phase 4.7 — Provider Factory (backward-compatible re-export)

DEPRECATED: Import directly from veritas.llm instead.
This module exists for backward compatibility only.

Usage (preferred):
    from veritas.llm import create_provider, get_provider_info

Usage (backward compat):
    from src.core.provider_factory import create_provider
"""

from __future__ import annotations
from typing import Optional

# Re-export from new canonical location
from veritas.llm.factory import create_provider, get_provider_info
from veritas.llm.provider import LLMProvider

__all__ = ["create_provider", "get_provider_info", "LLMProvider"]
