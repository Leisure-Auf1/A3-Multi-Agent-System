#!/usr/bin/env python3
"""
Plugin Demo — Veritas Showcase

Creates and installs 3 custom plugins that extend the RuntimeEngine
without modifying any core code:

  SecurityPlugin  — audits every transition
  MetricsPlugin   — collects timing stats
  AlertPlugin     — fires on errors
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.runtime import (
    RuntimeEngine, RuntimeContext, AgentState, TransitionTable,
    RuntimePolicyEngine,
)
from src.runtime.plugins import RuntimePlugin, PluginManager


# ── Plugin 1: Security Audit ────────────────

class SecurityPlugin(RuntimePlugin):
    """Audits every state transition."""
    name = "security_audit"
    version = "1.0.0"
    priority = 10
    audit_log = []

    def on_start(self):
        print("  [SecurityPlugin] 🔒 Audit active")

    def after_transition(self, engine, from_s, to_s, ctx, transition):
        entry = f"AUDIT: {from_s.name} → {to_s.name} | {transition.status}"
        self.audit_log.append(entry)

    def on_run_end(self, engine, ctx, duration_ms):
        print(f"  [SecurityPlugin] 🔒 Audited {len(self.audit_log)} transitions")


# ── Plugin 2: Metrics ────────────────────────

class MetricsPlugin(RuntimePlugin):
    """Collects execution metrics."""
    name = "metrics_collector"
    version = "1.0.0"

    total_time = 0.0
    transition_count = 0
    error_count = 0

    def after_transition(self, engine, from_s, to_s, ctx, transition):
        self.total_time += transition.duration_ms
        self.transition_count += 1
        if transition.status == "error":
            self.error_count += 1

    def on_run_end(self, engine, ctx, duration_ms):
        avg = self.total_time / max(self.transition_count, 1)
        print(f"  [MetricsPlugin] 📊 {self.transition_count} transitions, "
              f"avg {avg:.1f}ms, {self.error_count} errors")


# ── Plugin 3: Alert ─────────────────────────

class AlertPlugin(RuntimePlugin):
    """Fires alerts on errors."""
    name = "alert_system"
    version = "1.0.0"
    alerts = []

    def on_error(self, engine, state, ctx, error):
        alert = f"🚨 ALERT: Error at {state.label}: {error[:80]}"
        self.alerts.append(alert)

    def on_run_end(self, engine, ctx, duration_ms):
        if self.alerts:
            print(f"  [AlertPlugin] 🚨 {len(self.alerts)} alerts fired")
        else:
            print(f"  [AlertPlugin] ✅ No alerts")


# ── Main ─────────────────────────────────────

def main():
    print("=" * 60)
    print("  Veritas Plugin Showcase")
    print("  3 Plugins: Security + Metrics + Alert")
    print("=" * 60)
    print()

    # ── Plugin Manager ──
    mgr = PluginManager()
    security = mgr.install(SecurityPlugin())  # type: ignore
    metrics = mgr.install(MetricsPlugin())    # type: ignore
    alert = mgr.install(AlertPlugin())        # type: ignore

    # ── Engine ──
    engine = RuntimeEngine(
        session_id="showcase_plugins",
        policy_engine=RuntimePolicyEngine(),
    )
    mgr.initialize_all(engine)
    mgr.start_all()

    # ONE LINE to hook all plugins into the engine
    engine.add_hook(mgr.bridge)

    # ── Handlers ──
    table = TransitionTable(custom={
        AgentState.INIT: AgentState.PROFILE,
        AgentState.PROFILE: AgentState.PLAN,
        AgentState.PLAN: AgentState.EVALUATE,
        AgentState.EVALUATE: AgentState.DONE,
    })
    engine._table = table

    def good(ctx): ctx.profile = {"ok": True}
    def bad(ctx): raise RuntimeError("injected failure for demo")
    def recover(ctx): ctx.evaluation = {"score": 80}

    engine.register_handler(AgentState.PROFILE, good)
    engine.register_handler(AgentState.PLAN, bad)
    engine.register_handler(AgentState.EVALUATE, recover)

    # ── Run ──
    print("▶ Running with 3 plugins...")
    print()
    engine.run()

    # ── Results ──
    print()
    print("=" * 60)
    print("  Plugin Results")
    print("=" * 60)
    print(f"  SecurityPlugin: {len(security.audit_log)} audit entries")  # type: ignore
    print(f"  MetricsPlugin:  {metrics.transition_count} transitions, "  # type: ignore
          f"{metrics.error_count} errors")
    print(f"  AlertPlugin:    {len(alert.alerts)} alerts")  # type: ignore
    if alert.alerts:  # type: ignore
        for a in alert.alerts:  # type: ignore
            print(f"    {a}")

    print(f"\n  Plugin Manager summary:")
    for p in mgr.list_plugins():
        print(f"    {p['name']} v{p['version']} | {p['state']} | priority={p['priority']}")

    print()
    print("✅ 3 plugins installed, monitored, zero engine changes")


if __name__ == "__main__":
    main()
