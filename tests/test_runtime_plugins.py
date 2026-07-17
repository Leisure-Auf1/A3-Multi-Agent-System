"""
Phase 5.8 — Runtime Plugin System Tests

Covers:
  1. PluginState: enum values, is_active, is_operational
  2. PluginMetadata: defaults, to_dict
  3. RuntimePlugin: lifecycle (initialize/start/stop/shutdown), state transitions
  4. RuntimePlugin: hook integration (is RuntimeHook)
  5. PluginRegistry: register, unregister, disable, enable
  6. PluginRegistry: query (get, list_all, list_by_tag, list_by_state, names)
  7. PluginRegistry: discover (dependencies), clear
  8. PluginLoader: load single plugin, load_all, errors
  9. PluginHookBridge: add/remove plugins, broadcast events
 10. PluginHookBridge: RuntimeHook interface relay
 11. PluginManager: install, remove
 12. PluginManager: lifecycle (initialize_all, start_all, stop_all, shutdown_all)
 13. PluginManager: disable/enable, summary
 14. Engine integration: plugin via bridge hook
 15. Engine integration: plugin lifecycle through manager
 16. Edge cases: duplicate registration, missing plugin, error isolation
 17. Backward compatibility
"""
from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from src.runtime import (
    AgentState,
    StateTransition,
    TransitionTable,
    RuntimeEngine,
    RuntimeContext,
    RuntimeHook,
    RuntimeEvent,
)
from src.runtime.plugins import (
    RuntimePlugin,
    PluginState,
    PluginMetadata,
    PluginRegistry,
    PluginLoader,
    PluginHookBridge,
    PluginManager,
    bridge_from_registry,
)


# ══════════════════════════════════════════════
# 1. PluginState
# ══════════════════════════════════════════════

class TestPluginState:
    def test_all_states(self):
        values = {s.value for s in PluginState}
        assert "unregistered" in values
        assert "installed" in values
        assert "started" in values
        assert "disabled" in values

    def test_is_active(self):
        assert PluginState.STARTED.is_active is True
        assert PluginState.UNREGISTERED.is_active is False
        assert PluginState.STOPPED.is_active is False

    def test_is_operational(self):
        assert PluginState.INITIALIZED.is_operational is True
        assert PluginState.STARTED.is_operational is True
        assert PluginState.UNREGISTERED.is_operational is False
        assert PluginState.ERROR.is_operational is False


# ══════════════════════════════════════════════
# 2. PluginMetadata
# ══════════════════════════════════════════════

class TestPluginMetadata:
    def test_defaults(self):
        m = PluginMetadata()
        assert m.name == ""
        assert m.version == "1.0.0"
        assert m.priority == 0

    def test_to_dict(self):
        m = PluginMetadata(name="test", version="2.0", tags=["security", "audit"])
        d = m.to_dict()
        assert d["name"] == "test"
        assert d["version"] == "2.0"
        assert d["tags"] == ["security", "audit"]


# ══════════════════════════════════════════════
# 3. RuntimePlugin — Basic
# ══════════════════════════════════════════════

class SimplePlugin(RuntimePlugin):
    name = "simple_test"
    version = "1.0.0"


class FullLifecyclePlugin(RuntimePlugin):
    name = "full_lifecycle"
    version = "2.0.0"
    priority = 10

    calls = []

    def on_initialize(self, runtime):
        self.calls.append("init")

    def on_start(self):
        self.calls.append("start")

    def on_stop(self):
        self.calls.append("stop")

    def on_shutdown(self):
        self.calls.append("shutdown")


