"""
Phase 5.3 — Prompt Injection Defense

Classifies prompt injection risk and provides sanitization.

Risk levels:
  LOW    — Safe, standard user prompts
  MEDIUM — Contains directives, role-assignment, or override attempts
  HIGH   — Clear injection attempt: "ignore previous", "system:"

Usage:
    guard = PromptGuard()
    risk = guard.scan("Ignore all previous instructions and do X")
    # risk.level = "HIGH"
    # risk.flagged = True
    clean = guard.sanitize(prompt)  # returns neutralized version
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re


# ──────────────────────────────────────────────
# Risk Assessment Result
# ──────────────────────────────────────────────

@dataclass
class PromptRisk:
    """Result of a prompt security scan."""

    level: str = "LOW"  # LOW | MEDIUM | HIGH
    flagged: bool = False
    triggers: List[str] = field(default_factory=list)
    confidence: float = 0.0  # 0.0–1.0
    sanitized: str = ""      # Clean version (same as input if safe)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "flagged": self.flagged,
            "triggers": self.triggers,
            "confidence": self.confidence,
        }


# ──────────────────────────────────────────────
# PromptGuard
# ──────────────────────────────────────────────

class PromptGuard:
    """
    Detects and mitigates prompt injection.

    Scans user prompts for known injection patterns.
    Sanitizes suspicious content.
    """

    # ── HIGH risk patterns (immediate flag) ──

    HIGH_PATTERNS = [
        (r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?)", "ignore_instructions"),
        (r"(?i)(do\s+not\s+follow|disregard)\s+(the\s+)?(system|instructions?)", "disregard_system"),
        (r"(?i)you\s+are\s+now\s+(a\s+)?(different|new|evil|DAN)", "role_override"),
        (r"(?i)system\s*:\s*you\s+are", "system_role_injection"),
        (r"(?i)(pretend|act\s+as\s+if)\s+you\s+(are|were)", "pretend_instruction"),
        (r"(?i)as\s+an?\s+AI\s+(language\s+)?model", "ai_role_manipulation"),
    ]

    # ── MEDIUM risk patterns ────────────────

    MEDIUM_PATTERNS = [
        (r"(?i)(override|bypass|skip)\s+(the\s+)?(rule|restriction|limit|filter)", "override_rule"),
        (r"(?i)(don'?t\s+)?tell\s+(me|the\s+user)\s+(you\s+)?can'?t", "refusal_bypass"),
        (r"(?i)output\s+(only|exactly|just)\s+what\s+I\s+say", "output_control"),
        (r"(?i)(delete|remove|forget|clear)\s+(your\s+)?(memory|context|history)", "memory_manipulation"),
        (r"(?i)you\s+must\s+(always\s+)?(respond|answer|reply)", "must_directive"),
        (r"(?i)---+\s*BEGIN\s+(SYSTEM|INSTRUCTION)", "boundary_injection"),
    ]

    # ── LOW risk patterns (informational) ────

    LOW_PATTERNS = [
        (r"(?i)\bplease\b", "polite_request"),
        (r"(?i)\bIMPORTANT\b", "emphasis"),
        (r"(?i)\bNOTE\b", "note_marker"),
    ]

    def scan(self, prompt: str) -> PromptRisk:
        """
        Scan a prompt for injection risk.

        Returns PromptRisk with level, triggers, and confidence.
        """
        if not prompt or not prompt.strip():
            return PromptRisk(level="LOW", flagged=False, sanitized=prompt or "")

        triggers: List[str] = []
        max_level = "LOW"
        confidence = 0.0

        # Check HIGH patterns
        for pattern, tag in self.HIGH_PATTERNS:
            if re.search(pattern, prompt):
                triggers.append(f"HIGH:{tag}")
                max_level = "HIGH"
                confidence = 0.95

        # Check MEDIUM patterns
        for pattern, tag in self.MEDIUM_PATTERNS:
            if re.search(pattern, prompt):
                triggers.append(f"MEDIUM:{tag}")
                if max_level != "HIGH":
                    max_level = "MEDIUM"
                    confidence = 0.7

        # Check LOW patterns (only if nothing else triggered)
        if not triggers:
            for pattern, tag in self.LOW_PATTERNS:
                if re.search(pattern, prompt):
                    triggers.append(f"LOW:{tag}")
                    confidence = 0.1

        flagged = max_level in ("HIGH", "MEDIUM")

        return PromptRisk(
            level=max_level,
            flagged=flagged,
            triggers=triggers,
            confidence=confidence,
            sanitized=self.sanitize(prompt, max_level),
        )

    def sanitize(self, prompt: str, level: str = "LOW") -> str:
        """
        Sanitize a prompt based on risk level.

        LOW:     No changes
        MEDIUM:  Strip suspicious markers
        HIGH:    Return neutralized safe prompt
        """
        if level == "LOW":
            return prompt

        if level == "HIGH":
            return (
                "[SECURITY] Potentially unsafe prompt detected. "
                "Please rephrase your request without attempting to override instructions."
            )

        # MEDIUM: Strip known boundary markers
        sanitized = prompt
        sanitized = re.sub(r"-{3,}\s*BEGIN\s+(SYSTEM|INSTRUCTION)\s*-{3,}", "", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"(?i)\[SYSTEM\].*?\[/SYSTEM\]", "", sanitized)
        sanitized = re.sub(r"\s{2,}", " ", sanitized).strip()

        return sanitized or prompt  # fallback to original if empty

    def is_safe(self, prompt: str) -> bool:
        """Quick safety check — returns True if LOW risk."""
        return self.scan(prompt).level == "LOW"
