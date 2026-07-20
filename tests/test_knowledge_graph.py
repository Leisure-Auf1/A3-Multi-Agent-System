"""
Tests for Phase 8.3-D1 — Knowledge Graph Integration.

Covers:
- Default KG builds correctly (nodes, edges, prerequisites)
- Bridge: plan ordering via topological sort
- Bridge: gap analysis for missing prerequisites
- PlannerAgent with KG: topological ordering
- PlannerAgent with KG: skip mastered, boost weak
- ErrorAnalysis with KG enrichment
- KG + mastery integration
- Fallback when KG not available
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


# --- Fixtures ---

@pytest.fixture
def default_kg():
    from src.knowledge_graph.bridge import get_default_kg
    return get_default_kg()


@pytest.fixture
def planner_agent():
    from src.agents.planner_agent import PlannerAgent
    return PlannerAgent()


@pytest.fixture
def eval_agent():
    from src.agents.evaluation_agent import EvaluationAgent
    return EvaluationAgent()


# --- Test: Default KG ---


class TestDefaultKG:
    """Default Knowledge Graph builds correctly."""

    def test_kg_has_nodes(self, default_kg):
        assert default_kg.node_count > 0

    def test_kg_has_edges(self, default_kg):
        assert default_kg.edge_count > 0

    def test_kg_nodes_have_prerequisites(self, default_kg):
        """Some nodes should have prerequisite relationships."""
        # transformer node should exist and have prereqs
        preqs = default_kg.get_all_prerequisites("kg:ch2:transformer")
        assert len(preqs) > 0

    def test_kg_topological_order_is_dag(self, default_kg):
        """Topological sort should produce valid ordering."""
        order = default_kg.topological_order()
        assert len(order) > 0
        # Prerequisites should come before dependents
        for node_id in order:
            prereqs = default_kg.get_all_prerequisites(node_id)
            for p in prereqs:
                if p in order:
                    assert order.index(p) < order.index(node_id), \
                        f"Prereq {p} must come before {node_id}"

    def test_kg_transitive_prerequisites(self, default_kg):
        """Transitive prerequisites include indirect dependencies."""
        # transformer requires attention, which requires linear_algebra
        all_preqs = default_kg.get_all_prerequisites("kg:ch2:transformer")
        # linear_algebra should be in transitive prereqs
        assert "kg:ch2:linear_algebra" in all_preqs
        assert "kg:ch2:attention" in all_preqs


# --- Test: Bridge functions ---


class TestBridge:
    """Bridge functions for plan ordering and gap analysis."""

    def test_compute_gap_no_mastery(self, default_kg):
        """Gap analysis with empty mastery finds all prerequisites as missing."""
        from src.knowledge_graph.bridge import compute_gap_for_concept
        gap = compute_gap_for_concept(default_kg, "kg:ch2:transformer", {})

        # Without any mastery, all prereqs should be missing
        assert len(gap.missing_prerequisites) > 0
        assert "kg:ch2:linear_algebra" in gap.missing_prerequisites

    def test_compute_gap_with_mastery(self, default_kg):
        """Gap analysis with mastered prerequisites."""
        from src.knowledge_graph.bridge import compute_gap_for_concept
        mastery = {"kg:ch2:linear_algebra": 0.9, "kg:ch2:attention": 0.9}

        gap = compute_gap_for_concept(default_kg, "kg:ch2:transformer", mastery)

        # All prereqs mastered → no missing
        assert len(gap.missing_prerequisites) == 0

    def test_compute_gap_with_weak(self, default_kg):
        """Gap analysis with weak prerequisites."""
        from src.knowledge_graph.bridge import compute_gap_for_concept
        mastery = {"kg:ch2:linear_algebra": 0.5, "kg:ch2:attention": 0.4}

        gap = compute_gap_for_concept(default_kg, "kg:ch2:transformer", mastery)

        # Both should be weak (0.3-0.8 range)
        assert len(gap.weak_concepts) >= 1
        # Recommended sequence should put missing/weak before target
        assert "kg:ch2:transformer" in gap.recommended_sequence
        assert gap.recommended_sequence[-1] == "kg:ch2:transformer"

    def test_compute_plan_order_skips_mastered(self, default_kg):
        """Optimal path skips fully mastered nodes."""
        from src.knowledge_graph.bridge import compute_plan_order
        mastery = {
            "kg:ch2:linear_algebra": 0.95,
            "kg:ch2:attention": 0.9,
            "kg:ch2:tokenization": 0.85,
            "kg:ch2:transformer": 0.5,
        }
        concept_ids = ["kg:ch2:linear_algebra", "kg:ch2:attention",
                       "kg:ch2:tokenization", "kg:ch2:transformer"]

        path = compute_plan_order(default_kg, concept_ids, mastery)

        # Mastered nodes should be skipped
        assert "kg:ch2:linear_algebra" in path.skipped_nodes
        assert "kg:ch2:attention" in path.skipped_nodes

    def test_map_error_to_prerequisites(self, default_kg):
        """Map a wrong answer to missing prerequisites."""
        from src.knowledge_graph.bridge import map_error_to_prerequisites
        mastery = {"kg:ch2:linear_algebra": 0.0, "kg:ch2:attention": 0.6}

        result = map_error_to_prerequisites(
            default_kg, "kg:ch2:transformer", mastery
        )

        assert "missing_prerequisites" in result
        assert "kg:ch2:linear_algebra" in result["missing_prerequisites"]


# --- Test: PlannerAgent with KG ---


class TestPlannerWithKG:
    """PlannerAgent integrates with Knowledge Graph."""

    def test_planner_with_kg_produces_valid_plan(self, planner_agent, default_kg):
        """Planner with KG produces a valid LearningPlan."""
        from src.core.agent_router import DynamicProfile
        profile = DynamicProfile(knowledge_base="junior_dev")

        plan = planner_agent.plan(
            profile, course_id="multi_agent_ai", knowledge_graph=default_kg
        )

        assert len(plan.nodes) > 0
        assert plan.total_minutes > 0
        assert plan.plan_id

    def test_planner_with_kg_respects_topological_order(self, planner_agent, default_kg):
        """KG planner orders nodes respecting prerequisites."""
        from src.core.agent_router import DynamicProfile
        profile = DynamicProfile(knowledge_base="junior_dev")

        plan = planner_agent.plan(
            profile, course_id="multi_agent_ai", knowledge_graph=default_kg
        )

        # Nodes should be in dependency order
        node_ids = [n.node_id for n in plan.nodes]
        # llm_basics should come before agent_loop (which depends on prompt_engineering)
        if "llm_basics" in node_ids and "agent_loop" in node_ids:
            assert node_ids.index("llm_basics") < node_ids.index("agent_loop"), \
                "llm_basics must come before agent_loop"

    def test_planner_without_kg_still_works(self, planner_agent):
        """Planner without KG falls back to original behavior."""
        from src.core.agent_router import DynamicProfile
        profile = DynamicProfile(knowledge_base="junior_dev")

        plan = planner_agent.plan(profile, course_id="python_basics")

        assert len(plan.nodes) > 0
        assert plan.total_minutes > 0

    def test_planner_with_kg_and_mastery(self, planner_agent, default_kg):
        """Planner with KG + mastery_map skips mastered nodes."""
        from src.core.agent_router import DynamicProfile

        # Simulate StudentMemory with high mastery
        class HighMasteryMem:
            mastery_map = {
                "llm_basics": 0.9,
                "prompt_engineering": 0.85,
            }
            weak_points = []

        profile = DynamicProfile(knowledge_base="mid_level")
        plan = planner_agent.plan(
            profile,
            course_id="multi_agent_ai",
            student_memory=HighMasteryMem(),
            knowledge_graph=default_kg,
        )

        node_ids = [n.node_id for n in plan.nodes]
        # Mastered nodes should be skipped
        assert "llm_basics" not in node_ids

    def test_planner_with_kg_boosts_weak(self, planner_agent, default_kg):
        """Planner with KG boosts weak nodes."""
        from src.core.agent_router import DynamicProfile

        class WeakMasteryMem:
            mastery_map = {"llm_basics": 0.25, "prompt_engineering": 0.3}
            weak_points = [{"concept": "llm_basics"}]

        profile = DynamicProfile(knowledge_base="junior_dev")
        plan = planner_agent.plan(
            profile,
            course_id="multi_agent_ai",
            student_memory=WeakMasteryMem(),
            knowledge_graph=default_kg,
        )

        for node in plan.nodes:
            if node.node_id in ("llm_basics", "prompt_engineering"):
                # Weak nodes should get extra depth
                assert node.depth >= 2


# --- Test: ErrorAnalysis with KG ---


class TestErrorAnalysisWithKG:
    """ErrorAnalysis enriched with KG gap analysis."""

    def test_with_kg_adds_missing_prerequisites(self, eval_agent, default_kg):
        """KG analysis adds missing prerequisites to related_concepts."""
        mastery = {"kg:ch2:linear_algebra": 0.1, "kg:ch2:attention": 0.5}

        analysis = eval_agent.analyze_wrong_answer_with_kg(
            question="How does Transformer work?",
            student_answer="It works with simple pattern matching",
            correct_answer="It uses self-attention to compute weighted token representations",
            question_id="kg:ch2:transformer",
            knowledge_graph=default_kg,
            mastery_map=mastery,
        )

        # Should have added linear_algebra as a missing prerequisite
        assert len(analysis.related_concepts) > 0

    def test_with_kg_enhances_recovery_plan(self, eval_agent, default_kg):
        """KG analysis enhances recovery plan with prerequisite info."""
        mastery = {"kg:ch2:linear_algebra": 0.0, "kg:ch2:attention": 0.6}

        analysis = eval_agent.analyze_wrong_answer_with_kg(
            question="How does Transformer work?",
            student_answer="It's just a bigger RNN",
            correct_answer="Transformer uses parallel self-attention, not recurrence",
            question_id="kg:ch2:transformer",
            knowledge_graph=default_kg,
            mastery_map=mastery,
        )

        # Recovery plan should be present and non-trivial
        assert len(analysis.recovery_plan) > 20
        # related_concepts should include missing prerequisites
        assert "kg:ch2:linear_algebra" in analysis.related_concepts

    def test_without_kg_still_works(self, eval_agent):
        """Error analysis without KG works as before."""
        analysis = eval_agent.analyze_wrong_answer_with_kg(
            question="What is Python?",
            student_answer="A snake",
            correct_answer="A programming language",
            question_id="q1",
        )

        assert isinstance(analysis, type(eval_agent.analyze_wrong_answer("", "", "")))
        assert analysis.generation_source == "rule"

    def test_with_kg_empty_mastery_ok(self, eval_agent, default_kg):
        """With KG but empty mastery, no crash."""
        analysis = eval_agent.analyze_wrong_answer_with_kg(
            question="What is attention?",
            student_answer="Looking at something",
            correct_answer="A mechanism for computing token relationships",
            question_id="kg:ch2:attention",
            knowledge_graph=default_kg,
            mastery_map={},
        )

        assert analysis is not None


# --- Test: Integration ---


class TestKGIntegration:
    """Full integration: KG + Planner + workflow."""

    def test_workflow_with_kg(self, default_kg):
        """A3Workflow with KG produces a plan respecting prerequisites."""
        from workflow import A3Workflow

        wf = A3Workflow(
            student_id="kg_test",
            knowledge_graph=default_kg,
        )
        result = wf.run(
            user_goal="Learn Multi-Agent AI",
            user_profile={"knowledge_base": "junior_dev"},
        )

        plan = result.learning_plan
        assert plan is not None
        node_count = len(plan.get("nodes", []))
        assert node_count > 0

    def test_kg_and_memory_together(self, default_kg):
        """KG + StudentMemory together produce adaptive plans."""
        from workflow import A3Workflow
        from veritas.memory import MemoryManager

        sid = "kg_memory_test"

        # Session 1: establish mastery
        wf1 = A3Workflow(student_id=sid, knowledge_graph=default_kg)
        wf1.run(user_goal="Learn AI basics", user_profile={"knowledge_base": "junior_dev"})

        # Session 2: should see accumulated mastery
        wf2 = A3Workflow(student_id=sid, knowledge_graph=default_kg)
        result = wf2.run(user_goal="Learn more AI", user_profile={"knowledge_base": "junior_dev"})

        assert result.learning_plan is not None
        # Memory should have accumulated
        mem = MemoryManager().get_student_memory(sid)
        assert mem is not None
        assert len(mem.session_summaries) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
