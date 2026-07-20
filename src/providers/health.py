"""
Phase 9.2 — Provider Health Check

Checks provider availability by making a minimal API call.

Usage:
    from src.providers.health import check_provider, check_all_providers

    result = check_provider("openai")
    # → {"provider": "openai", "available": True, "latency_ms": 234.5, "error": ""}

    results = check_all_providers()
    # → [{"provider": "openai", "available": False, ...}, ...]

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from .factory import ProviderFactory
from src.config.secrets import get_api_key, PROVIDER_LABELS, PROVIDER_EMOJI


def check_provider(
    provider_name: str,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Check if a provider is available by making a real API call.

    Sends a minimal prompt ("Hi") to verify connectivity and key validity.

    Args:
        provider_name: Provider name (openai / deepseek / ...).
        timeout: Max seconds to wait for the health check.

    Returns:
        {
            "provider": "openai",
            "label": "GPT (OpenAI)",
            "emoji": "🤖",
            "available": True/False,
            "latency_ms": 234.5 or None,
            "error": "" or error message,
        }
    """
    label = PROVIDER_LABELS.get(provider_name, provider_name)
    emoji = PROVIDER_EMOJI.get(provider_name, "🔌")

    # Read API key from env
    api_key = get_api_key(provider_name)
    if not api_key:
        return {
            "provider": provider_name,
            "label": label,
            "emoji": emoji,
            "available": False,
            "latency_ms": None,
            "error": f"Missing {provider_name.upper()}_API_KEY environment variable",
        }

    # Create provider and test
    try:
        provider = ProviderFactory.create(provider_name, api_key=api_key)
    except ValueError as e:
        return {
            "provider": provider_name,
            "label": label,
            "emoji": emoji,
            "available": False,
            "latency_ms": None,
            "error": f"Failed to create provider: {e}",
        }

    start = time.time()
    try:
        resp = provider.generate("Hi")
        elapsed = (time.time() - start) * 1000  # ms

        if resp.success:
            return {
                "provider": provider_name,
                "label": label,
                "emoji": emoji,
                "available": True,
                "latency_ms": round(elapsed, 1),
                "error": "",
                "model": resp.model,
            }
        else:
            return {
                "provider": provider_name,
                "label": label,
                "emoji": emoji,
                "available": False,
                "latency_ms": round(elapsed, 1),
                "error": resp.error,
            }
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return {
            "provider": provider_name,
            "label": label,
            "emoji": emoji,
            "available": False,
            "latency_ms": round(elapsed, 1) if elapsed > 0 else None,
            "error": str(e)[:500],
        }


def check_all_providers(
    timeout: float = 10.0,
) -> List[Dict[str, Any]]:
    """
    Check all 8 providers sequentially.

    Each provider gets up to `timeout` seconds.
    Total max time ≈ 8 × timeout seconds.

    Returns:
        List of result dicts, same shape as check_provider().
    """
    results = []
    for name in ["openai", "anthropic", "google", "qwen",
                  "deepseek", "kimi", "grok", "spark"]:
        results.append(check_provider(name, timeout=timeout))
    return results
