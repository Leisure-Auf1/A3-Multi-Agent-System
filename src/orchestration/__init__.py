"""
Phase 9.3-B — Model Orchestrator Layer (Runtime)

Sits between Agent layer and Provider layer. Agents NEVER call Provider directly.

Modules:
    task_planner     — user request → TaskType
    model_selector   — capability + task + availability + quality + cost
    cost_optimizer   — economy/balanced/premium tier routing
    fallback_manager — circuit breaker + auto-switch on API failure
    context          — ModelExecutionContext, ExecutionResult
    runtime          — OrchestratorRuntime (central entry point)

Flow:
    Agent → OrchestratorRuntime.execute() → ModelSelector → ProviderFactory → Provider

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from .task_planner import TaskPlanner
from .model_selector import ModelSelector, SelectionResult, select_model
from .cost_optimizer import (
    CostDecision,
    get_task_cost_tier,
    get_provider_cost_estimate,
    get_provider_cost_tier,
    select_cost_optimal,
    rank_by_cost,
)
from .fallback_manager import FallbackManager, ProviderState
from .context import ModelExecutionContext, ExecutionResult
from .runtime import OrchestratorRuntime, get_runtime
from .analytics import DecisionAnalytics
from .user_preferences import UserPreferenceManager, UserModelPreference, TaskPreference

__all__ = [
    "TaskPlanner",
    "ModelSelector", "SelectionResult", "select_model",
    "CostDecision",
    "get_task_cost_tier",
    "get_provider_cost_estimate",
    "get_provider_cost_tier",
    "select_cost_optimal",
    "rank_by_cost",
    "FallbackManager", "ProviderState",
    "ModelExecutionContext", "ExecutionResult",
    "OrchestratorRuntime", "get_runtime",
    "DecisionAnalytics",
    "UserPreferenceManager", "UserModelPreference", "TaskPreference",
]
