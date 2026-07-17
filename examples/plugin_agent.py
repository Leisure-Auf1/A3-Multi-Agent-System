#!/usr/bin/env python3
"""
Plugin Agent — Veritas Runtime Example

Shows how to create and install a custom RuntimePlugin that monitors
agent execution. Demonstrates the full plugin lifecycle.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.runtime import RuntimeEngine, TransitionTable, AgentState, RuntimePolicyEngine
from src.runtime.plugins import RuntimePlugin, PluginManager
from src.runtime.recovery import RecoveryManager


# ── Custom Plugin ───────────────────────────

class AuditPlugin(RuntimePlugin):
    """Logs every state transition with timing."""

    name = "audit_logger"
    version = "1.0.0"
    priority = 10

    transitions = []

    def on_start(self):
        print(f"[AuditPlugin] Started — monitoring transitions")

    def after_transition(self, engine, from_s, to_s, ctx, transition):
        self.transitions.append({
            "from": from_s.name,
            "to": to_s.name,
            "status": transition.status,
            "duration_ms": transition.duration_ms,
        })
        print(f"[AuditPlugin] {from_s.name} → {to_s.name} "
              f"({transition.status}, {transition.duration_ms:.1f}ms)")

    def on_error(self, engine, state, ctx, error):
        print(f"[AuditPlugin] ❌ Error at {state.name}: {error}")


class MetricsPlugin(RuntimePlugin):
    """Collects basic metrics during execution."""

    name = "metrics_collector"
    version = "1.0.0"

    total_transitions = 0
    error_count = 0

    def after_transition(self, engine, from_s, to_s, ctx, transition):
        self.total_transitions += 1
        if transition.status == "error":
            self.error_count += 1

    def on_run_end(self, engine, ctx, total_duration_ms):
        error_rate = (self.error_count / max(self.total_transitions, 1)) * 100
        print(f"[Metrics] {self.total_transitions} transitions, "
              f"{self.error_count} errors ({error_rate:.1f}%)")


# ── Main ─────────────────────────────────────

def main():
    print("=" * 50)
    print("  Veritas Plugin Agent Example")
    print("=" * 50)
    print()

    # Set up Plugin Manager
    mgr = PluginManager()
    audit = mgr.install(AuditPlugin())
    metrics = mgr.install(MetricsPlugin())

    # Build engine with recovery
    engine = RuntimeEngine(
        session_id="plugin_demo",
        policy_engine=RuntimePolicyEngine(),
        recovery_manager=RecoveryManager(),
    )

    # Initialize plugins with the engine
    print("▶ Initializing plugins...")
    mgr.initialize_all(engine)

    # Start plugins
    print("▶ Starting plugins...")
    mgr.start_all()

    # Hook bridge into engine — one line, all plugins receive events
    engine.add_hook(mgr.bridge)

    # Setup state handlers
    table = TransitionTable(custom={
        AgentState.INIT: AgentState.PROFILE,
        AgentState.PROFILE: AgentState.EXECUTE,
        AgentState.EXECUTE: AgentState.DONE,
    })
    engine._table = table

    def profile_handler(ctx):
        ctx.profile = {"knowledge_base": "expert"}
        print("  [Handler] Profile extracted")

    def execute_handler(ctx):
        ctx.resources = [{"type": "document", "title": "Plugin Guide"}]
        print("  [Handler] Resources generated")

    engine.register_handler(AgentState.PROFILE, profile_handler)
    engine.register_handler(AgentState.EXECUTE, execute_handler)

    # Run
    print("▶ Running engine...")
    print()
    engine.run()

    # Results
    print()
    print("=" * 50)
    print("  Results")
    print("=" * 50)
    print(f"  AuditPlugin transitions: {len(audit.transitions)}")
    print(f"  MetricsPlugin: {metrics.total_transitions} total, "
          f"{metrics.error_count} errors")
    print(f"  Plugin summary: {mgr.summary()}")

    # Cleanup
    mgr.stop_all()
    print(f"  Plugins stopped. Active: {mgr.summary()['started']}")


if __name__ == "__main__":
    main()
