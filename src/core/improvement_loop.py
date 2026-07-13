"""
Phase 14 — ImprovementLoop: 低分检测 → Reflection → 策略更新

流程:
  Agent 执行 → Trace → Evaluation → 发现低分
  → MetaReflector → ExperienceMemory → 下一轮优化策略

输出: ImprovementSuggestion
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

@dataclass
class ImprovementSuggestion:
    """改进建议"""
    target_agent: str                     # 目标 Agent
    problem: str                          # 问题描述
    solution: str                         # 解决方案
    priority: int = 5                     # 优先级 1-10
    source: str = "evaluation"            # evaluation | reflection | manual
    agent_scores: Dict[str, float] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_agent": self.target_agent,
            "problem": self.problem,
            "solution": self.solution,
            "priority": self.priority,
            "source": self.source,
            "agent_scores": self.agent_scores,
            "timestamp": self.timestamp,
        }


# ──────────────────────────────────────────────
# ImprovementLoop
# ──────────────────────────────────────────────

class ImprovementLoop:
    """
    改进循环管理器.

    使用:
        loop = ImprovementLoop(evaluator, reflector, experience_memory)
        suggestions = loop.run_cycle(
            agent_results={"ProfileAgent": eval_r1, "PlannerAgent": eval_r2},
        )
        # → 低分 Agent 触发 reflection, 生成改进建议
    """

    LOW_SCORE_THRESHOLD = 0.5
    PERSONALIZATION_THRESHOLD = 0.4

    def __init__(
        self,
        evaluator: Any,            # AgentEvaluator
        reflector: Any = None,     # MetaReflectorAgent
        experience_store: Any = None,  # ExperienceMemoryStore
    ):
        self.evaluator = evaluator
        self.reflector = reflector
        self.experience_store = experience_store
        self._suggestions: List[ImprovementSuggestion] = []

    def run_cycle(
        self,
        agent_results: Dict[str, Any],  # {agent_name: EvaluationResult}
        node_id: str = "",
        student_id: str = "",
    ) -> List[ImprovementSuggestion]:
        """
        运行一轮改进检测.

        Args:
            agent_results: 各 Agent 的评估结果
            node_id: 关联节点
            student_id: 学生 ID

        Returns:
            改进建议列表
        """
        suggestions: List[ImprovementSuggestion] = []

        for agent_name, result in agent_results.items():
            # 获取评估分数
            if hasattr(result, "overall_score"):
                score = result.overall_score
                dims = {
                    "correctness": getattr(result, "correctness_score", 0),
                    "personalization": getattr(result, "personalization_score", 0),
                    "explainability": getattr(result, "explainability_score", 0),
                }
            elif isinstance(result, dict):
                score = result.get("overall_score", 0)
                dims = {
                    "correctness": result.get("correctness_score", 0),
                    "personalization": result.get("personalization_score", 0),
                    "explainability": result.get("explainability_score", 0),
                }
            else:
                continue

            # 跳过高分
            if score >= self.LOW_SCORE_THRESHOLD:
                continue

            # ── 低分 → 生成建议 ──
            problem = f"{agent_name} 综合评分 {score:.0%} (低于阈值 {self.LOW_SCORE_THRESHOLD:.0%})"

            # 针对性建议
            if dims.get("personalization", 0) < self.PERSONALIZATION_THRESHOLD:
                solution = (
                    f"增强 {agent_name} 的个性化能力: "
                    "确保读取 StudentMemory 中的 mastery_map 和 weak_points, "
                    "根据学生画像调整输出"
                )
            elif dims.get("correctness", 0) < 0.5:
                solution = f"修复 {agent_name} 的输出格式和内容准确性问题"
            else:
                solution = f"优化 {agent_name} 的决策解释和效率"

            suggestion = ImprovementSuggestion(
                target_agent=agent_name,
                problem=problem,
                solution=solution,
                priority=8 if dims.get("personalization", 0) < self.PERSONALIZATION_THRESHOLD else 6,
                source="evaluation",
                agent_scores=dims,
            )
            suggestions.append(suggestion)

            # ── 触发 MetaReflector ──
            if self.reflector:
                try:
                    reflection = self.reflector.reflect(
                        node_id=node_id or agent_name.lower(),
                        failure_context={
                            "mistake": problem,
                            "student_id": student_id,
                            "scores": [score],
                            "attempts": 1,
                        },
                        concept=agent_name.lower(),
                        severity="HIGH" if score < 0.3 else "MEDIUM",
                    )
                    if reflection:
                        suggestions.append(ImprovementSuggestion(
                            target_agent=agent_name,
                            problem=reflection.root_cause,
                            solution=f"{reflection.improvement} | 策略: {reflection.future_strategy}",
                            priority=9,
                            source="reflection",
                        ))
                except Exception:
                    pass

        self._suggestions.extend(suggestions)
        return suggestions

    def get_pending_suggestions(self) -> List[ImprovementSuggestion]:
        return self._suggestions

    def get_top_suggestions(self, n: int = 5) -> List[ImprovementSuggestion]:
        return sorted(self._suggestions, key=lambda s: -s.priority)[:n]

    def get_by_agent(self, agent_name: str) -> List[ImprovementSuggestion]:
        return [s for s in self._suggestions if s.target_agent == agent_name]

    def clear(self) -> None:
        self._suggestions.clear()


# ──────────────────────────────────────────────
# 便捷工厂
# ──────────────────────────────────────────────

def create_improvement_loop(
    evaluator: Any,
    reflector: Any = None,
    experience_store: Any = None,
) -> ImprovementLoop:
    return ImprovementLoop(
        evaluator=evaluator,
        reflector=reflector,
        experience_store=experience_store,
    )
