#!/usr/bin/env python3
"""
Recovery Demo — Veritas Showcase

Demonstrates the full recovery pipeline:
  1. Agent fails (AGENT_EXCEPTION)
  2. PolicyEngine detects failure → RETRY
  3. RecoveryManager executes retry with backoff
  4. Agent recovers on second attempt
  5. Lifecycle tracks FAILED → RECOVERING → READY

Also shows what happens WITHOUT recovery (baseline comparison).
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.runtime import (
    RuntimeEngine, RuntimeContext, AgentState, TransitionTable,
    RuntimePolicyEngine,
)
from src.runtime.recovery import RecoveryManager, RecoveryConfig
from src.runtime.lifecycle import LifecycleManager
from src.benchmark import FailureScenario, FailureInjector


def run_with(label, with_recovery):
    """Run a single scenario and return success + timeline."""
    print(f"\n  ▸ {label}")
    print(f"    Recovery: {'ON' if with_recovery else 'OFF'}")

    lm = LifecycleManager()
    recovery = RecoveryManager(RecoveryConfig(max_retries=3)) if with_recovery else None
    policy = RuntimePolicyEngine() if with_recovery else None

    engine = RuntimeEngine(
        session_id=f"recovery_{label.lower().replace(' ', '_')}",
        policy_engine=policy,
        recovery_manager=recovery,
    )
    engine.add_hook(lm)

    table = TransitionTable(custom={
        AgentState.INIT: AgentState.PROFILE,
        AgentState.PROFILE: AgentState.DONE,
    })
    engine._table = table

    # Inject a failure that fails on first attempt, succeeds on retry
    injector = FailureInjector()
    attempts = []

    def flaky_handler(ctx):
        attempts.append(1)
        if len(attempts) == 1:
            raise RuntimeError("Simulated runtime error — should trigger recovery")

    wrapped = injector.wrap("profile", flaky_handler, FailureScenario.AGENT_EXCEPTION)
    engine.register_handler(AgentState.PROFILE, wrapped)

    t0 = time.time()
    engine.run()
    elapsed = (time.time() - t0) * 1000

    success = engine._checkpoint.error_count() == 0 or (
        recovery and any(r.success for r in recovery.history)
    )

    return {
        "label": label,
        "success": success,
        "elapsed_ms": elapsed,
        "attempts": len(attempts),
        "recovery_used": recovery is not None and len(recovery.history) > 0,
        "lifecycle": lm.agent_states,
    }


def main():
    print("=" * 60)
    print("  Veritas Recovery Showcase")
    print("  Failure → Detection → Retry → Recovery")
    print("=" * 60)

    # ── Scenario 1: WITHOUT recovery ──
    r1 = run_with("Baseline (no recovery)", with_recovery=False)

    # ── Scenario 2: WITH recovery ──
    r2 = run_with("Runtime (with recovery)", with_recovery=True)

    # ── Scenario 3: LLM Timeout ──
    print(f"\n  ▸ LLM Timeout Simulation")
    print(f"    Recovery: ON")
    recovery = RecoveryManager(RecoveryConfig(max_retries=2))
    lm = LifecycleManager()

    engine = RuntimeEngine(
        session_id="recovery_timeout",
        policy_engine=RuntimePolicyEngine(),
        recovery_manager=recovery,
    )
    engine.add_hook(lm)

    table = TransitionTable(custom={
        AgentState.INIT: AgentState.PROFILE,
        AgentState.PROFILE: AgentState.DONE,
    })
    engine._table = table

    timeout_attempts = []
    def timeout_handler(ctx):
        timeout_attempts.append(1)
        if len(timeout_attempts) == 1:
            raise TimeoutError("LLM request timed out after 30s")

    injector = FailureInjector()
    wrapped = injector.wrap("profile", timeout_handler, FailureScenario.LLM_TIMEOUT)
    engine.register_handler(AgentState.PROFILE, wrapped)
    engine.run()

    r3 = {
        "success": any(r.success for r in recovery.history),
        "attempts": len(timeout_attempts),
        "recoveries": len(recovery.history),
    }

    # ── Results ──
    print()
    print("=" * 60)
    print("  Recovery Report")
    print("=" * 60)

    for r in [r1, r2]:
        status_icon = "✅" if r["success"] else "❌"
        rec = "✓" if r.get("recovery_used") else "✗"
        print(f"\n  {r['label']}:")
        print(f"    Status:     {status_icon} {'SUCCESS' if r['success'] else 'FAILED'}")
        print(f"    Attempts:   {r['attempts']}")
        print(f"    Time:       {r['elapsed_ms']:.1f}ms")
        print(f"    Recovery:   {rec}")
        print(f"    Lifecycle:  {r.get('lifecycle', {})}")

    print(f"\n  LLM Timeout:")
    print(f"    Status:     {'✅ SUCCESS' if r3['success'] else '❌ FAILED'}")
    print(f"    Attempts:   {r3['attempts']}")
    print(f"    Recoveries: {r3['recoveries']}")

    # ── Summary ──
    print()
    print("=" * 60)
    improvement = "100%" if r1["success"] == False and r2["success"] == True else "—"
    print(f"  Recovery Improvement: +{improvement}")
    print(f"  Without recovery: {'FAILED' if not r1['success'] else 'PASSED'}")
    print(f"  With recovery:    {'PASSED' if r2['success'] else 'FAILED'}")
    print()
    print("✅ Recovery pipeline: Detect → Retry → Recover → Continue")


if __name__ == "__main__":
    main()
