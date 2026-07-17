"""
Phase 4.1 — WorkflowResult: 统一 Pipeline 输出模型

A3 所有 Pipeline 入口 (A3Workflow, web/app_v3.py, v1/pipeline.py)
共享此输出契约。每个 Agent 的产出映射到明确命名的字段，
便于 Trace、Evaluation、Dashboard 统一消费。

字段:
  profile       — ProfileAgent 六维画像
  learning_plan — PlannerAgent 学习路径
  resources     — ResourceAgent 推荐资源
  evaluation    — ReviewGate 质量评估
  reflection    — ReflectionAgent 执行后反思
  trace         — EventBus 完整时间线 (TraceEvent list)
  memory_saved  — MemoryManager 是否成功持久化
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
# WorkflowContext
# ──────────────────────────────────────────────

@dataclass
class WorkflowContext:
    """工作流执行上下文 — 标识一次 pipeline run"""
    session_id: str = ""
    user_goal: str = ""
    user_profile: Dict[str, Any] = field(default_factory=dict)
    knowledge_gaps: List[str] = field(default_factory=list)
    start_time: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_goal": self.user_goal,
            "user_profile": self.user_profile,
            "knowledge_gaps": self.knowledge_gaps,
            "start_time": self.start_time,
        }


# ──────────────────────────────────────────────
# WorkflowResult — 统一输出模型
# ──────────────────────────────────────────────

@dataclass
class WorkflowResult:
    """
    A3 Pipeline 统一输出。

    所有编排入口必须返回此结构，确保 Dashboard/Trace/Evaluation
    可以无差别消费。

    使用:
        result = workflow.run(user_goal="...")
        print(result.learning_plan)     # PlannerAgent 输出
        print(result.evaluation)        # ReviewGate 评分
        print(result.memory_saved)      # 是否持久化
    """

    # ── 执行状态 ──
    success: bool = False
    context: WorkflowContext = field(default_factory=WorkflowContext)
    total_duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)
    completed_at: str = ""

    # ── Agent 产出 ──
    profile: Optional[Dict[str, Any]] = None
    """ProfileAgent 输出: 六维画像字典 (含 profile, source, confidence)"""

    learning_plan: Optional[Dict[str, Any]] = None
    """PlannerAgent 输出: LearningPlan.to_dict() {nodes, total_minutes, strategy_rationale}"""

    resources: Optional[List[Dict[str, Any]]] = None
    """ResourceAgent 输出: List[ResourceItem.to_dict()]"""

    evaluation: Optional[Dict[str, Any]] = None
    """ReviewGate 输出: {score, issues, passed}"""

    reflection: Optional[Dict[str, Any]] = None
    """ReflectionAgent 输出: {success, score, achievements, improvements, summary}"""

    trace: Optional[List[Dict[str, Any]]] = None
    """EventBus 完整时间线: List[TraceEvent.to_dict()]"""

    memory_saved: bool = False
    """MemoryManager 是否成功持久化本次会话"""

    meta_reflection: Optional[Dict[str, Any]] = None
    """Phase 4.6 — MetaReflector 输出: {mistake, root_cause, improvement, future_strategy, severity, concept, node_id}"""

    # ── 向后兼容别名 ──
    @property
    def plan(self) -> Optional[Dict[str, Any]]:
        """向后兼容: plan == learning_plan"""
        return self.learning_plan

    @plan.setter
    def plan(self, value: Optional[Dict[str, Any]]) -> None:
        self.learning_plan = value

    # ── Phase 4.4 — Explanations ──
    @property
    def explanations(self) -> Optional[List[Dict[str, Any]]]:
        """决策解释列表 — 从 evaluation['explanations'] 提取."""
        if self.evaluation and isinstance(self.evaluation, dict):
            return self.evaluation.get("explanations")
        return None

    # ── 序列化 ──

    def to_dict(self) -> Dict[str, Any]:
        """完整序列化 — 供 Dashboard / API 消费 (含向后兼容 plan 别名)"""
        return {
            "success": self.success,
            "context": self.context.to_dict(),
            "profile": self.profile,
            "learning_plan": self.learning_plan,
            "plan": self.learning_plan,  # 向后兼容
            "resources": self.resources,
            "evaluation": self.evaluation,
            "reflection": self.reflection,
            "trace": self.trace,
            "memory_saved": self.memory_saved,
            "meta_reflection": self.meta_reflection,
            "total_duration_ms": self.total_duration_ms,
            "errors": self.errors,
            "completed_at": self.completed_at,
        }

    def summary(self) -> Dict[str, Any]:
        """轻量摘要 — 供列表/卡片展示"""
        nodes = len(self.learning_plan.get("nodes", [])) if self.learning_plan else 0
        resources_count = len(self.resources) if self.resources else 0
        score = self.evaluation.get("score", 0) if self.evaluation else 0

        return {
            "success": self.success,
            "goal": self.context.user_goal,
            "nodes": nodes,
            "resources": resources_count,
            "score": score,
            "duration_ms": self.total_duration_ms,
            "memory_saved": self.memory_saved,
        }
