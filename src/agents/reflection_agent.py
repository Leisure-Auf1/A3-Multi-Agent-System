"""
Phase 3 — ReflectionAgent: 执行后反思分析

职责:
  输入: 执行结果 (plan, resources, feedback)
  输出: 反思报告 (成功评估, 学习收获, 改进建议)

适用于 pipeline 执行完成后的总结性反思。
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

@dataclass
class ReflectionResult:
    """反思分析结果"""
    success: bool = True                       # 目标是否达成
    goal: str = ""                             # 原始目标
    score: float = 0.0                         # 评分 (0-100)
    achievements: List[str] = field(default_factory=list)   # 达成的成果
    improvements: List[str] = field(default_factory=list)   # 改进建议
    summary: str = ""                          # 综合总结
    source: str = "rule"                       # 反思来源: rule | llm (Phase 4.2)
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "goal": self.goal,
            "score": self.score,
            "achievements": self.achievements,
            "improvements": self.improvements,
            "summary": self.summary,
            "source": self.source,
            "generated_at": self.generated_at,
        }


# ──────────────────────────────────────────────
# ReflectionAgent
# ──────────────────────────────────────────────

class ReflectionAgent:
    """
    执行后反思 Agent.

    分析:
      - 目标是否达成?
      - 学到了什么?
      - 应该改进什么?

    使用:
        agent = ReflectionAgent()
        result = agent.reflect(
            goal="学习 Python 网络编程",
            plan={...},
            resources=[...],
            feedback={"score": 85},
        )
    """

    def __init__(self):
        self._llm_provider = None  # LLMProvider (Phase 4.2, optional)

    # ── LLM Provider Injection (Phase 4.2) ─────

    def set_llm_provider(self, provider: Any) -> None:
        """Inject an LLMProvider for LLM reflection (None = pure rule)."""
        self._llm_provider = provider

    # ── 主入口 ────────────────────────────────

    def reflect(
        self,
        goal: str = "",
        plan: Optional[Dict[str, Any]] = None,
        resources: Optional[List[Dict[str, Any]]] = None,
        feedback: Optional[Dict[str, Any]] = None,
        execution_context: Optional[Dict[str, Any]] = None,
    ) -> ReflectionResult:
        """
        执行反思分析.

        Args:
            goal: 学习目标
            plan: 学习计划 (LearningPlan.to_dict())
            resources: 推荐资源列表
            feedback: 反馈数据 (含 score, issues)
            execution_context: 额外上下文

        Returns:
            ReflectionResult
        """
        plan = plan or {}
        resources = resources or []
        feedback = feedback or {}
        execution_context = execution_context or {}

        # 评估成功与否
        score = feedback.get("score", 75)
        success = score >= 70

        # 确定成果
        achievements = self._determine_achievements(
            plan=plan,
            resources=resources,
            score=score,
        )

        # 确定改进方向
        improvements = self._determine_improvements(
            plan=plan,
            feedback=feedback,
            resources=resources,
        )

        # 生成总结 — LLM 优先 (Phase 4.2), 失败 fallback 规则模板
        summary = ""
        llm_improvements: List[str] = []
        source = "rule"
        if self._llm_provider is not None:
            summary, llm_improvements = self._reflect_with_llm(
                goal=goal, plan=plan, resources=resources, score=score,
            )
            if summary:
                source = "llm"
                for imp in llm_improvements:
                    if imp not in improvements:
                        improvements.append(imp)

        if not summary:
            summary = self._generate_summary(
                goal=goal,
                success=success,
                score=score,
                achievements=achievements,
                improvements=improvements,
            )

        result = ReflectionResult(
            success=success,
            goal=goal,
            score=score,
            achievements=achievements,
            improvements=improvements,
            summary=summary,
            source=source,
        )
        return result

    # ── LLM 反思 (Phase 4.2) ────────────────────

    REFLECTION_LLM_PROMPT = """你是学习反思分析专家。基于本次学习规划的执行结果，生成简洁的反思总结。

学习目标: {goal}
学习路径: {plan_summary}
推荐资源: {resources_summary}
质量评分: {score}/100

