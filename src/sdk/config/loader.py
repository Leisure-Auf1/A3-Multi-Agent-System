"""
Phase 6.0 — Runtime Config

Configuration system for the Veritas Runtime SDK.
Supports Python dataclass, YAML files, and environment variables.

Priority (highest to lowest):
    1. Programmatic (RuntimeConfig constructor args)
    2. Environment variables (VERITAS_*)
    3. YAML config file
    4. Defaults

Usage:
    # Python
    config = RuntimeConfig(recovery=True, max_retries=3)

    # YAML
    loader = ConfigLoader()
    config = loader.load("veritas.yaml")

    # Merge
    config = loader.load("veritas.yaml", overrides={"recovery": False})
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import os

from ..exceptions import ConfigError


# ══════════════════════════════════════════════
# RuntimeConfig
# ══════════════════════════════════════════════


@dataclass
class PluginEntry:
    """Configuration for a single plugin."""
    name: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeConfig:
    """
    Configuration for the Veritas Runtime.

    All fields have sensible defaults. Override via constructor,
    YAML, or environment variables.

    Usage:
        config = RuntimeConfig(
            recovery=RecoverySubConfig(enabled=True, max_retries=3),
            plugins=[PluginEntry(name="security", enabled=True)],
        )
    """

    # ── Recovery ──────────────────────────
    recovery_enabled: bool = True
    max_retries: int = 3
    retry_delay_ms: float = 1000.0

    # ── Plugins ───────────────────────────
    plugins: List[PluginEntry] = field(default_factory=list)

    # ── Distributed ───────────────────────
    distributed_enabled: bool = False
    distributed_nodes: List[str] = field(default_factory=list)

    # ── Observability ─────────────────────
    trace_enabled: bool = True
    explainability_enabled: bool = True
    lifecycle_enabled: bool = True

    # ── Execution ─────────────────────────
    default_timeout_seconds: float = 300.0
    max_transitions: int = 50

    # ── Security ──────────────────────────
    security_enabled: bool = False

    # ── Metadata ──────────────────────────
    runtime_name: str = "veritas-core"
    runtime_version: str = "6.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recovery": {
                "enabled": self.recovery_enabled,
                "max_retries": self.max_retries,
                "retry_delay_ms": self.retry_delay_ms,
            },
            "plugins": [{"name": p.name, "enabled": p.enabled, "config": p.config} for p in self.plugins],
            "distributed": {
                "enabled": self.distributed_enabled,
                "nodes": self.distributed_nodes,
            },
            "observability": {
                "trace_enabled": self.trace_enabled,
                "explainability_enabled": self.explainability_enabled,
                "lifecycle_enabled": self.lifecycle_enabled,
            },
            "execution": {
                "default_timeout_seconds": self.default_timeout_seconds,
                "max_transitions": self.max_transitions,
            },
            "security": {"enabled": self.security_enabled},
            "runtime": {
                "name": self.runtime_name,
                "version": self.runtime_version,
            },
        }


# ══════════════════════════════════════════════
# ConfigLoader
# ══════════════════════════════════════════════


class ConfigLoader:
    """
    Loads RuntimeConfig from multiple sources with priority.

    Priority: constructor > env vars > YAML file > defaults.

    Usage:
        loader = ConfigLoader()
        config = loader.load("veritas.yaml")
        config = loader.load("veritas.yaml", overrides={"recovery_enabled": False})
    """

    ENV_PREFIX = "VERITAS_"

    def __init__(self):
        pass

    def load(
        self,
        yaml_path: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> RuntimeConfig:
        """
        Load configuration with layered priority.

        Args:
            yaml_path: Path to a YAML config file (optional).
            overrides: Programmatic overrides (highest priority).

        Returns:
            Merged RuntimeConfig.

        Raises:
            ConfigError: If the YAML file exists but is malformed.
        """
        config = RuntimeConfig()

        # Layer 1: YAML file
        if yaml_path and os.path.exists(yaml_path):
            yaml_data = self._load_yaml(yaml_path)
            if yaml_data:
                config = self._merge_yaml(config, yaml_data)

        # Layer 2: Environment variables
        config = self._apply_env(config)

        # Layer 3: Programmatic overrides (highest priority)
        if overrides:
            config = self._apply_overrides(config, overrides)

        return config

    def load_from_dict(self, data: Dict[str, Any]) -> RuntimeConfig:
        """Load configuration from a plain dictionary (no YAML/ENV)."""
        config = RuntimeConfig()
        return self._merge_yaml(config, data)

    # ── Internal ──────────────────────────

    def _load_yaml(self, path: str) -> Optional[Dict[str, Any]]:
        """Load a YAML config file. Returns None if missing."""
        try:
            import yaml
            with open(path, "r") as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            # PyYAML not installed — skip YAML loading
            return None
        except Exception as e:
            raise ConfigError(f"Failed to load YAML: {e}", path=path)

    def _merge_yaml(
        self,
        config: RuntimeConfig,
        data: Dict[str, Any],
    ) -> RuntimeConfig:
        """Merge YAML data into a RuntimeConfig."""
        runtime = data.get("runtime", {})

        recovery = runtime.get("recovery", {})
        if "enabled" in recovery:
            config.recovery_enabled = recovery["enabled"]
        if "max_retries" in recovery:
            config.max_retries = recovery["max_retries"]
        if "retry_delay_ms" in recovery:
            config.retry_delay_ms = recovery["retry_delay_ms"]

        plugins_data = runtime.get("plugins", {}).get("enabled", [])
        if plugins_data:
            config.plugins = [
                PluginEntry(name=p if isinstance(p, str) else p.get("name", ""))
                for p in plugins_data
            ]

        dist = runtime.get("distributed", {})
        if "enabled" in dist:
            config.distributed_enabled = dist["enabled"]
        if "nodes" in dist:
            config.distributed_nodes = dist["nodes"]

        obs = runtime.get("observability", {})
        for key in ("trace_enabled", "explainability_enabled", "lifecycle_enabled"):
            if key in obs:
                setattr(config, key, obs[key])

        exec_cfg = runtime.get("execution", {})
        if "default_timeout_seconds" in exec_cfg:
            config.default_timeout_seconds = exec_cfg["default_timeout_seconds"]
        if "max_transitions" in exec_cfg:
            config.max_transitions = exec_cfg["max_transitions"]

        sec = runtime.get("security", {})
        if "enabled" in sec:
            config.security_enabled = sec["enabled"]

        return config

    def _apply_env(self, config: RuntimeConfig) -> RuntimeConfig:
        """Apply VERITAS_* environment variables."""
        env_map = {
            "VERITAS_RECOVERY": ("recovery_enabled", self._parse_bool),
            "VERITAS_MAX_RETRIES": ("max_retries", int),
            "VERITAS_DISTRIBUTED": ("distributed_enabled", self._parse_bool),
            "VERITAS_SECURITY": ("security_enabled", self._parse_bool),
            "VERITAS_TRACE": ("trace_enabled", self._parse_bool),
            "VERITAS_EXPLAIN": ("explainability_enabled", self._parse_bool),
            "VERITAS_LIFECYCLE": ("lifecycle_enabled", self._parse_bool),
        }

        for env_key, (attr_name, converter) in env_map.items():
            value = os.getenv(env_key)
            if value is not None:
                try:
                    setattr(config, attr_name, converter(value))
                except (ValueError, TypeError):
                    pass

        return config

    def _apply_overrides(
        self,
        config: RuntimeConfig,
        overrides: Dict[str, Any],
    ) -> RuntimeConfig:
        """Apply programmatic overrides."""
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config

    @staticmethod
    def _parse_bool(value: str) -> bool:
        return value.lower() in ("true", "1", "yes", "on")
