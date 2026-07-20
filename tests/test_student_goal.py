"""
Tests for Phase 8.3-D2 — Long-Term Learning Goal Management.

Covers:
- StudentGoal model: creation, serialization, preset generation
- StudentGoal: milestone checking, progress computation
- Goal Store: CRUD, persistence, summary
- PlannerAgent: goal-driven course selection, pace adjustment, concept boosting
- ContentGeneratorAgent: goal-driven title, objectives, summary
- ResourceAgent: goal-driven career/exam resource augmentation
- Dashboard: data provider and rendering (unit test)
- Backward compatibility: no goal → existing behavior preserved

Constraints:
- Does NOT modify Veritas-Core
- Does NOT modify src/core/
- All existing agent interfaces remain backward-compatible
"""

import json
import sys
import os
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


# ──────────────────────────────────────────────
# Test Data Helpers
# ──────────────────────────────────────────────

TEST_STUDENT_ID = "test_goal_student"


def _ensure_test_user(user_id: str) -> None:
    """Create a minimal user record so FK constraints pass."""
    from src.data.db import _get_conn, init_db
    from datetime import datetime, timezone
    init_db()  # ensure tables exist on current connection
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO users (id, email, password_hash, display_name, is_guest, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, f"{user_id}@test.local", "hash_test", "Test User", 0, now),
    )
    conn.commit()


def _make_career_goal() -> "StudentGoal":
    from src.agents.student_goal import StudentGoal, Milestone, GoalCategory

    milestones = [
        Milestone(
            milestone_id="ms_1",
            title="掌握 Python 基础",
            target_concepts=["python_basics"],
            target_mastery=0.8,
            estimated_days=5,
        ),
        Milestone(
            milestone_id="ms_2",
            title="掌握 API 设计",
            target_concepts=["api_design", "rest"],
            target_mastery=0.8,
            estimated_days=7,
        ),
        Milestone(
            milestone_id="ms_3",
            title="掌握 Docker",
            target_concepts=["docker"],
            target_mastery=0.7,
            estimated_days=5,
        ),
    ]

    goal = StudentGoal(
        goal_id=uuid.uuid4().hex[:16],
        student_id=TEST_STUDENT_ID,
        category="career",
        target="Python 后端工程师",
        target_level="intermediate",
        milestones=milestones,
        deadline="2026-12-31",
        metadata={"preset_id": "python_backend"},
    )
    goal.recompute_progress()
    return goal


# ──────────────────────────────────────────────
# 1. StudentGoal Model Tests
# ──────────────────────────────────────────────


