"""
Phase 5.3 — FeedbackLoop: UserSim → MetaReflector → Prompt 优化循环

流程:
  资源生成 → UserSimulation → 评分 & 问题提取
  ↓ (< 阈值)
  MetaReflector 召回教训 → 生成 Prompt 优化建议
  ↓
  FeedbackRecord 记录 → 优化后 Prompt → 下一轮生成
  直到评分 ≥ 阈值 或 达到最大轮数
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from .contracts import FeedbackRecord


class FeedbackLoop:
    """
    学习反馈闭环编排器.

    串联 UserSim 评分 → MetaReflector 召回 → Prompt 优化 → 下一轮生成.

    使用方式:
        loop = FeedbackLoop(sim_agent, reflector, threshold=70)
        record = loop.run_one_cycle(
            lecture_text="...",
            exercise_text="...",
            node_id="closures",
            original_prompt="...",
            cycle=1,
        )
        if record.sim_score >= loop.threshold:
            print("通过!")
        else:
            # 用 record.prompt_refinement 重新生成
            ...
    """

    MAX_CYCLES = 3  # 最多 3 轮反馈

    def __init__(
        self,
        sim_agent: Any,         # UserSimulationAgent
        reflector: Any = None,  # MetaReflectorAgent (可选)
        threshold: int = 70,    # 通关阈值
        max_cycles: int = 3,
    ):
        self.sim_agent = sim_agent
        self.reflector = reflector
        self.threshold = threshold
        self.max_cycles = max_cycles
        self._history: List[FeedbackRecord] = []

    # ── 主循环 ────────────────────────────────

    def run_one_cycle(
        self,
        lecture_text: str,
        exercise_text: str = "",
        node_id: str = "",
        original_prompt: str = "",
        target_concept: str = "",
        cycle: int = 1,
    ) -> FeedbackRecord:
        """
        运行一轮反馈循环.

        Args:
            lecture_text: 讲义全文
            exercise_text: 练习题文本
            node_id: 节点 ID
            original_prompt: 生成用的原始 Prompt
            target_concept: 目标概念
            cycle: 当前轮次

        Returns:
            FeedbackRecord
        """
        # ── Step 1: UserSim 评分 ──
        sim_result = self.sim_agent.simulate(
            lecture_text=lecture_text,
            exercise_text=exercise_text,
        )

        sim_score = sim_result.would_recommend_score
        top_issues = self._extract_top_issues(sim_result)

        record = FeedbackRecord(
            record_id=f"fb_{node_id}_c{cycle}",
            node_id=node_id,
            sim_score=sim_score,
            would_drop_out=sim_result.would_drop_out,
            revision_required=sim_result.revision_required,
            top_issues=top_issues,
            cycle_number=cycle,
        )

        # ── Step 2: 评分低于阈值 → MetaReflector ──
        if sim_score < self.threshold and self.reflector:
            self._apply_reflection(
                record=record,
                original_prompt=original_prompt,
                target_concept=target_concept,
                sim_result=sim_result,
            )

        # ── Step 3: 记录历史 ──
        self._history.append(record)

        return record

    # ── 辅助方法 ──────────────────────────────

    def _extract_top_issues(self, sim_result: Any) -> List[str]:
        """从 SimulationResult 提取 top 问题"""
        issues: List[str] = []

        # 认知负荷问题
        cog = sim_result.cognitive_load
        if cog.concept_density_warning and cog.concept_density_msg:
            issues.append(cog.concept_density_msg[:100])

        # 画像排异
        dislike = sim_result.profile_dislike
        issues.extend(dislike.dislikes_detected[:2])
        issues.extend(dislike.missing_expected_elements[:2])

        # 心智差额
        gaps = sim_result.mind_gaps
        issues.extend(gaps.gaps[:3])

        # 修改建议
        issues.extend(sim_result.revision_suggestions[:2])

        return issues[:5]  # 最多 5 个

    def _apply_reflection(
        self,
        record: FeedbackRecord,
        original_prompt: str,
        target_concept: str,
        sim_result: Any,
    ) -> None:
        """应用 MetaReflector 召回 + 生成优化建议"""
        if not self.reflector:
            return

        # 召回教训
        query = target_concept or record.node_id
        try:
            recalled = self.reflector.recall_lessons(query, n_results=3)
        except Exception:
            recalled = []

        record.recalled_lessons = [
            {
                "error_type": getattr(l, "error_type", ""),
                "root_cause": getattr(l, "root_cause_analysis", "")[:100],
                "lint_rule": getattr(l, "abstract_lint_rule", ""),
            }
            for l in recalled
        ]

        # 生成优化建议
        refinement = self._build_refinement(
            original_prompt=original_prompt,
            issues=record.top_issues,
            lessons=record.recalled_lessons,
            sim_score=record.sim_score,
        )

        record.prompt_refinement = refinement
        record.refinement_rationale = (
            f"评分 {record.sim_score} < 阈值 {self.threshold}, "
            f"召回 {len(recalled)} 条教训, "
            f"生成优化建议"
        )
        record.status = "OPTIMIZED"

    def _build_refinement(
        self,
        original_prompt: str,
        issues: List[str],
        lessons: List[Dict[str, Any]],
        sim_score: int,
    ) -> str:
        """基于问题和教训生成 Prompt 优化片段"""
        lines = ["\n# ====== FEEDBACK LOOP REFINEMENT ======"]

        if issues:
            lines.append(f"## 本轮评分: {sim_score}/100")
            lines.append("## 发现的 Top 问题:")
            for i, issue in enumerate(issues, 1):
                lines.append(f"  {i}. {issue}")

        if lessons:
            lines.append("## 历史教训 (MetaReflector 召回):")
            for j, lesson in enumerate(lessons, 1):
                lines.append(f"  {j}. [{lesson.get('error_type', '')}] "
                             f"{lesson.get('lint_rule', '')}")

        lines.append("## 优化指令:")
        lines.append("  请根据以上问题重新生成教学内容, 特别注意:")
        lines.append("  1. 控制概念密度 ≤ 3 个/节")
        lines.append("  2. 每个抽象概念配 ❌ vs ✅ 对比")
        lines.append("  3. 避免大段纯文字 (每 200 字后插入代码)")

        lines.append("# ====== END REFINEMENT ======\n")
        return "\n".join(lines)

    # ── 完整多轮循环 ──────────────────────────

    def run_full_loop(
        self,
        lecture_text: str,
        exercise_text: str = "",
        node_id: str = "",
        original_prompt: str = "",
        target_concept: str = "",
        regenerate_fn: Optional[Any] = None,
    ) -> List[FeedbackRecord]:
        """
        运行完整多轮反馈循环 (最多 MAX_CYCLES 轮).

        Args:
            lecture_text: 初始讲义
            exercise_text: 练习题
            node_id: 节点 ID
            original_prompt: 初始 Prompt
            target_concept: 目标概念
            regenerate_fn: 重新生成函数 (prompt, lecture) -> new_lecture

        Returns:
            所有轮次的 FeedbackRecord 列表
        """
        current_lecture = lecture_text
        current_prompt = original_prompt

        for cycle in range(1, self.max_cycles + 1):
            record = self.run_one_cycle(
                lecture_text=current_lecture,
                exercise_text=exercise_text,
                node_id=node_id,
                original_prompt=current_prompt,
                target_concept=target_concept,
                cycle=cycle,
            )

            # 检查是否通过
            if record.sim_score >= self.threshold:
                record.status = "APPLIED"
                break

            # 尝试重新生成 (如果有 regenerate_fn)
            if regenerate_fn and record.prompt_refinement:
                try:
                    refined_prompt = current_prompt + record.prompt_refinement
                    new_lecture = regenerate_fn(refined_prompt)
                    if new_lecture:
                        current_lecture = new_lecture
                        current_prompt = refined_prompt
                except Exception:
                    pass

        # 记录效果
        for i in range(1, len(self._history)):
            prev = self._history[i - 1]
            curr = self._history[i]
            curr.effect_delta = curr.sim_score - prev.sim_score

        return self._history

    @property
    def history(self) -> List[FeedbackRecord]:
        return self._history

    def clear_history(self) -> None:
        self._history = []


# ──────────────────────────────────────────────
# 便捷工厂
# ──────────────────────────────────────────────

def create_feedback_loop(
    sim_agent: Any,
    reflector: Any = None,
    threshold: int = 70,
) -> FeedbackLoop:
    """创建反馈循环实例"""
    return FeedbackLoop(
        sim_agent=sim_agent,
        reflector=reflector,
        threshold=threshold,
    )