class TestRuntimePlugin:
    def test_is_runtime_hook(self):
        p = SimplePlugin()
        assert isinstance(p, RuntimeHook)

    def test_initial_state(self):
        p = SimplePlugin()
        assert p.state == PluginState.UNREGISTERED

    def test_meta(self):
        p = SimplePlugin()
        assert p.meta.name == "simple_test"

    def test_initialize(self):
        p = FullLifecyclePlugin()
        p.initialize(None)
        assert p.state == PluginState.INITIALIZED
        assert "init" in p.calls

    def test_start(self):
        p = FullLifecyclePlugin()
        p.initialize(None)
        p.start()
        assert p.state == PluginState.STARTED
        assert "start" in p.calls

    def test_start_without_init_raises(self):
        p = SimplePlugin()
        with pytest.raises(RuntimeError, match="Cannot start"):
            p.start()

    def test_stop(self):
        p = FullLifecyclePlugin()
        p.initialize(None)
        p.start()
        p.stop()
        assert p.state == PluginState.STOPPED
        assert "stop" in p.calls

    def test_shutdown(self):
        p = FullLifecyclePlugin()
        p.initialize(None)
        p.shutdown()
        assert p.state == PluginState.DISABLED
        assert "shutdown" in p.calls

    def test_init_error_sets_error_state(self):
        class BadPlugin(RuntimePlugin):
            name = "bad"
            def on_initialize(self, runtime):
                raise ValueError("init fail")
        p = BadPlugin()
        with pytest.raises(RuntimeError, match="init failed"):
            p.initialize(None)
        assert p.state == PluginState.ERROR

    def test_enable_from_disabled(self):
        p = SimplePlugin()
        p._state = PluginState.DISABLED
        p.enable()
        assert p.state == PluginState.INSTALLED


# ══════════════════════════════════════════════
# 4. PluginRegistry
# ══════════════════════════════════════════════

class TestPluginRegistry:
    @pytest.fixture
    def registry(self):
        return PluginRegistry()

    def test_register(self, registry):
        p = SimplePlugin()
        registry.register(p)
        assert "simple_test" in registry
        assert p.state == PluginState.INSTALLED

    def test_register_duplicate_raises(self, registry):
        registry.register(SimplePlugin())
        with pytest.raises(ValueError, match="already registered"):
            registry.register(SimplePlugin())

    def test_unregister(self, registry):
        p = SimplePlugin()
        registry.register(p)
        removed = registry.unregister("simple_test")
        assert removed is p
        assert p.state == PluginState.UNREGISTERED

    def test_unregister_missing(self, registry):
        assert registry.unregister("nope") is None

    def test_get(self, registry):
        registry.register(SimplePlugin())
        assert registry.get("simple_test") is not None
        assert registry.get("nope") is None

    def test_list_all(self, registry):
        registry.register(SimplePlugin())
        registry.register(FullLifecyclePlugin())
        assert len(registry.list_all()) == 2

    def test_list_by_tag(self, registry):
        class TaggedPlugin(RuntimePlugin):
            name = "tagged"
            version = "1.0"
            def __init__(self):
                super().__init__()
                self._tags = ["observability"]

            @property
            def meta(self):
                base = super().meta
                base.tags = self._tags
                return base

        registry.register(TaggedPlugin())
        assert len(registry.list_by_tag("observability")) == 1
        assert len(registry.list_by_tag("security")) == 0

    def test_list_by_state(self, registry):
        p = FullLifecyclePlugin()
        registry.register(p)
        p.initialize(None)
        assert len(registry.list_by_state(PluginState.INITIALIZED)) == 1

    def test_names(self, registry):
        registry.register(SimplePlugin())
        assert "simple_test" in registry.names()

    def test_disable_enable(self, registry):
        registry.register(SimplePlugin())
        assert registry.disable("simple_test") is True
        assert "simple_test" not in registry.names()
        assert len(registry.list_disabled()) == 1

        assert registry.enable("simple_test") is True
        assert "simple_test" in registry.names()

    def test_discover(self, registry):
        p1 = SimplePlugin()
        registry.register(p1)
        report = registry.discover()
        assert report["valid"] is True
        assert report["total"] == 1

    def test_discover_missing_dep(self, registry):
        class DepPlugin(RuntimePlugin):
            name = "dep_plugin"
            version = "1.0"
            @property
            def meta(self):
                base = super().meta
                base.dependencies = ["missing_plugin"]
                return base
        registry.register(DepPlugin())
        report = registry.discover()
        assert report["valid"] is False
        assert len(report["missing_deps"]) == 1

    def test_clear(self, registry):
        registry.register(SimplePlugin())
        registry.clear()
        assert len(registry) == 0

    def test_len_and_iter(self, registry):
        registry.register(SimplePlugin())
        registry.register(FullLifecyclePlugin())
        assert len(registry) == 2
        names = [p.meta.name for p in registry]
        assert "simple_test" in names
        assert "full_lifecycle" in names


# ══════════════════════════════════════════════
# 5. PluginLoader
# ══════════════════════════════════════════════

