"""
Phase 13 — AgentEvaluationEngine: 自动评价 Agent 输出质量

评分维度:
  - correctness: 输出是否符合规则
  - personalization: 是否使用学生 memory
  - explainability: 是否存在 reason
  - efficiency: 是否浪费步骤

输出: EvaluationResult (含 suggestions)
"""

from __future__ import annotations
import json, time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .judge import JudgeResult, RuleJudge, LLMJudge
from core.event_bus import AgentEventBus


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

@dataclass
class EvaluationResult:
    """单次 Agent 评估结果"""
    agent_name: str
    session_id: str = ""
    correctness_score: float = 0.0
    personalization_score: float = 0.0
    explainability_score: float = 0.0
    efficiency_score: float = 0.0
    overall_score: float = 0.0
    suggestions: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "session_id": self.session_id,
            "correctness_score": self.correctness_score,
            "personalization_score": self.personalization_score,
            "explainability_score": self.explainability_score,
            "efficiency_score": self.efficiency_score,
            "overall_score": self.overall_score,
            "suggestions": self.suggestions,
            "details": self.details,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_judge(cls, agent_name: str, judge_result: JudgeResult,
                   session_id: str = "") -> "EvaluationResult":
        dims = judge_result.dimensions
        suggestions = []
        if dims.get("correctness", 0) < 0.5:
            suggestions.append("改进输出格式和内容准确性")
        if dims.get("personalization", 0) < 0.4:
            suggestions.append("增强个性化: 使用学生记忆和画像")
        if dims.get("explainability", 0) < 0.4:
            suggestions.append("增加决策解释: 为什么这么推荐/规划")
        if dims.get("efficiency", 0) < 0.5:
            suggestions.append("优化执行效率: 减少冗余步骤")

        return cls(
            agent_name=agent_name,
            session_id=session_id,
            correctness_score=dims.get("correctness", 0),
            personalization_score=dims.get("personalization", 0),
            explainability_score=dims.get("explainability", 0),
            efficiency_score=dims.get("efficiency", 0),
            overall_score=judge_result.score,
            suggestions=suggestions,
            details={"source": judge_result.source, "reason": judge_result.reason},
        )


# ──────────────────────────────────────────────
# AgentEvaluator
# ──────────────────────────────────────────────

class AgentEvaluator:
    """
    Agent 输出质量评估引擎.

    使用:
        evaluator = AgentEvaluator()
        result = evaluator.evaluate(
            agent_name="PlannerAgent",
            output=plan,
            input_context={"has_memory": True, "used_mastery": True},
        )
        print(f"Overall: {result.overall_score}")
    """

    def __init__(self, llm_router: Any = None):
        self.rule_judge = RuleJudge()
        self.llm_judge = LLMJudge(router=llm_router)
        self._history: List[EvaluationResult] = []

    def evaluate(
        self,
        agent_name: str,
        output: Any,
        input_context: Optional[Dict[str, Any]] = None,
        trace: Optional[Any] = None,
        use_llm: bool = False,
    ) -> EvaluationResult:
        """
        评估 Agent 输出.

        Args:
            agent_name: Agent 名称
            output: Agent 输出
            input_context: {has_memory, used_mastery, used_weak_points, ...}
            trace: TraceEvent (optional)
            use_llm: 是否使用 LLM 评估

        Returns:
            EvaluationResult
        """
        input_context = input_context or {}

        if use_llm and self.llm_judge.router:
            judge_result = self.llm_judge.evaluate(agent_name, output, input_context)
        else:
            judge_result = self.rule_judge.evaluate(agent_name, output, input_context, trace)

        result = EvaluationResult.from_judge(agent_name, judge_result)

        # 通过 EventBus 发布评估结果
        bus = AgentEventBus.get_instance()
        bus.emit(
            "AgentEvaluator",
            f"evaluate_{agent_name}",
            input_summary=f"agent={agent_name}",
            output_summary=f"score={result.overall_score:.2f}",
            metadata={"evaluation": result.to_dict()},
        )

        self._history.append(result)
        return result

    def evaluate_agent_pipeline(
        self,
        profile_output: Any,
        plan_output: Any,
        recommendation_output: Any,
        memory_context: Dict[str, Any],
    ) -> Dict[str, EvaluationResult]:
        """评估完整 Agent 管道"""
        results = {}

        # ProfileAgent
        ctx = {"has_memory": bool(memory_context.get("profile_history"))}
        results["ProfileAgent"] = self.evaluate("ProfileAgent", profile_output, ctx)

        # PlannerAgent
        ctx = {
            "has_memory": True,
            "used_mastery": bool(memory_context.get("mastery_map")),
            "used_weak_points": bool(memory_context.get("weak_points")),
        }
        results["PlannerAgent"] = self.evaluate("PlannerAgent", plan_output, ctx)

        # ResourceRecommendationAgent
        if recommendation_output:
            ctx = {"has_memory": True, "used_mastery": True}
            results["ResourceRecommendationAgent"] = self.evaluate(
                "ResourceRecommendationAgent", recommendation_output, ctx
            )

        return results

    def get_summary(self) -> Dict[str, Any]:
        """获取历史评分摘要"""
        if not self._history:
            return {"avg_score": 0.0, "evaluations": 0}

        agents = {}
        for r in self._history:
            if r.agent_name not in agents:
                agents[r.agent_name] = {"scores": [], "count": 0}
            agents[r.agent_name]["scores"].append(r.overall_score)
            agents[r.agent_name]["count"] += 1

        summary = {}
        for agent, data in agents.items():
            scores = data["scores"]
            summary[agent] = {
                "avg_score": round(sum(scores) / len(scores), 2),
                "min_score": min(scores),
                "max_score": max(scores),
                "evaluations": data["count"],
            }

        return {
            "avg_overall": round(sum(r.overall_score for r in self._history) / len(self._history), 2),
            "total_evaluations": len(self._history),
            "agents": summary,
        }

    def get_low_scoring(self, threshold: float = 0.5) -> List[EvaluationResult]:
        """获取低分评估"""
        return [r for r in self._history if r.overall_score < threshold]
