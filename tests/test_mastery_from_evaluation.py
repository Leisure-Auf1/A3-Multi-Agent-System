"""
Tests for Phase 8.2-B1 — Real evaluation-driven mastery updates.

Covers:
- weak_areas in evaluation → mastery input = 0.2
- strong_areas in evaluation → mastery input = 0.85
- Untested nodes → mastery input = 0.6
- Fallback to old behavior when evaluation is None
- Empty evaluation → old behavior
"""

import pytest
from unittest.mock import MagicMock, patch
from src.workflow import A3Workflow


class MockMemoryManager:
    """Captures mastery_updates passed to update_student_memory."""

    def __init__(self):
        self.last_mastery_updates = None

    def update_student_memory(self, student_id, profile=None,
                              mastery_updates=None, **kwargs):
        if mastery_updates is not None:
            self.last_mastery_updates = mastery_updates
        self.last_student_id = student_id


def _make_plan(node_ids=None):
    """Build a minimal plan dict with given node_ids."""
    if node_ids is None:
        node_ids = ["http_basics", "async_patterns", "security"]
    return {
        "nodes": [{"node_id": nid, "title": nid} for nid in node_ids],
        "total_minutes": 120,
    }


# ═══════════════════════════════════════════════════════════════
# _extract_mastery_updates() with evaluation
# ═══════════════════════════════════════════════════════════════


class TestMasteryUpdatesFromQuizResult:
    """evaluation weak/strong areas drive real mastery scores."""

    def test_weak_area_reduces_mastery_input(self):
        """Nodes in weak_areas get mastery input = 0.2."""
        wf = A3Workflow(student_id="test_user")
        plan = _make_plan(["http_basics", "async_patterns", "security"])
        evaluation = {
            "weak_areas": ["http_basics"],
            "strong_areas": [],
        }

        result = wf._extract_mastery_updates(plan, evaluation)

        assert result["http_basics"] == 0.2
        assert result["async_patterns"] == 0.6  # untested → neutral
        assert result["security"] == 0.6

    def test_strong_area_increases_mastery_input(self):
        """Nodes in strong_areas get mastery input = 0.85."""
        wf = A3Workflow(student_id="test_user")
        plan = _make_plan(["http_basics", "async_patterns", "security"])
        evaluation = {
            "weak_areas": [],
            "strong_areas": ["async_patterns"],
        }

        result = wf._extract_mastery_updates(plan, evaluation)

        assert result["async_patterns"] == 0.85
        assert result["http_basics"] == 0.6

    def test_mixed_weak_and_strong(self):
        """Weak and strong areas coexist in same evaluation."""
        wf = A3Workflow(student_id="test_user")
        plan = _make_plan(["http_basics", "async_patterns", "security"])
        evaluation = {
            "weak_areas": ["http_basics"],
            "strong_areas": ["async_patterns"],
        }

        result = wf._extract_mastery_updates(plan, evaluation)

        assert result["http_basics"] == 0.2
        assert result["async_patterns"] == 0.85
        assert result["security"] == 0.6

    def test_weak_and_strong_disjoint(self):
        """Node cannot be both weak and strong — weak takes precedence."""
        wf = A3Workflow(student_id="test_user")
        plan = _make_plan(["ambiguous_topic"])
        evaluation = {
            "weak_areas": ["ambiguous_topic"],
            "strong_areas": ["ambiguous_topic"],
        }

        result = wf._extract_mastery_updates(plan, evaluation)

        # weak takes precedence (checked first)
        assert result["ambiguous_topic"] == 0.2


class TestMasteryFallbackWithoutQuiz:
    """Without evaluation, old placeholder behavior is preserved."""

    def test_none_evaluation_returns_placeholder(self):
        """evaluation=None returns 0.6 for all nodes (old behavior)."""
        wf = A3Workflow(student_id="test_user")
        plan = _make_plan()

        result = wf._extract_mastery_updates(plan, None)

        for nid in result:
            assert result[nid] == 0.6

    def test_empty_evaluation_returns_placeholder(self):
        """Empty evaluation dict (no weak/strong) returns 0.6."""
        wf = A3Workflow(student_id="test_user")
        plan = _make_plan()

        result = wf._extract_mastery_updates(plan, {})

        for nid in result:
            assert result[nid] == 0.6

    def test_evaluation_without_weak_strong_keys(self):
        """Evaluation without weak_areas/strong_areas keys → old behavior."""
        wf = A3Workflow(student_id="test_user")
        plan = _make_plan()
        evaluation = {"score": 80, "passed": True}

        result = wf._extract_mastery_updates(plan, evaluation)

        for nid in result:
            assert result[nid] == 0.6

    def test_null_plan_returns_empty(self):
        """plan=None returns empty dict."""
        wf = A3Workflow(student_id="test_user")

        result = wf._extract_mastery_updates(None, {"weak_areas": ["x"]})

        assert result == {}


class TestSaveToMemoryPassesEvaluation:
    """_save_to_memory() forwards evaluation to _extract_mastery_updates."""

    def test_evaluation_reaches_mastery_updates(self):
        """Evaluation from pipeline flows to mastery calculation."""
        wf = A3Workflow(student_id="test_user")
        mock_mem = MockMemoryManager()
        wf.memory = mock_mem

        plan = _make_plan(["http", "async"])
        evaluation = {
            "weak_areas": ["http"],
            "strong_areas": ["async"],
        }

        wf._save_to_memory(
            student_id="test",
            user_goal="learn",
            profile={"knowledge_base": "junior_dev"},
            plan=plan,
            resources=[],
            reflection={},
            evaluation=evaluation,
        )

        updates = mock_mem.last_mastery_updates
        assert updates is not None
        assert updates["http"] == 0.2
        assert updates["async"] == 0.85

    def test_no_evaluation_still_works(self):
        """Calling without evaluation is backward-compatible."""
        wf = A3Workflow(student_id="test_user")
        mock_mem = MockMemoryManager()
        wf.memory = mock_mem

        plan = _make_plan(["http", "async"])

        wf._save_to_memory(
            student_id="test",
            user_goal="learn",
            profile={"knowledge_base": "junior_dev"},
            plan=plan,
            resources=[],
            reflection={},
        )

        updates = mock_mem.last_mastery_updates
        assert updates is not None
        for nid in updates:
            assert updates[nid] == 0.6
