#!/usr/bin/env python3
"""
Multi-Agent Demo — Veritas Showcase

Demonstrates a full 3-agent pipeline:
  ProfileAgent → PlannerAgent → EvaluatorAgent

All agents run through the RuntimeEngine state machine with
hooks observing every transition. Zero direct RuntimeEngine
access from the agent layer.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.runtime import (
    RuntimeEngine, RuntimeContext, AgentState, TransitionTable,
    RuntimeHook, RuntimePolicyEngine,
)
from src.runtime.recovery import RecoveryManager


# ── Agent Implementations ──────────────────

class ProfileAgent:
    """Extracts user knowledge profile."""
    @staticmethod
    def execute(ctx: RuntimeContext):
        ctx.profile = {
            "knowledge_base": "intermediate",
            "cognitive_style": "visual_dominant",
            "learning_pace": "fast_track",
            "interaction_preference": "code_sandbox",
        }
        print(f"  [ProfileAgent] → {ctx.profile['knowledge_base']}, "
              f"{ctx.profile['cognitive_style']}")


class PlannerAgent:
    """Generates a learning plan."""
    @staticmethod
    def execute(ctx: RuntimeContext):
        level = ctx.profile.get("knowledge_base", "beginner")
        ctx.learning_plan = {
            "nodes": [
                {"topic": "Python Basics", "duration": 2},
                {"topic": "Data Structures", "duration": 3},
                {"topic": "Algorithms", "duration": 4},
            ],
            "strategy": f"Progressive for {level} level",
        }
        print(f"  [PlannerAgent] → {len(ctx.learning_plan['nodes'])} nodes")


class EvaluatorAgent:
    """Evaluates plan quality."""
    @staticmethod
    def execute(ctx: RuntimeContext):
        node_count = len(ctx.learning_plan.get("nodes", []))
        score = min(100, node_count * 25 + 30)
        ctx.evaluation = {
            "score": score,
            "issues": [],
            "verdict": "ready" if score >= 70 else "needs_revision",
        }
        print(f"  [EvaluatorAgent] → score={score}, {ctx.evaluation['verdict']}")


# ── Observer Hook ──────────────────────────

class ShowcaseObserver(RuntimeHook):
    """Observes and prints the agent pipeline."""
    timeline = []

    def after_transition(self, engine, from_s, to_s, ctx, transition):
        self.timeline.append({
            "from": from_s.name,
            "to": to_s.name,
            "duration_ms": transition.duration_ms,
            "status": transition.status,
        })
        print(f"  ⚡ {from_s.name} → {to_s.name} "
              f"({transition.status}, {transition.duration_ms:.1f}ms)")


# ── Main ────────────────────────────────────

def main():
    print("=" * 60)
    print("  Veritas Multi-Agent Showcase")
    print("  3-Agent Pipeline: Profile → Plan → Evaluate")
    print("=" * 60)
    print()

    # Build Runtime with full stack
    engine = RuntimeEngine(
        session_id="showcase_multiagent",
        policy_engine=RuntimePolicyEngine(),
        recovery_manager=RecoveryManager(),
    )

    # Custom transition table
    table = TransitionTable(custom={
        AgentState.INIT: AgentState.PROFILE,
        AgentState.PROFILE: AgentState.PLAN,
        AgentState.PLAN: AgentState.EVALUATE,
        AgentState.EVALUATE: AgentState.DONE,
    })
    engine._table = table

    # Register handlers
    engine.register_handler(AgentState.PROFILE, ProfileAgent.execute)
    engine.register_handler(AgentState.PLAN, PlannerAgent.execute)
    engine.register_handler(AgentState.EVALUATE, EvaluatorAgent.execute)

    # Hook observer
    observer = ShowcaseObserver()
    engine.add_hook(observer)

    # Execute
    print("▶ Running 3-agent pipeline...")
    print()
    ctx = engine.run()

    # Results
    print()
    print("=" * 60)
    print("  Results")
    print("=" * 60)
    print(f"  Profile:     {ctx.profile}")
    print(f"  Plan nodes:  {len(ctx.learning_plan.get('nodes', []))}")
    print(f"  Evaluation:  score={ctx.evaluation['score']}, "
          f"verdict={ctx.evaluation['verdict']}")
    print(f"  Timeline:    {' → '.join(t['to'] for t in observer.timeline)}")
    print(f"  Total states: {engine._checkpoint.state_count()}")
    print(f"  Errors:      {len(ctx.errors)}")
    print()
    print("✅ Multi-agent pipeline complete")


if __name__ == "__main__":
    main()
