"""
Phase 11.5 — LLM-Enabled Agent Adapter

Provides a unified adapter that allows any agent to switch between
LLM mode (using LLMProvider.generate()) and rule mode (fallback to
deterministic logic).

Design:
- Each agent method can be wrapped with @llm_or_rule
- Adapter handles prompt construction, parsing, and fallback
- LLM failure automatically triggers rule-mode fallback
- Zero modification to existing agent internals

Usage:
    adapter = LLMAgentAdapter(provider=mock_provider)
    result = adapter.call(
        agent_name="ProfileAgent",
        prompt_template="Extract profile from: {text}",
        input_vars={"text": "I'm a visual learner..."},
        rule_fn=lambda: profile_agent.extract(text),
        output_parser=json.loads,
    )
"""

from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from veritas.llm.provider import LLMProvider
from src.core.event_bus import AgentEventBus


# ──────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────

@dataclass
class AdapterCallResult:
    """Result from an LLM adapter call."""
    success: bool
    mode: str  # "llm" | "rule"
    data: Any
    llm_response: str = ""
    error: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "mode": self.mode,
            "error": self.error,
            "latency_ms": self.latency_ms,
        }


@dataclass
class AdapterStats:
    """Statistics for the LLM agent adapter."""
    total_calls: int = 0
    llm_calls: int = 0
    rule_fallbacks: int = 0
    errors: int = 0
    total_latency_ms: float = 0.0

    @property
    def fallback_rate(self) -> float:
        return self.rule_fallbacks / max(self.total_calls, 1)

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(self.total_calls, 1)


# ──────────────────────────────────────────────
# LLMAgentAdapter
# ──────────────────────────────────────────────