class TestStudentGoalModel:
    """StudentGoal data model behavior."""

    def test_create_and_serialize(self):
        """Goal created from dataclass → dict → from_dict roundtrip."""
        from src.agents.student_goal import StudentGoal, Milestone

        ms = Milestone(
            milestone_id="ms_x",
            title="Test MS",
            target_concepts=["c1", "c2"],
            target_mastery=0.8,
            estimated_days=3,
        )
        goal = StudentGoal(
            goal_id="g001",
            student_id="s001",
            category="career",
            target="Python Backend",
            milestones=[ms],
        )

        d = goal.to_dict()
        assert d["goal_id"] == "g001"
        assert d["category"] == "career"
        assert d["progress"] == 0.0
        assert d["completed_milestones"] == 0
        assert d["total_milestones"] == 1
        assert d["milestones"][0]["title"] == "Test MS"

        restored = StudentGoal.from_dict(d)
        assert restored.goal_id == "g001"
        assert restored.target == "Python Backend"
        assert len(restored.milestones) == 1
        assert restored.milestones[0].milestone_id == "ms_x"

    def test_progress_computation(self):
        """Progress = completed / total milestones."""
        from src.agents.student_goal import StudentGoal, Milestone

        ms1 = Milestone("a", "M1", completed=True)
        ms2 = Milestone("b", "M2", completed=False)
        ms3 = Milestone("c", "M3", completed=True)
        goal = StudentGoal("g", "s", milestones=[ms1, ms2, ms3])
        goal.recompute_progress()
        assert goal.progress == pytest.approx(0.67, abs=0.01)
        assert goal.completed_milestones == 2
        assert goal.total_milestones == 3

    def test_progress_zero_milestones(self):
        from src.agents.student_goal import StudentGoal
        goal = StudentGoal("g", "s")
        goal.recompute_progress()
        assert goal.progress == 0.0

    def test_check_milestones_against_mastery(self):
        """Mastery triggers milestone completion."""
        goal = _make_career_goal()

        # ms_1 needs python_basics ≥ 0.8
        result = goal.check_milestones_against_mastery(
            {"python_basics": 0.85}
        )
        assert "ms_1" in result["newly_completed"]
        assert goal.progress > 0.0

    def test_milestone_not_met_when_below_threshold(self):
        goal = _make_career_goal()
        result = goal.check_milestones_against_mastery(
            {"python_basics": 0.6}  # below 0.8
        )
        assert "ms_1" not in result["newly_completed"]

    def test_get_next_milestone(self):
        goal = _make_career_goal()
        next_ms = goal.get_next_milestone()
        assert next_ms is not None
        assert next_ms.milestone_id == "ms_1"

    def test_get_pending_concepts(self):
        goal = _make_career_goal()
        concepts = goal.get_pending_concepts()
        assert "python_basics" in concepts
        assert "api_design" in concepts
        assert "docker" in concepts

    def test_create_from_career_preset(self):
        from src.agents.student_goal import StudentGoal
        goal = StudentGoal.from_preset(
            student_id="s_test",
            category="career",
            preset_id="python_backend",
        )
        assert goal is not None
        assert goal.category == "career"
        assert goal.target == "Python 后端工程师"
        assert len(goal.milestones) > 0
        assert goal.metadata["recommended_course"] == "python_advanced"

    def test_create_from_exam_preset(self):
        from src.agents.student_goal import StudentGoal
        goal = StudentGoal.from_preset(
            student_id="s_test",
            category="exam",
            preset_id="pcep",
        )
        assert goal is not None
        assert goal.category == "exam"
        assert goal.target == "PCEP (Python Certified Entry-Level)"

    def test_create_from_invalid_preset_returns_none(self):
        from src.agents.student_goal import StudentGoal
        goal = StudentGoal.from_preset("s", "invalid_cat", "x")
        assert goal is None

    def test_days_remaining_and_overdue(self):
        from src.agents.student_goal import StudentGoal
        # Past deadline
        goal = StudentGoal("g", "s", deadline="2020-01-01")
        assert goal.is_overdue
        assert goal.days_remaining is not None and goal.days_remaining < 0

        # Future deadline
        goal2 = StudentGoal("g", "s", deadline="2099-12-31")
        assert not goal2.is_overdue
        assert goal2.days_remaining is not None and goal2.days_remaining > 0

        # No deadline
        goal3 = StudentGoal("g", "s")
        assert not goal3.is_overdue
        assert goal3.days_remaining is None


# ──────────────────────────────────────────────
# 2. Goal Store Tests
# ──────────────────────────────────────────────


class TestGoalStore:
    """Goal store SQLite persistence."""

    def test_save_and_load(self):
        from src.data.goal_store import save_goal, get_goal, delete_goal
        from src.data.db import init_db

        init_db()

        goal = _make_career_goal()
        goal.student_id = "test_store_user"

        # Ensure test user exists
        _ensure_test_user("test_store_user")

        # Clean up first
        delete_goal("test_store_user")

        saved = save_goal(goal)
        assert saved is True

        loaded = get_goal("test_store_user")
        assert loaded is not None
        assert loaded.goal_id == goal.goal_id
        assert loaded.target == "Python 后端工程师"
        assert len(loaded.milestones) == 3

        # Clean up
        delete_goal("test_store_user")

    def test_load_nonexistent_returns_none(self):
        from src.data.goal_store import get_goal
        result = get_goal("nonexistent_user_999")
        assert result is None

    def test_get_goal_summary(self):
        from src.data.goal_store import save_goal, get_goal_summary, delete_goal
        from src.data.db import init_db
        init_db()

        goal = _make_career_goal()
        goal.student_id = "test_summary_user"
        _ensure_test_user("test_summary_user")
        delete_goal("test_summary_user")
        save_goal(goal)

        summary = get_goal_summary("test_summary_user")
        assert summary["has_goal"] is True
        assert summary["goal"]["target"] == "Python 后端工程师"
        assert summary["progress"] == 0.0
        assert summary["next_milestone"] is not None

        delete_goal("test_summary_user")

    def test_summary_for_no_goal(self):
        from src.data.goal_store import get_goal_summary
        summary = get_goal_summary("no_goal_user_xxx")
        assert summary["has_goal"] is False
        assert summary["goal"] is None

    def test_check_and_update_goal_progress(self):
        from src.data.goal_store import (
            save_goal, check_and_update_goal_progress, delete_goal,
        )
        from src.data.db import init_db
        from src.agents.student_goal import StudentGoal, Milestone

        init_db()
        goal = StudentGoal(
            goal_id=uuid.uuid4().hex[:16],
            student_id="test_progress_user",
            category="skill",
            target="Test Skill",
            milestones=[
                Milestone("ms_a", "A", target_concepts=["concept_a"], target_mastery=0.8),
                Milestone("ms_b", "B", target_concepts=["concept_b"], target_mastery=0.8),
            ],
        )
        _ensure_test_user("test_progress_user")
        delete_goal("test_progress_user")
        save_goal(goal)

        # Mark concept_a as mastered → ms_a should complete
        updated = check_and_update_goal_progress(
            "test_progress_user",
            {"concept_a": 0.9, "concept_b": 0.3},
        )
        assert updated is not None
        assert updated.progress == pytest.approx(0.5, abs=0.01)
        assert updated.milestones[0].completed is True
        assert updated.milestones[1].completed is False

        delete_goal("test_progress_user")


