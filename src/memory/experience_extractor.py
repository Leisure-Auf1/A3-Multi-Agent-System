"""
Phase 5.1 — Experience Extractor

Converts raw runtime events and MetaReflection results
into structured ExperienceLesson records for Agent Memory.

Responsibilities:
  - Filter meaningless runtime information (noise)
  - Extract reusable agent knowledge
  - Assign confidence score based on evidence quality
  - Bridge Runtime → Memory without direct coupling

Architecture:
    Runtime Events / MetaReflection
            │
    ExperienceExtractor
            │
    ExperienceRecord → MemoryManager
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import re


# ──────────────────────────────────────────────
# Data Model
# ──────────────────────────────────────────────

@dataclass
class ExperienceLesson:
    """
    Structured, high-quality agent knowledge extracted from runtime.

    Contrast with raw FailurePatternLesson (contracts.py):
      - FailurePatternLesson: raw, code-level, error-specific
      - ExperienceLesson: generalized, reusable, confidence-weighted
    """

    lesson_id: str = ""
    problem: str = ""               # Abstracted problem statement
    cause: str = ""                 # Root cause analysis
    context: str = ""               # When/where this applies
    solution: str = ""              # Recommended fix or strategy
    source: str = "metareflector"   # origin: metareflector | evaluation | reflection
    node_id: str = ""               # Associated pipeline node
    severity: str = "MEDIUM"        # LOW | MEDIUM | HIGH | CRITICAL
    confidence: float = 0.0         # 0.0–1.0, based on evidence quality
    evidence_count: int = 0         # Number of confirming events
    tags: List[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lesson_id": self.lesson_id,
            "problem": self.problem,
            "cause": self.cause,
            "context": self.context,
            "solution": self.solution,
            "source": self.source,
            "node_id": self.node_id,
            "severity": self.severity,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "tags": self.tags,
            "created_at": self.created_at,
        }

    def to_experience_record(self) -> Dict[str, Any]:
        """Convert to MemoryManager.store_experience() compatible format."""
        return {
            "problem": self.problem[:120],
            "cause": self.cause[:120],
            "context": self.context[:200],
            "solution": self.solution[:300],
            "source": self.source,
            "node_id": self.node_id,
            "severity": self.severity,
            "applicable_profile": _extract_profile_tag(self.context),
        }


# ──────────────────────────────────────────────
# ExperienceExtractor
# ──────────────────────────────────────────────

class ExperienceExtractor:
    """
    Extracts reusable agent knowledge from runtime data.

    Filters raw events through quality gates:
      1. Relevance filter — discard noise/uninformative events
      2. Deduplication — merge similar lessons
      3. Confidence scoring — weigh by evidence strength

    Usage:
        extractor = ExperienceExtractor()
        lesson = extractor.extract_from_meta_reflection(
            mistake="too many concepts",
            root_cause="cognitive overload",
            improvement="split into 3 sections",
            severity="HIGH",
            node_id="node-3",
        )
        # Store to Memory
        mm.store_experience(**lesson.to_experience_record())
    """

    MIN_CONFIDENCE: float = 0.3  # Below this, don't store
    MIN_PROBLEM_LENGTH: int = 5  # Too short = noise

    def extract_from_meta_reflection(
        self,
        mistake: str = "",
        root_cause: str = "",
        improvement: str = "",
        severity: str = "MEDIUM",
        node_id: str = "",
        concept: str = "",
    ) -> Optional[ExperienceLesson]:
        """
        Extract a lesson from MetaReflector output.

        Filters out trivial/non-actionable reflections.
        """
        # Gate 1: Relevance
        if not self._is_actionable(mistake, root_cause, improvement):
            return None

        # Gate 2: Severity boost
        confidence = self._compute_confidence(
            severity=severity,
            has_cause=bool(root_cause and len(root_cause) > 10),
            has_solution=bool(improvement and len(improvement) > 10),
        )

        if confidence < self.MIN_CONFIDENCE:
            return None

        tags = self._extract_tags(mistake, root_cause)

        return ExperienceLesson(
            lesson_id=f"exp_{node_id}_{severity.lower()}",
            problem=self._clean(mistake)[:120],
            cause=self._clean(root_cause)[:120],
            context=f"node-{node_id} / {concept}" if concept else f"node-{node_id}",
            solution=self._clean(improvement)[:300],
            source="metareflector",
            node_id=node_id,
            severity=severity,
            confidence=confidence,
            evidence_count=1,
            tags=tags,
        )

    def extract_from_evaluation(
        self,
        score: int = 100,
        issues: Optional[List[str]] = None,
        node_id: str = "",
    ) -> Optional[ExperienceLesson]:
        """
        Extract a lesson from EvaluationManager output.

        Only fires when evaluation reveals actionable problems.
        """
        issues = issues or []
        if not issues or score >= 70:
            return None

        problem = "; ".join(issues[:2])
        severity = "HIGH" if score < 40 else "MEDIUM" if score < 60 else "LOW"

        confidence = self._compute_confidence(
            severity=severity,
            has_cause=True,
            has_solution=False,  # evaluation has no solution, just score
        )
        if confidence < self.MIN_CONFIDENCE:
            return None

        return ExperienceLesson(
            lesson_id=f"eval_{node_id}_{severity.lower()}",
            problem=self._clean(problem)[:120],
            cause="Evaluation score below threshold — quality issue detected",
            context=f"node-{node_id} / score={score}",
            solution="Review content quality; consider reflection-based improvement",
            source="evaluation",
            node_id=node_id,
            severity=severity,
            confidence=confidence * 0.5,  # evaluation has less evidence
            evidence_count=1,
        )

    def extract_from_runtime_event(
        self,
        event_data: Dict[str, Any],
    ) -> Optional[ExperienceLesson]:
        """
        Extract a lesson from a raw RuntimeEvent dict.

        Only error events with actionable metadata produce lessons.
        """
        etype = event_data.get("event_type", "")
        status = event_data.get("status", "")

        if status != "error" and etype not in ("error", "reflection", "meta_reflection"):
            return None

        metadata = event_data.get("metadata", {}) or {}
        error_msg = metadata.get("error", metadata.get("error_message", ""))
        if not error_msg or len(error_msg) < self.MIN_PROBLEM_LENGTH:
            return None

        state = event_data.get("state", "UNKNOWN")

        return ExperienceLesson(
            lesson_id=f"rt_{state.lower()}",
            problem=self._clean(error_msg)[:120],
            cause=f"Runtime error at state: {state}",
            context=f"state-{state}",
            solution="Investigate handler implementation for this state",
            source="runtime",
            node_id=state,
            severity="MEDIUM",
            confidence=0.3,
            evidence_count=1,
        )

    # ── Helpers ───────────────────────────────

    def _is_actionable(self, mistake: str, cause: str, solution: str) -> bool:
        """Check if the reflection is worth persisting."""
        text = f"{mistake} {cause} {solution}"
        # Too short → likely noise (allow single letters to pass)
        if len(text.strip()) < self.MIN_PROBLEM_LENGTH:
            return False
        # Generic phrases → not useful (whole-word match only)
        noise_words = {"unknown", "n/a", "none", "todo", "待定"}
        words = set(text.lower().split())
        if noise_words & words:
            return False
        return True

    def _compute_confidence(
        self,
        severity: str = "MEDIUM",
        has_cause: bool = False,
        has_solution: bool = False,
    ) -> float:
        """Score confidence 0.0–1.0 based on evidence quality."""
        base = 0.5  # Default

        # Severity weight
        if severity == "CRITICAL":
            base += 0.2
        elif severity == "HIGH":
            base += 0.1
        elif severity == "LOW":
            base -= 0.2

        # Evidence completeness
        if has_cause:
            base += 0.15
        if has_solution:
            base += 0.2

        return round(max(0.0, min(1.0, base)), 2)

    @staticmethod
    def _clean(text: str) -> str:
        """Normalize text: strip excessive whitespace, trim."""
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _extract_tags(mistake: str, cause: str) -> List[str]:
        """Extract keyword tags from reflection text."""
        combined = f"{mistake} {cause}".lower()
        tags = []
        tag_patterns = {
            "concept-overload": ["太多", "过多", "overload", "密度", "density"],
            "wrong-abstraction": ["抽象", "abstraction", "错误建模"],
            "needs-example": ["缺少例子", "示例", "example", "没有例子"],
            "pacing-issue": ["太快", "节奏", "pacing", "慢", "too fast", "too slow"],
            "prerequisite-gap": ["前置", "prerequisite", "没学过", "missing"],
        }
        for tag, keywords in tag_patterns.items():
            if any(kw in combined for kw in keywords):
                tags.append(tag)
        return tags[:3]


def _extract_profile_tag(context: str) -> str:
    """Extract a profile-type tag from context text."""
    profile_hints = {
        "junior": "junior_dev",
        "visual": "visual_dominant",
        "auditory": "auditory",
        "senior": "senior",
        "beginner": "junior_dev",
    }
    ctx_lower = context.lower()
    for hint, tag in profile_hints.items():
        if hint in ctx_lower:
            return tag
    return ""