class LLMAgentAdapter:
    """
    Adapter for LLM-enabled agents with automatic rule fallback.

    This is NOT a replacement for agents — it wraps existing agent
    methods and adds LLM capability with fallback.
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        default_system_prompt: str = "You are an AI education agent. Be precise and structured.",
        max_retries: int = 1,
        fallback_enabled: bool = True,
    ):
        self.provider = provider
        self.default_system_prompt = default_system_prompt
        self.max_retries = max_retries
        self.fallback_enabled = fallback_enabled
        self.stats = AdapterStats()
        self._bus = AgentEventBus.get_instance()

    # ── Main Call API ──────────────────────────

    def call(
        self,
        agent_name: str,
        prompt_template: str,
        input_vars: Dict[str, str],
        rule_fn: Callable[[], Any],
        output_parser: Optional[Callable[[str], Any]] = None,
        system_prompt: str = "",
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AdapterCallResult:
        """
        Call an agent via LLM with automatic rule fallback.

        Args:
            agent_name: Agent identifier (e.g., "ProfileAgent").
            prompt_template: String template with {variable} placeholders.
            input_vars: Dict of values to fill the template.
            rule_fn: Zero-arg function that returns the rule-based result.
            output_parser: Optional parser for LLM output (default: identity).
            system_prompt: Override the default system prompt.
            temperature: LLM temperature for generation.
            max_tokens: Max tokens for LLM response.

        Returns:
            AdapterCallResult with success, mode, data.
        """
        self.stats.total_calls += 1
        t0 = time.time()

        # If no provider, go straight to rule
        if not self.provider or not self.provider.is_available:
            return self._fallback_to_rule(agent_name, rule_fn, t0, reason="no_provider")

        # Build prompt
        prompt = prompt_template.format(**input_vars)
        sys_prompt = system_prompt or self.default_system_prompt

        # Try LLM call with retries
        for attempt in range(self.max_retries + 1):
            try:
                response = self.provider.generate(
                    prompt=prompt,
                    system_prompt=sys_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                if response.success:
                    # Parse output
                    data = response.content
                    if output_parser:
                        try:
                            data = output_parser(response.content)
                        except Exception as parse_err:
                            if self.fallback_enabled:
                                return self._fallback_to_rule(
                                    agent_name, rule_fn, t0,
                                    reason=f"parse_error: {parse_err}"
                                )
                            data = response.content

                    latency = (time.time() - t0) * 1000
                    self.stats.llm_calls += 1
                    self.stats.total_latency_ms += latency

                    self._bus.emit(
                        agent=agent_name,
                        action="llm_call",
                        input_summary=prompt[:100],
                        output_summary=str(data)[:100],
                        status="success",
                        duration_ms=latency,
                    )

                    return AdapterCallResult(
                        success=True,
                        mode="llm",
                        data=data,
                        llm_response=response.content,
                        latency_ms=latency,
                    )

                # LLM returned error — retry or fallback
                if attempt < self.max_retries:
                    continue

            except Exception as e:
                if attempt < self.max_retries:
                    continue
                if self.fallback_enabled:
                    return self._fallback_to_rule(agent_name, rule_fn, t0, reason=str(e))

        # All retries exhausted
        if self.fallback_enabled:
            return self._fallback_to_rule(agent_name, rule_fn, t0, reason="max_retries")

        # No fallback — return error
        latency = (time.time() - t0) * 1000
        self.stats.errors += 1
        return AdapterCallResult(
            success=False, mode="llm", data=None,
            error="LLM call failed after retries", latency_ms=latency,
        )

    def _fallback_to_rule(
        self,
        agent_name: str,
        rule_fn: Callable[[], Any],
        t0: float,
        reason: str = "",
    ) -> AdapterCallResult:
        """Execute rule-based fallback."""
        latency = (time.time() - t0) * 1000
        self.stats.rule_fallbacks += 1
        self.stats.total_latency_ms += latency

        try:
            result = rule_fn()
        except Exception as e:
            self.stats.errors += 1
            return AdapterCallResult(
                success=False, mode="rule", data=None,
                error=f"Rule fallback failed: {e}", latency_ms=latency,
            )

        self._bus.emit(
            agent=agent_name,
            action="rule_fallback",
            input_summary=f"Reason: {reason}",
            output_summary=str(result)[:100],
            status="success",
            duration_ms=latency,
        )

        return AdapterCallResult(
            success=True,
            mode="rule",
            data=result,
            latency_ms=latency,
        )

    # ── Convenience: JSON output ────────────────

    def call_json(
        self,
        agent_name: str,
        prompt_template: str,
        input_vars: Dict[str, str],
        rule_fn: Callable[[], Any],
        **kwargs,
    ) -> AdapterCallResult:
        """
        Call an agent expecting JSON output.
        Uses json.loads as the output parser.
        """
        return self.call(
            agent_name=agent_name,
            prompt_template=prompt_template,
            input_vars=input_vars,
            rule_fn=rule_fn,
            output_parser=self._safe_json_parse,
            system_prompt=kwargs.get("system_prompt", "") + "\nOutput ONLY valid JSON. No markdown, no explanation.",
            temperature=kwargs.get("temperature", 0.1),
            max_tokens=kwargs.get("max_tokens", 1024),
        )

    @staticmethod
    def _safe_json_parse(text: str) -> Any:
        """Parse JSON from text, handling markdown code blocks."""
        text = text.strip()
        # Strip markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]) if len(lines) > 2 else text
            if text.endswith("```"):
                text = text[:-3]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try extracting first JSON object
            import re
            m = re.search(r"\{[^{}]*\}", text, re.DOTALL)
            if m:
                return json.loads(m.group())
            raise

    # ── Stats ───────────────────────────────────

    def reset_stats(self):
        self.stats = AdapterStats()

    @property
    def fallback_rate(self) -> float:
        return self.stats.fallback_rate

    def __repr__(self) -> str:
        return (
            f"LLMAgentAdapter(provider={self.provider}, "
            f"calls={self.stats.total_calls}, "
            f"fallback_rate={self.stats.fallback_rate:.0%})"
        )


# ──────────────────────────────────────────────
# CLI Demo
# ──────────────────────────────────────────────

if __name__ == "__main__":
    from veritas.llm.mock_provider import MockLLMProvider

    print("╔══════════════════════════════════════════╗")
    print("║  LLMAgentAdapter — Demo                 ║")
    print("╚══════════════════════════════════════════╝")
    print()

    # Mock provider
    mock = MockLLMProvider()
    mock.add_response(
        "Extract profile",
        '{"knowledge_base": "mid_level", "cognitive_style": "visual_dominant"}',
    )

    adapter = LLMAgentAdapter(provider=mock)

    # Test 1: LLM mode
    result = adapter.call_json(
        agent_name="ProfileAgent",
        prompt_template="Extract profile from: {text}",
        input_vars={"text": "I am an intermediate programmer who likes visuals."},
        rule_fn=lambda: {"knowledge_base": "junior_dev", "source": "rule"},
    )
    print(f"Test 1 — LLM mode: {result.mode}, data={result.data}")
    print(f"  Latency: {result.latency_ms:.1f}ms")

    # Test 2: Force rule fallback (no provider)
    adapter_nollm = LLMAgentAdapter(provider=None)
    result2 = adapter_nollm.call(
        agent_name="TestAgent",
        prompt_template="Do something: {text}",
        input_vars={"text": "test"},
        rule_fn=lambda: "rule_result",
    )
    print(f"Test 2 — No provider fallback: {result2.mode}, data={result2.data}")

    print(f"\nStats: {adapter.stats}")
