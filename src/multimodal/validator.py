"""
Phase 9.5 — Content Validator

Three-stage validation pipeline:
  1. Academic validation (content quality, coverage)
  2. Format validation (Markdown, JSON, Python)
  3. Safety validation (PII, harmful content, injection)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from .artifact import ResourceArtifact, ResourceType


@dataclass
class ValidationResult:
    """Result of the validation pipeline."""
    passed: bool = True
    is_critical: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stage: str = ""


class ContentValidator:
    """Three-stage content validation pipeline."""

    # ── Stage 1: Academic Validation ──────────────────────

    def _validate_academic(self, artifact: ResourceArtifact) -> List[str]:
        errors = []
        content = artifact.content or ""

        # Check: content is not empty
        if not content.strip():
            errors.append("Content is empty")
            return errors

        # Check: minimum length (100 chars)
        if len(content) < 50:
            errors.append(f"Content too short: {len(content)} chars (min 50)")

        # Check: topic relevance
        if artifact.topic and artifact.topic.lower() not in content.lower():
            errors.append(f"Content may not be relevant to topic: {artifact.topic}")

        # Check: concept coverage (at least 1 concept mentioned)
        if hasattr(artifact, 'metadata') and artifact.metadata.get('concepts'):
            concepts = artifact.metadata['concepts']
            covered = sum(1 for c in concepts if c.lower() in content.lower())
            if covered == 0:
                errors.append("None of the target concepts are covered in content")

        return errors

    # ── Stage 2: Format Validation ────────────────────────

    def _validate_format(self, artifact: ResourceArtifact) -> List[str]:
        errors = []
        content = artifact.content or ""
        fmt = artifact.content_format

        if fmt == "markdown":
            # Must have at least one heading
            if not re.search(r'^#+\s', content, re.MULTILINE):
                errors.append("Markdown: no headings found")
            # Must have some body text
            if len(content.split('\n')) < 5:
                errors.append("Markdown: too few lines (min 5)")

        elif fmt == "json":
            import json
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                errors.append(f"JSON parse error: {e}")

        elif fmt == "python":
            # Check for basic Python syntax
            try:
                compile(content, "<artifact>", "exec")
            except SyntaxError as e:
                errors.append(f"Python syntax error: {e}")
            # No dangerous code
            dangerous = ['os.system', 'subprocess', 'eval(', 'exec(',
                         'rm -rf', '__import__']
            for d in dangerous:
                if d in content:
                    errors.append(f"Python: dangerous code detected ({d})")

        elif fmt == "base64":
            if not content.startswith("data:"):
                errors.append("Base64: invalid data URI format")

        return errors

    # ── Stage 3: Safety Validation ────────────────────────

    PII_PATTERNS = [
        (r'\b\d{17}[\dXx]\b', 'Chinese ID number'),
        (r'\b1[3-9]\d{9}\b', 'Chinese phone number'),
        (r'\b[\w.-]+@[\w.-]+\.\w+\b', 'Email address'),
    ]

    HARMFUL_KEYWORDS = [
        'violence', 'hate speech', 'self-harm', 'suicide',
        'illegal activity', 'nsfw', 'pornography',
    ]

    INJECTION_PATTERNS = [
        r'ignore (previous|all) instructions',
        r'system prompt:',
        r'<<SYS>>',
        r'you are now',
        r'act as',
    ]

    def _validate_safety(self, artifact: ResourceArtifact) -> List[str]:
        errors = []
        content = artifact.content or ""
        lower = content.lower()

        # PII check
        for pattern, label in self.PII_PATTERNS:
            if re.search(pattern, content):
                errors.append(f"PII detected: {label}")

        # Harmful content
        for kw in self.HARMFUL_KEYWORDS:
            if kw in lower:
                errors.append(f"Harmful content detected: {kw}")

        # Prompt injection
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, lower):
                errors.append(f"Prompt injection detected: {pattern}")

        return errors

    # ── Pipeline orchestration ────────────────────────────

    def validate(self, artifact: ResourceArtifact) -> ValidationResult:
        """
        Run all three stages. Stop on critical failures.
        Academic/format errors are non-critical (can still activate).
        Safety errors are ALWAYS critical.
        """
        all_errors = []
        result = ValidationResult()

        # Stage 1: Academic
        academic_errors = self._validate_academic(artifact)
        all_errors.extend(academic_errors)
        result.stage = "academic"

        # Stage 2: Format
        format_errors = self._validate_format(artifact)
        all_errors.extend(format_errors)
        result.stage = "format"

        # Stage 3: Safety (always runs)
        safety_errors = self._validate_safety(artifact)
        all_errors.extend(safety_errors)
        result.stage = "safety"

        if safety_errors:
            result.is_critical = True
            result.passed = False
            result.errors = all_errors
            return result

        if all_errors:
            result.errors = all_errors
            # Non-critical errors: still allow activation
            result.passed = False
            result.is_critical = False
        else:
            result.passed = True

        return result
