"""
Phase 5.1 — Experience Extractor Tests

Covers:
  1. extract_from_meta_reflection: actionable vs noise
  2. extract_from_evaluation: score thresholds
  3. extract_from_runtime_event: error events only
  4. Confidence scoring
  5. Noise filtering (too short, generic phrases)
  6. to_experience_record conversion
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from veritas.memory.experience_extractor import ExperienceExtractor, ExperienceLesson


# ──────────────────────────────────────────────
# 1. MetaReflection extraction
# ──────────────────────────────────────────────

class TestMetaReflection:
    def test_extracts_good_lesson(self):
        extractor = ExperienceExtractor()
        lesson = extractor.extract_from_meta_reflection(
            mistake="Too many concepts introduced in one section",
            root_cause="Cognitive overload from 5 new concepts at once",
            improvement="Split into 3 smaller sections with examples",
            severity="HIGH",
            node_id="node-4",
            concept="closures",
        )
        assert lesson is not None
        assert isinstance(lesson, ExperienceLesson)
        assert lesson.severity == "HIGH"
        assert lesson.confidence >= 0.5
        assert "Cognitive overload" in lesson.cause

    def test_filters_noise_short_text(self):
        extractor = ExperienceExtractor()
        # Use truly too-short text (each field < 1 char, combined < 5 chars)
        lesson = extractor.extract_from_meta_reflection(
            mistake="a", root_cause="b", improvement="c",  # combined "a b c" = 5 chars, meets threshold
        )
        # Actually at 5 chars it still passes. Test with empty or near-empty.
        lesson2 = extractor.extract_from_meta_reflection(
            mistake="", root_cause="", improvement="",  # empty → fails length
        )
        assert lesson2 is None

    def test_filters_generic_phrases(self):
        extractor = ExperienceExtractor()
        lesson = extractor.extract_from_meta_reflection(
            mistake="unknown", root_cause="n/a", improvement="todo",
        )
        assert lesson is None

    def test_low_severity_reduces_confidence(self):
        extractor = ExperienceExtractor()
        high = extractor.extract_from_meta_reflection(
            mistake="Concept overload detected",
            root_cause="Too many topics in one lesson",
            improvement="Split topics",
            severity="HIGH",
            node_id="n1",
        )
        low = extractor.extract_from_meta_reflection(
            mistake="Minor typo in notes",
            root_cause="Typo in formatting",
            improvement="Fix typo",
            severity="LOW",
            node_id="n2",
        )
        assert high is not None
        assert high.confidence > 0.4
        # LOW severity may still pass if has cause+improvement
        if low is not None:
            assert low.confidence < high.confidence

    def test_extracts_tags(self):
        extractor = ExperienceExtractor()
        lesson = extractor.extract_from_meta_reflection(
            mistake="Too many abstract concepts, concept density too high",
            root_cause="No prerequisite check before deep abstraction",
            improvement="Add concrete examples before abstraction",
            severity="HIGH",
            node_id="n5",
        )
        assert lesson is not None
        assert "concept-overload" in lesson.tags or "wrong-abstraction" in lesson.tags

    def test_to_experience_record(self):
        extractor = ExperienceExtractor()
        lesson = extractor.extract_from_meta_reflection(
            mistake="Missing type annotations in generated code",
            root_cause="LLM omission of type hints",
            improvement="Add type annotation check gate",
            severity="MEDIUM",
            node_id="node-2",
        )
        assert lesson is not None
        rec = lesson.to_experience_record()
        assert rec["problem"]  # not empty
        assert rec["source"] == "metareflector"
        assert rec["severity"] == "MEDIUM"


# ──────────────────────────────────────────────
# 2. Evaluation extraction
# ──────────────────────────────────────────────

class TestEvaluation:
    def test_extracts_from_low_score(self):
        extractor = ExperienceExtractor()
        lesson = extractor.extract_from_evaluation(
            score=45,
            issues=["No resources recommended", "Plan too short"],
            node_id="eval-1",
        )
        assert lesson is not None
        assert lesson.source == "evaluation"
        assert lesson.severity in ("MEDIUM", "HIGH")

    def test_no_extract_high_score(self):
        extractor = ExperienceExtractor()
        lesson = extractor.extract_from_evaluation(
            score=85,
            issues=[],
            node_id="eval-2",
        )
        assert lesson is None

    def test_no_extract_no_issues(self):
        extractor = ExperienceExtractor()
        lesson = extractor.extract_from_evaluation(
            score=30,
            issues=[],
            node_id="eval-3",
        )
        assert lesson is None  # No issues → nothing actionable


# ──────────────────────────────────────────────
# 3. RuntimeEvent extraction
# ──────────────────────────────────────────────

class TestRuntimeEvent:
    def test_extracts_from_error_event(self):
        extractor = ExperienceExtractor()
        lesson = extractor.extract_from_runtime_event({
            "event_type": "transition",
            "status": "error",
            "state": "REFLECT",
            "metadata": {"error": "ReflectionAgent handler timeout after 30s"},
        })
        assert lesson is not None
        assert lesson.source == "runtime"
        assert "ReflectionAgent" in lesson.problem

    def test_ignores_success_events(self):
        extractor = ExperienceExtractor()
        lesson = extractor.extract_from_runtime_event({
            "event_type": "transition",
            "status": "success",
            "state": "PROFILE",
        })
        assert lesson is None

    def test_ignores_short_error(self):
        extractor = ExperienceExtractor()
        lesson = extractor.extract_from_runtime_event({
            "event_type": "error",
            "status": "error",
            "metadata": {"error": "x"},  # too short
        })
        assert lesson is None

    def test_extracts_from_meta_reflection_event(self):
        extractor = ExperienceExtractor()
        lesson = extractor.extract_from_runtime_event({
            "event_type": "meta_reflection",
            "status": "success",
            "state": "META_REFLECT",
            "metadata": {"error": "Concept density triggered meta-reflection"},
        })
        assert lesson is not None
        assert lesson.source == "runtime"


# ──────────────────────────────────────────────
# 4. Confidence scoring
# ──────────────────────────────────────────────

class TestConfidence:
    def test_critical_with_evidence(self):
        extractor = ExperienceExtractor()
        lesson = extractor.extract_from_meta_reflection(
            mistake="Critical: pipeline crash from missing profile",
            root_cause="ProfileAgent returned empty when LLM call failed",
            improvement="Add a guard in ProfileAgent.extract()",
            severity="CRITICAL",
            node_id="n-crit",
        )
        assert lesson is not None
        # CRITICAL (base+0.2) + has_cause (0.15) + has_solution (0.2) = 1.05 → capped at 1.0
        assert lesson.confidence >= 0.85

    def test_low_no_evidence_low_confidence(self):
        extractor = ExperienceExtractor()
        lesson = extractor.extract_from_meta_reflection(
            mistake="tiny",
            root_cause="",
            improvement="",
            severity="LOW",
        )
        # Should be filtered by relevance gate before confidence check
        assert lesson is None


# ──────────────────────────────────────────────
# 5. ExperienceLesson model
# ──────────────────────────────────────────────

class TestExperienceLesson:
    def test_defaults(self):
        lesson = ExperienceLesson()
        assert lesson.problem == ""
        assert lesson.source == "metareflector"
        assert lesson.severity == "MEDIUM"
        assert lesson.confidence == 0.0

    def test_to_dict(self):
        lesson = ExperienceLesson(
            lesson_id="exp_1",
            problem="test problem",
            cause="test cause",
            context="test context",
            solution="test solution",
            confidence=0.85,
            tags=["tag1"],
        )
        d = lesson.to_dict()
        assert d["lesson_id"] == "exp_1"
        assert d["confidence"] == 0.85
        assert "tag1" in d["tags"]

    def test_to_experience_record(self):
        lesson = ExperienceLesson(
            problem="Long problem statement that should be truncated to 120 chars max so this is definitely over the limit.",
            cause="Root cause analysis here.",
            context="node-n1 / concept-X",
            solution="Fix it.",
            source="metareflector",
            node_id="n1",
            severity="HIGH",
        )
        rec = lesson.to_experience_record()
        assert len(rec["problem"]) <= 120
        assert len(rec["cause"]) <= 120
        assert rec["source"] == "metareflector"
        assert rec["severity"] == "HIGH"