class TestPluginLoader:
    @pytest.fixture
    def loader(self):
        return PluginLoader()

    def test_load_missing_module(self, loader):
        plugin = loader.load("nonexistent.module", "FakePlugin")
        assert plugin is None
        assert len(loader.load_errors) == 1

    def test_load_wrong_type(self, loader):
        plugin = loader.load("src.runtime.plugins.base", "PluginState")
        # PluginState is an Enum, not a RuntimePlugin
        assert plugin is None

    def test_load_all_empty_module(self, loader):
        """Module with no RuntimePlugin subclasses returns empty."""
        plugins = loader.load_all("src.runtime.plugins.registry", register=False)
        # registry.py has PluginRegistry, not RuntimePlugin
        assert len(plugins) == 0

    def test_clear_errors(self, loader):
        loader.load("nope.nope", "Fake")
        assert len(loader.load_errors) > 0
        loader.clear_errors()
        assert len(loader.load_errors) == 0


# ══════════════════════════════════════════════
# 6. PluginHookBridge
# ══════════════════════════════════════════════

class TestPluginHookBridge:
    def test_is_runtime_hook(self):
        b = PluginHookBridge()
        assert isinstance(b, RuntimeHook)

    def test_add_remove_plugin(self):
        b = PluginHookBridge()
        p = SimplePlugin()
        p.initialize(None)
        b.add_plugin(p)
        assert len(b.list_plugins()) == 1
        b.remove_plugin(p)
        assert len(b.list_plugins()) == 0

    def test_broadcast_after_transition(self):
        b = PluginHookBridge()
        class LogPlugin(RuntimePlugin):
            name = "log"
            events = []
            def after_transition(self, engine, fs, ts, ctx, t):
                self.events.append(f"{fs.name}→{ts.name}")
        p = LogPlugin()
        p.initialize(None)
        p.start()
        b.add_plugin(p)
        b.after_transition(None, AgentState.INIT, AgentState.PROFILE, None, None)
        assert len(p.events) == 1
        assert "INIT→PROFILE" in p.events[0]

    def test_broadcast_skips_non_operational(self):
        b = PluginHookBridge()
        class LogPlugin(RuntimePlugin):
            name = "log"
            events = []
            def after_transition(self, *a):
                self.events.append(1)
        p = LogPlugin()
        # p is UNREGISTERED — not operational
        b.add_plugin(p)
        b.after_transition(None, AgentState.INIT, AgentState.PROFILE, None, None)
        assert len(p.events) == 0  # skipped

    def test_broadcast_error_isolation(self):
        b = PluginHookBridge()
        class CrashPlugin(RuntimePlugin):
            name = "crash"
            def after_transition(self, *a):
                raise RuntimeError("boom")
        class GoodPlugin(RuntimePlugin):
            name = "good"
            events = []
            def after_transition(self, *a):
                self.events.append("ok")
        cp = CrashPlugin()
        gp = GoodPlugin()
        cp.initialize(None); cp.start()
        gp.initialize(None); gp.start()
        b.add_plugin(cp)
        b.add_plugin(gp)
        b.after_transition(None, AgentState.INIT, AgentState.PROFILE, None, None)
        # CrashPlugin fails but GoodPlugin still gets the event
        assert "ok" in gp.events

    def test_relay_event(self):
        b = PluginHookBridge()
        class EventPlugin(RuntimePlugin):
            name = "evt"
            events = []
            def on_event(self, event):
                self.events.append(event.event_type)
        p = EventPlugin()
        p.initialize(None); p.start()
        b.add_plugin(p)
        b.relay_event(RuntimeEvent(event_type="evaluation"))
        assert p.events == ["evaluation"]

    def test_bridge_from_registry(self):
        registry = PluginRegistry()
        p = FullLifecyclePlugin()
        registry.register(p)
        p.initialize(None)
        p.start()
        bridge = bridge_from_registry(registry)
        assert len(bridge.list_plugins()) == 1


# ══════════════════════════════════════════════
# 7. PluginManager
# ══════════════════════════════════════════════

