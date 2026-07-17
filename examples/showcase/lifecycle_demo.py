#!/usr/bin/env python3
"""
Lifecycle Demo — Veritas Showcase

Shows how LifecycleManager tracks every agent through its state:
  READY → RUNNING → (FAILED → RECOVERING → READY) → TERMINATED
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from veritas.runtime import (
    RuntimeEngine, RuntimeContext, AgentState, TransitionTable,
    RuntimePolicyEngine,
)
from veritas.runtime.recovery import RecoveryManager, RecoveryConfig
from veritas.runtime.lifecycle import LifecycleManager


def main():
    print("=" * 60)
    print("  Veritas Lifecycle Showcase")
    print("  Agent OS: Track every agent through its lifecycle")
    print("=" * 60)
    print()

    # ── Setup ──
    lm = LifecycleManager()
    recovery = RecoveryManager(RecoveryConfig(max_retries=2))

    engine = RuntimeEngine(
        session_id="showcase_lifecycle",
        policy_engine=RuntimePolicyEngine(),
        recovery_manager=recovery,
    )

    # Attach lifecycle via hook — zero engine changes
    engine.add_hook(lm)

    # Three agents: one succeeds, one fails+recovers, one always works
    attempts = {"flaky": 0}

    def good_handler(ctx):
        ctx.profile = {"agent": "good"}
        print("  [GoodAgent] ✓ succeeded")

    def flaky_handler(ctx):
        attempts["flaky"] += 1
        if attempts["flaky"] < 2:
            print(f"  [FlakyAgent] ✗ attempt {attempts['flaky']} failed")
            raise RuntimeError("transient error — should recover")
        ctx.learning_plan = {"nodes": [1, 2]}
        print(f"  [FlakyAgent] ✓ recovered on attempt {attempts['flaky']}")

    def reliable_handler(ctx):
        ctx.evaluation = {"score": 92}
        print("  [ReliableAgent] ✓ always works")

    table = TransitionTable(custom={
        AgentState.INIT: AgentState.PROFILE,
        AgentState.PROFILE: AgentState.PLAN,
        AgentState.PLAN: AgentState.EVALUATE,
        AgentState.EVALUATE: AgentState.DONE,
    })
    engine._table = table
    engine.register_handler(AgentState.PROFILE, good_handler)
    engine.register_handler(AgentState.PLAN, flaky_handler)
    engine.register_handler(AgentState.EVALUATE, reliable_handler)

    # ── Run ──
    print("▶ Running agents with lifecycle tracking...")
    print()
    engine.run()

    # ── Lifecycle Results ──
    print()
    print("=" * 60)
    print("  Agent Lifecycle Report")
    print("=" * 60)

    for name in ["profile", "plan", "evaluate"]:
        agent = lm.get_agent(name)
        if agent:
            print(f"\n  ▸ {name} ({agent.agent_name})")
            print(f"    Final state:  {agent.lifecycle.value}")
            print(f"    Errors:       {agent.error_count}")
            print(f"    Recoveries:   {agent.recovery_count}")
            print(f"    History:")
            for h in agent.history[-4:]:  # last 4 events
                print(f"      {h['from']} → {h['to']}: {h.get('detail', '')[:60]}")

    # Session summary
    print(f"\n  Session: {lm.session.session_id}")
    print(f"  Status:  {lm.session.final_status}")
    print(f"  Timeline: {' → '.join(lm.session.timeline())}")
    print()

    print("✅ Lifecycle tracking complete")
    print(f"   All agents tracked through their full lifecycle")
    print(f"   FlakyAgent recovered: {attempts['flaky'] > 1}")


if __name__ == "__main__":
    main()