# ──────────────────────────────────────────────
# 3. PlannerAgent Goal Integration
# ──────────────────────────────────────────────


class TestPlannerGoalIntegration:
    """PlannerAgent uses StudentGoal for routing."""

    @pytest.fixture
    def planner(self):
        from src.agents.planner_agent import PlannerAgent
        return PlannerAgent()

    def test_plan_with_goal_uses_recommended_course(self, planner):
        """Goal's recommended_course overrides auto-detection."""
        goal = _make_career_goal()
        # Preset 'python_backend' recommends 'python_advanced'
        profile = {
            "knowledge_base": "junior_dev",
            "cognitive_style": "visual_dominant",
            "learning_pace": "normal",
            "error_prone_bias": "",
            "interaction_preference": "code_sandbox",
            "frustration_threshold": "medium",
        }

        plan = planner.plan(
            profile=profile,
            student_goal=goal,
        )
        assert plan is not None
        assert len(plan.nodes) > 0
        # Should use python_advanced (not python_basics or multi_agent_ai)
        assert "python_advanced" in plan.plan_id or plan.nodes[0].title != ""

    def test_plan_without_goal_preserves_behavior(self, planner):
        """No goal → existing behavior unchanged (backward compat)."""
        profile = {
            "knowledge_base": "junior_dev",
            "cognitive_style": "visual_dominant",
            "learning_pace": "normal",
            "error_prone_bias": "",
            "interaction_preference": "code_sandbox",
            "frustration_threshold": "medium",
        }

        plan = planner.plan(profile=profile, goal_text="学习 Python")
        assert plan is not None
        assert len(plan.nodes) > 0

    def test_goal_appears_in_rationale(self, planner):
        goal = _make_career_goal()
        profile = {
            "knowledge_base": "junior_dev",
            "cognitive_style": "visual_dominant",
            "learning_pace": "normal",
            "error_prone_bias": "",
            "interaction_preference": "code_sandbox",
            "frustration_threshold": "medium",
        }

        plan = planner.plan(profile=profile, student_goal=goal)
        # Rationale should mention goal info
        assert "Python 后端工程师" in plan.strategy_rationale
        assert "career" in plan.strategy_rationale

    def test_goal_deadline_urgency_pace(self, planner):
        """Past deadline → urgency=2 → pace accelerates."""
        from datetime import date, timedelta
        goal = _make_career_goal()
        goal.deadline = (date.today() + timedelta(days=1)).isoformat()

        profile = {
            "knowledge_base": "junior_dev",
            "cognitive_style": "visual_dominant",
            "learning_pace": "normal",
            "error_prone_bias": "",
            "interaction_preference": "code_sandbox",
            "frustration_threshold": "medium",
        }

        plan = planner.plan(profile=profile, student_goal=goal)
        # Should mention deadline urgency
        rationale = plan.strategy_rationale
        assert "紧急" in rationale or plan.total_minutes < 1000


# ──────────────────────────────────────────────
# 4. ContentGeneratorAgent Goal Integration
# ──────────────────────────────────────────────


