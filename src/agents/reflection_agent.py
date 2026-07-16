"""
Phase 3 — ReflectionAgent: 执行后反思分析

职责:
  输入: 执行结果 (plan, resources, feedback)
  输出: 反思报告 (成功评估, 学习收获, 改进建议)

适用于 pipeline 执行完成后的总结性反思。
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


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
        pass

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

        # 生成总结
        summary = self._generate_summary(
            goal=goal,
            success=success,
            score=score,
            achievements=achievements,
            improvements=improvements,
        )

        return ReflectionResult(
            success=success,
            goal=goal,
            score=score,
            achievements=achievements,
            improvements=improvements,
            summary=summary,
        )

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
