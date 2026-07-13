"""
Phase 12 — Judge Interface: RuleJudge + LLMJudge 统一评分接口

支持两种模式:
  RuleJudge: 基于规则的快速评分
  LLMJudge: 大模型评估 (需要 router)

统一接口: judge.evaluate(input, output) → {score, reason}
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

@dataclass
class JudgeResult:
    """单次评分结果"""
    score: float = 0.0           # 0.0-1.0
    reason: str = ""              # 评分理由
    source: str = "rule"          # rule | llm
    dimensions: Dict[str, float] = field(default_factory=dict)  # 各维度分数

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "reason": self.reason,
            "source": self.source,
            "dimensions": self.dimensions,
        }


# ──────────────────────────────────────────────
# RuleJudge
# ──────────────────────────────────────────────

class RuleJudge:
    """
    基于规则的快速评分.

    评估维度:
      - correctness: 输出是否符合规则/格式
      - personalization: 是否使用了学生记忆
      - explainability: 是否有解释理由
      - efficiency: 是否没有浪费步骤
    """

    def __init__(self):
        self._rules: Dict[str, Any] = {
            "correctness": self._score_correctness,
            "personalization": self._score_personalization,
            "explainability": self._score_explainability,
            "efficiency": self._score_efficiency,
        }

    def evaluate(
        self,
        agent_name: str,
        output: Any,
        input_context: Optional[Dict[str, Any]] = None,
        trace: Optional[Any] = None,
    ) -> JudgeResult:
        """
        评估 Agent 输出.

        Args:
            agent_name: Agent 名称
            output: Agent 输出 (dict / object / str)
            input_context: 输入上下文 (profile, memory, ...)
            trace: TraceEvent 列表

        Returns:
            JudgeResult
        """
        input_context = input_context or {}
        scores: Dict[str, float] = {}

        for dim, scorer in self._rules.items():
            try:
                scores[dim] = scorer(agent_name, output, input_context, trace)
            except Exception:
                scores[dim] = 0.0

        # 综合分
        weights = {"correctness": 0.35, "personalization": 0.3,
                   "explainability": 0.2, "efficiency": 0.15}
        overall = sum(scores.get(d, 0.0) * w for d, w in weights.items())
        overall = round(overall, 2)

        # 生成理由
        reasons = []
        if scores.get("correctness", 0) < 0.5:
            reasons.append("输出格式或内容不正确")
        if scores.get("personalization", 0) < 0.3:
            reasons.append("未使用学生个性化信息")
        if scores.get("explainability", 0) < 0.3:
            reasons.append("缺少决策解释")
        reason = "; ".join(reasons) if reasons else "输出质量良好"

        return JudgeResult(
            score=overall,
            reason=reason,
            source="rule",
            dimensions=scores,
        )

    # ── 各维度评分 ──────────────────────────

    def _score_correctness(self, agent: str, output: Any,
                           ctx: Dict[str, Any], trace: Any) -> float:
        """评估输出正确性"""
        score = 0.5

        # 有输出即基本分
        if output is None:
            return 0.0

        # ProfileAgent: 检查六维字段
        if agent == "ProfileAgent":
            if isinstance(output, dict):
                expected = ["knowledge_base", "cognitive_style", "learning_pace"]
                hits = sum(1 for k in expected if k in output and output[k])
                score = min(1.0, hits / len(expected) + 0.2)

        # PlannerAgent: 检查 plan 结构
        elif agent == "PlannerAgent":
            if hasattr(output, "nodes"):
                score = 0.7 if len(output.nodes) >= 1 else 0.3
                if hasattr(output, "strategy_rationale") and output.strategy_rationale:
                    score += 0.2
                if hasattr(output, "total_minutes") and output.total_minutes > 0:
                    score += 0.1

        # ResourceRecommendationAgent: 检查推荐结构
        elif agent == "ResourceRecommendationAgent":
            if hasattr(output, "recommended_resources"):
                res = output.recommended_resources
                score = 0.6 if len(res) >= 1 else 0.2
                if hasattr(output, "reasoning") and output.reasoning:
                    score += 0.2

        return min(score, 1.0)

    def _score_personalization(self, agent: str, output: Any,
                                ctx: Dict[str, Any], trace: Any) -> float:
        """评估个性化程度"""
        score = 0.3  # 基线: 有输出就有基本个性化分

        # 检查是否使用了 student memory
        if ctx.get("has_memory"):
            score += 0.3
        if ctx.get("used_mastery"):
            score += 0.2
        if ctx.get("used_weak_points"):
            score += 0.2

        return min(score, 1.0)

    def _score_explainability(self, agent: str, output: Any,
                               ctx: Dict[str, Any], trace: Any) -> float:
        """评估可解释性"""
        score = 0.3  # 基线: 有输出就有基本解释性分

        # 输出有 reason 字段
        if isinstance(output, dict) and output.get("reason"):
            score += 0.5
        if hasattr(output, "reason") and getattr(output, "reason", ""):
            score += 0.5

        # Trace 中有决策解释
        if trace and hasattr(trace, "reasoning_type"):
            score += 0.2

        # 检查输入上下文是否有理由
        if ctx.get("has_decision_explanation"):
            score += 0.3

        return min(score, 1.0)

    def _score_efficiency(self, agent: str, output: Any,
                           ctx: Dict[str, Any], trace: Any) -> float:
        """评估效率"""
        score = 0.7  # 默认基本效率

        # 检查是否有多余步骤
        if trace and hasattr(trace, "latency_ms"):
            ms = trace.latency_ms if isinstance(trace.latency_ms, (int, float)) else 0
            if ms > 1000:
                score -= 0.2
            elif ms < 50:
                score += 0.2

        # 输出过大扣分
        if isinstance(output, dict) and len(json.dumps(output)) > 10000:
            score -= 0.2

        return max(0.0, min(score, 1.0))


# ──────────────────────────────────────────────
# LLMJudge
# ──────────────────────────────────────────────

class LLMJudge:
    """LLM 作为评估器 (需要 router)"""

    def __init__(self, router: Any = None):
        self.router = router

    def evaluate(
        self,
        agent_name: str,
        output: Any,
        input_context: Optional[Dict[str, Any]] = None,
    ) -> JudgeResult:
        """LLM 评估"""
        if not self.router:
            return RuleJudge().evaluate(agent_name, output, input_context)

        output_str = json.dumps(
            output.to_dict() if hasattr(output, "to_dict") else str(output),
            ensure_ascii=False,
        )[:1000]

        prompt = f"""你是Agent质量评估专家。评估以下 {agent_name} 的输出。

输入上下文: {json.dumps(input_context or {}, ensure_ascii=False)[:300]}
输出: {output_str}

请按以下维度打分 (0.0-1.0):
- correctness: 输出是否正确
- personalization: 是否个性化
- explainability: 是否可解释
- efficiency: 是否高效

返回 JSON: {{"correctness": 0.8, "personalization": 0.7, "explainability": 0.6, "efficiency": 0.9, "reason": "总结"}}
只输出 JSON。"""

        try:
            payload = {
                "model": os.environ.get("LLM_MODEL", "spark-pro"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            }
            response = self.router.route_request("MetaReflector", payload)
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            data = json.loads(content)

            dims = {k: data.get(k, 0.0) for k in ["correctness", "personalization", "explainability", "efficiency"]}
            overall = round(sum(dims.values()) / 4, 2)

            return JudgeResult(
                score=overall,
                reason=data.get("reason", "LLM评估"),
                source="llm",
                dimensions=dims,
            )
        except Exception:
            return RuleJudge().evaluate(agent_name, output, input_context)