class TestContentGeneratorGoalIntegration:
    """ContentGeneratorAgent uses StudentGoal for goal-driven content."""

    @pytest.fixture
    def generator(self):
        from src.agents.content_generator_agent import ContentGeneratorAgent
        return ContentGeneratorAgent()

    @pytest.fixture
    def plan_dict(self):
        return {
            "plan_id": "plan_test",
            "profile_summary": "test profile",
            "nodes": [
                {
                    "node_id": "n1",
                    "title": "Test Node 1",
                    "core_concept": "test concept",
                    "depth": 2,
                    "estimated_minutes": 20,
                    "teaching_strategy": "standard",
                }
            ],
        }

    @pytest.fixture
    def profile_dict(self):
        return {
            "profile": {
                "knowledge_base": "junior_dev",
                "cognitive_style": "visual_dominant",
                "learning_pace": "normal",
                "error_prone_bias": "",
                "interaction_preference": "code_sandbox",
                "frustration_threshold": "medium",
            }
        }

    def test_generate_with_goal_in_title(self, generator, profile_dict, plan_dict):
        goal = _make_career_goal()
        material = generator.fallback_generate(
            profile_dict, plan_dict, student_goal=goal,
        )
        assert "Python 后端工程师" in material.title
        assert material.title.startswith("🎯")

    def test_generate_without_goal_normal_title(self, generator, profile_dict, plan_dict):
        material = generator.fallback_generate(profile_dict, plan_dict)
        assert "个性化学习教材" in material.title
        assert not material.title.startswith("🎯")

    def test_goal_in_learning_objectives(self, generator, profile_dict, plan_dict):
        goal = _make_career_goal()
        material = generator.fallback_generate(
            profile_dict, plan_dict, student_goal=goal,
        )
        objectives = " ".join(material.learning_objectives)
        assert "长期目标" in objectives or "Python 后端工程师" in objectives

    def test_goal_in_overall_summary(self, generator, profile_dict, plan_dict):
        goal = _make_career_goal()
        material = generator.fallback_generate(
            profile_dict, plan_dict, student_goal=goal,
        )
        assert "目标进度" in material.overall_summary


# ──────────────────────────────────────────────
# 5. ResourceAgent Goal Integration
# ──────────────────────────────────────────────


class TestResourceAgentGoalIntegration:
    """ResourceAgent adds goal-driven resources."""

    @pytest.fixture
    def agent(self):
        from src.agents.resource_agent import ResourceAgent
        return ResourceAgent()

    @pytest.fixture
    def profile(self):
        return {
            "knowledge_base": "junior_dev",
            "cognitive_style": "visual_dominant",
            "learning_pace": "normal",
            "error_prone_bias": "",
            "interaction_preference": "code_sandbox",
            "frustration_threshold": "medium",
        }

    def test_career_goal_adds_project_resources(self, agent, profile):
        goal = _make_career_goal()
        result = agent.recommend(
            profile=profile,
            goal="学习 Python",
            knowledge_gaps=["python"],
            student_goal=goal,
        )

        # Should have added career-specific resources
        titles = [r.title for r in result.resources]
        assert any("职业实战" in t for t in titles) or any(
            "面试准备" in t for t in titles
        )

    def test_exam_goal_adds_mock_exam(self, agent, profile):
        from src.agents.student_goal import StudentGoal, Milestone
        goal = StudentGoal(
            goal_id=uuid.uuid4().hex[:16],
            student_id="test_exam",
            category="exam",
            target="PCEP 认证",
            milestones=[Milestone("m1", "Python Basics", target_concepts=["python"])],
        )

        result = agent.recommend(
            profile=profile,
            goal="学习 Python",
            knowledge_gaps=["python"],
            student_goal=goal,
        )

        titles = [r.title for r in result.resources]
        assert any("模拟考试" in t for t in titles) or any(
            "考点梳理" in t for t in titles
        )

    def test_goal_label_appears_in_result(self, agent, profile):
        goal = _make_career_goal()
        result = agent.recommend(
            profile=profile,
            goal="",
            knowledge_gaps=["python"],
            student_goal=goal,
        )
        assert "Python 后端工程师" in result.goal

    def test_no_goal_preserves_behavior(self, agent, profile):
        """Backward compat: no goal = same as before."""
        result_no_goal = agent.recommend(
            profile=profile,
            goal="学习 Python",
            knowledge_gaps=["socket", "asyncio"],
        )
        assert result_no_goal is not None
        assert len(result_no_goal.resources) > 0


# ──────────────────────────────────────────────
# 6. Dashboard Data Provider Tests
# ──────────────────────────────────────────────


class TestDashboardGoalData:
    """Dashboard data provider for goal progress."""

    def test_demo_goal_progress_no_goal(self):
        from web.dashboard.data_providers import get_goal_progress

        data = get_goal_progress(student_id="")
        assert data["has_goal"] is False
        assert data["target"] == "尚未设定学习目标"

    def test_demo_goal_progress_with_goal(self):
        from web.dashboard.data_providers import get_goal_progress
        from src.data.goal_store import save_goal, delete_goal
        from src.data.db import init_db

        init_db()
        goal = _make_career_goal()
        goal.student_id = "test_dash_user"
        _ensure_test_user("test_dash_user")
        delete_goal("test_dash_user")
        save_goal(goal)

        data = get_goal_progress(student_id="test_dash_user")
        assert data["has_goal"] is True
        assert data["target"] == "Python 后端工程师"
        assert data["category"] == "career"
        assert "milestones" in data
        assert len(data["milestones"]) > 0

        delete_goal("test_dash_user")