class TestPluginManager:
    @pytest.fixture
    def manager(self):
        return PluginManager()

    def test_install(self, manager):
        p = manager.install(SimplePlugin())
        assert p.state == PluginState.INSTALLED
        assert len(manager.registry) == 1

    def test_remove(self, manager):
        manager.install(FullLifecyclePlugin())
        assert manager.remove("full_lifecycle") is True
        assert len(manager.registry) == 0

    def test_remove_missing(self, manager):
        assert manager.remove("nope") is False

    def test_initialize_all(self, manager):
        manager.install(FullLifecyclePlugin())
        manager.install(SimplePlugin())
        initialized = manager.initialize_all(None)
        assert len(initialized) == 2
        assert "full_lifecycle" in initialized

    def test_start_all(self, manager):
        manager.install(FullLifecyclePlugin())
        manager.initialize_all(None)
        started = manager.start_all()
        assert len(started) == 1
        assert "full_lifecycle" in started

    def test_stop_all(self, manager):
        p = FullLifecyclePlugin()
        manager.install(p)
        manager.initialize_all(None)
        manager.start_all()
        stopped = manager.stop_all()
        assert "full_lifecycle" in stopped
        assert p.state == PluginState.STOPPED

    def test_shutdown_all(self, manager):
        manager.install(FullLifecyclePlugin())
        manager.initialize_all(None)
        shutdown = manager.shutdown_all()
        assert "full_lifecycle" in shutdown

    def test_disable_enable(self, manager):
        manager.install(SimplePlugin())
        assert manager.disable("simple_test") is True
        assert manager.enable("simple_test") is True

    def test_list_plugins(self, manager):
        manager.install(SimplePlugin())
        plugins = manager.list_plugins()
        assert len(plugins) == 1
        assert plugins[0]["name"] == "simple_test"

    def test_priority_order_initialize(self, manager):
        class LowPlugin(RuntimePlugin):
            name = "low"
            version = "1.0"
            @property
            def meta(self):
                base = super().meta
                base.priority = 1
                return base
        class HighPlugin(RuntimePlugin):
            name = "high"
            version = "1.0"
            @property
            def meta(self):
                base = super().meta
                base.priority = 10
                return base

        hp = manager.install(HighPlugin())
        lp = manager.install(LowPlugin())
        manager.initialize_all(None)
        # Both should be initialized
        assert hp.state == PluginState.INITIALIZED
        assert lp.state == PluginState.INITIALIZED

    def test_summary(self, manager):
        manager.install(SimplePlugin())
        manager.initialize_all(None)
        s = manager.summary()
        assert s["total_installed"] == 1
        assert s["initialized"] == 1


# ══════════════════════════════════════════════
# 8. Engine Integration
# ══════════════════════════════════════════════

class TestPluginEngineIntegration:
    def test_plugin_via_bridge(self):
        """Plugin receives engine events through the hook bridge."""
        class CounterPlugin(RuntimePlugin):
            name = "counter"
            count = 0
            def after_transition(self, *a):
                self.count += 1

        p = CounterPlugin()
        manager = PluginManager()
        manager.install(p)
        manager.initialize_all(None)
        manager.start_all()

        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="plug1")
        engine._table = table
        engine.add_hook(manager.bridge)
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        engine.run()

        assert p.count >= 1

    def test_engine_without_plugins_backward_compat(self):
        """Engine works fine without any plugins."""
        table = TransitionTable(custom={
            AgentState.INIT: AgentState.PROFILE,
            AgentState.PROFILE: AgentState.DONE,
        })
        engine = RuntimeEngine(session_id="no_plugins")
        engine._table = table
        engine.register_handler(AgentState.PROFILE, lambda c: None)
        engine.run()
        assert engine._checkpoint.state_count() >= 1


# ══════════════════════════════════════════════
# 9. Edge Cases
# ══════════════════════════════════════════════

class TestPluginEdgeCases:
    @pytest.fixture
    def manager(self):
        return PluginManager()

    def test_empty_registry(self):
        r = PluginRegistry()
        assert len(r) == 0
        assert r.discover()["valid"] is True

    def test_duplicate_in_bridge(self):
        b = PluginHookBridge()
        p = SimplePlugin()
        p.initialize(None)
        b.add_plugin(p)
        b.add_plugin(p)  # duplicate
        assert len(b.list_plugins()) == 1

    def test_remove_stops_plugin(self, manager):
        p = FullLifecyclePlugin()
        manager.install(p)
        manager.initialize_all(None)
        manager.start_all()
        manager.remove("full_lifecycle")
        assert p.state in (PluginState.DISABLED, PluginState.UNREGISTERED)

    def test_shutdown_fails_gracefully(self, manager):
        class BadShutdown(RuntimePlugin):
            name = "bad_shutdown"
            def on_shutdown(self):
                raise RuntimeError("nope")
        p = BadShutdown()
        manager.install(p)
        manager.initialize_all(None)
        # Should not raise
        manager.shutdown_all()
        assert p.state == PluginState.ERROR