请输出 JSON (只输出 JSON, 不要 markdown):
{{
  "summary": "综合反思总结 (60-120字, 包含目标达成情况与关键收获)",
  "improvements": ["改进建议1", "改进建议2"]
}}"""

    def _reflect_with_llm(
        self,
        goal: str,
        plan: Dict[str, Any],
        resources: List[Dict[str, Any]],
        score: float,
    ) -> Tuple[str, List[str]]:
        """
        LLM 反思生成 (Phase 4.2).

        Returns:
            (summary, improvements) — 失败时返回 ("", []) 触发规则 fallback。
        """
        llm = self._llm_provider
        if llm is None:
            return "", []
        try:
            nodes = plan.get("nodes", [])
            plan_summary = (
                f"{len(nodes)} 个节点, 共 {plan.get('total_minutes', 0)} 分钟: "
                + ", ".join(n.get("title", "") for n in nodes[:6])
            ) if nodes else "无学习路径"
            resources_summary = (
                ", ".join(f"{r.get('type', '?')}:{r.get('title', '?')}" for r in resources[:5])
            ) if resources else "无推荐资源"

            response = llm.generate(
                prompt=self.REFLECTION_LLM_PROMPT.format(
                    goal=goal,
                    plan_summary=plan_summary,
                    resources_summary=resources_summary,
                    score=score,
                ),
                system_prompt="You are a learning reflection expert. Output ONLY valid JSON.",
                temperature=0.3,
                max_tokens=512,
            )
            if not response.success:
                return "", []

            content = response.content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:]) if len(lines) > 2 else content
                if content.endswith("```"):
                    content = content[:-3]
            data = json.loads(content)

            summary = data.get("summary", "")
            improvements = [
                i for i in data.get("improvements", []) or []
                if isinstance(i, str) and i.strip()
            ][:3]
            if isinstance(summary, str) and summary.strip():
                return summary.strip(), improvements
            return "", []
        except Exception:
            return "", []  # rule fallback

    # ── 内部逻辑 ──────────────────────────────

    def _determine_achievements(
        self,
        plan: Dict[str, Any],
        resources: List[Dict[str, Any]],
        score: float,
    ) -> List[str]:
        """确定达成的成果"""
        achievements: List[str] = []

        # 学习计划成果
        nodes = plan.get("nodes", [])
        if nodes:
            achievements.append(f"完成 {len(nodes)} 个学习节点的路径规划")

        total_minutes = plan.get("total_minutes", 0)
        if total_minutes > 0:
            achievements.append(f"预估学习时长 {total_minutes} 分钟")

        # 资源推荐成果
        if resources:
            type_counts: Dict[str, int] = {}
            for r in resources:
                rt = r.get("type", "unknown")
                type_counts[rt] = type_counts.get(rt, 0) + 1
            type_str = ", ".join(f"{t}×{c}" for t, c in type_counts.items())
            achievements.append(f"匹配 {len(resources)} 项个性化资源 ({type_str})")

        # 质量评分
        if score >= 85:
            achievements.append(f"质量评分 {score}分 — 优秀")
        elif score >= 70:
            achievements.append(f"质量评分 {score}分 — 良好")
        else:
            achievements.append(f"质量评分 {score}分 — 待改进")

        # 无具体成果时的默认
        if not achievements:
            achievements.append("完成基础分析流程")

        return achievements

    def _determine_improvements(
        self,
        plan: Dict[str, Any],
        feedback: Dict[str, Any],
        resources: List[Dict[str, Any]],
    ) -> List[str]:
        """确定改进方向"""
        improvements: List[str] = []

        issues = feedback.get("issues", [])
        if isinstance(issues, list) and issues:
            for issue in issues[:3]:
                if isinstance(issue, str):
                    improvements.append(f"修复: {issue}")
                elif isinstance(issue, dict):
                    improvements.append(f"修复: {issue.get('description', str(issue))}")

        # 基于资源量的建议
        if len(resources) > 6:
            improvements.append("资源数量过多, 建议精选核心资源减少认知负荷")
        elif len(resources) < 2 and plan.get("nodes"):
            improvements.append("资源覆盖不足, 建议为关键节点增加配套资源")

        # 基于计划的建议
        nodes = plan.get("nodes", [])
        if len(nodes) > 10:
            improvements.append("学习路径过长, 建议分阶段执行避免疲劳")

        # 基于评分的建议
        score = feedback.get("score", 75)
        if score < 60:
            improvements.append("当前质量评分偏低, 建议重新审视学习目标和画像匹配度")

        return improvements

    def _generate_summary(
        self,
        goal: str,
        success: bool,
        score: float,
        achievements: List[str],
        improvements: List[str],
    ) -> str:
        """生成综合总结"""
        status = "✅ 达成" if success else "⚠️ 需改进"

        parts = [
            f"目标: {goal}",
            f"状态: {status} (评分: {score}/100)",
        ]

        if achievements:
            parts.append(f"成果: {'; '.join(achievements[:3])}")

        if improvements:
            parts.append(f"改进: {'; '.join(improvements[:3])}")

        return " | ".join(parts)
