"""
Phase 7 — ResourceRecommendationAgent: 个性化资源精准推送

职责: 读取 StudentMemory, 决定"给谁什么资源, 为什么给"。
     不负责生成资源 — 生成交给 ContentAgent。

输入:
  student_profile   — DynamicProfile dict
  mastery_map       — {concept: mastery_score}
  weak_points       — [{concept, error_type, occurrence_count}]
  learning_behavior — {avg_score, interaction_count, preferred_style}
  learning_plan     — LearningPlan.nodes (可选)

输出:
  PersonalizedResourcePlan — {today_goal, recommended_resources, reasoning}
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

RESOURCE_TYPES = {
    "lecture":     {"label": "讲解",       "icon": "📖"},
    "exercise":    {"label": "练习",       "icon": "📝"},
    "code_lab":    {"label": "代码实验",   "icon": "💻"},
    "visual":      {"label": "图解/动画",  "icon": "🎨"},
    "challenge":   {"label": "挑战任务",   "icon": "🏆"},
    "review":      {"label": "复习巩固",   "icon": "🔄"},
    "extended":    {"label": "拓展阅读",   "icon": "📚"},
}


@dataclass
class RecommendedResource:
    """单条推荐"""
    resource_type: str               # lecture | exercise | code_lab | visual | challenge | review | extended
    title: str                       # 资源标题
    concept: str = ""                # 关联概念
    reason: str = ""                 # 推荐理由 (可解释)
    priority: int = 5                # 优先级 1-10
    estimated_minutes: int = 15       # 预计时间
    content_hints: Dict[str, Any] = field(default_factory=dict)  # 传递给 ContentAgent 的提示

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_type": self.resource_type,
            "title": self.title,
            "concept": self.concept,
            "reason": self.reason,
            "priority": self.priority,
            "estimated_minutes": self.estimated_minutes,
            "content_hints": self.content_hints,
        }


@dataclass
class PersonalizedResourcePlan:
    """个性化资源计划"""
    student_id: str
    today_goal: str                     # 今日学习目标
    recommended_resources: List[RecommendedResource] = field(default_factory=list)
    total_minutes: int = 0              # 总时长
    mastery_summary: str = ""           # 掌握度摘要
    reasoning: str = ""                 # 整体推荐逻辑
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "today_goal": self.today_goal,
            "recommended_resources": [r.to_dict() for r in self.recommended_resources],
            "total_minutes": self.total_minutes,
            "mastery_summary": self.mastery_summary,
            "reasoning": self.reasoning,
            "generated_at": self.generated_at,
        }


@dataclass
class ResourceFeedback:
    """资源使用反馈 (用于后续优化推荐)"""
    resource_id: str
    student_id: str
    resource_type: str
    concept: str
    clicked: bool = False
    completed: bool = False
    score: int = 0
    time_spent: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "student_id": self.student_id,
            "resource_type": self.resource_type,
            "concept": self.concept,
            "clicked": self.clicked,
            "completed": self.completed,
            "score": self.score,
            "time_spent": self.time_spent,
            "timestamp": self.timestamp,
        }


# ──────────────────────────────────────────────
# 推荐引擎
# ──────────────────────────────────────────────

class ResourceRecommendationAgent:
    """
    个性化资源推荐 Agent.

    使用:
        agent = ResourceRecommendationAgent()
        plan = agent.recommend(
            student_id="s1",
            student_memory=mem,
            learning_plan_nodes=plan_nodes,
        )
        for r in plan.recommended_resources:
            print(f"{r.title}: {r.reason}")

    后续 (由外部调用):
        feedback = agent.record_feedback("s1", resource_id="res_1", ...)
    """

    MAX_RESOURCES = 8
    MAX_MINUTES = 90

    def __init__(self):
        self._feedback_store: Dict[str, List[ResourceFeedback]] = {}
        self._resource_counter: int = 0

    # ── 主入口 ──────────────────────────────

    def recommend(
        self,
        student_id: str,
        student_memory: Any,          # StudentMemory
        learning_plan_nodes: Optional[List[Any]] = None,  # List[PlanNode]
    ) -> PersonalizedResourcePlan:
        """
        生成个性化资源推荐.

        Args:
            student_id: 学生ID
            student_memory: StudentMemory 实例
            learning_plan_nodes: 当前 LearningPlan 节点列表 (可选)

        Returns:
            PersonalizedResourcePlan
        """
        # ── 提取关键信息 ──
        mastery = getattr(student_memory, "mastery_map", {})
        weak_points = getattr(student_memory, "weak_points", [])
        behavior = getattr(student_memory, "learning_behavior", {})
        profiles = getattr(student_memory, "profile_history", [])

        # 最新画像
        latest_profile = profiles[-1] if profiles else {}
        cognitive_style = latest_profile.get("cognitive_style", "visual_dominant")
        interaction = latest_profile.get("interaction_preference", "code_sandbox")
        knowledge = latest_profile.get("knowledge_base", "junior_dev")

        # ── 1. 按掌握度分层 ──
        resources: List[RecommendedResource] = []
        weak_concepts = [w.get("concept", "") for w in weak_points if w.get("concept")]

        # 从 learning_plan 或 mastery_map 提取关注概念
        if learning_plan_nodes:
            focus_concepts = [n.core_concept[:20] for n in learning_plan_nodes if hasattr(n, "core_concept")]
        else:
            focus_concepts = list(mastery.keys())[:5]

        # 按掌握度分类
        for concept in mastery:
            score = mastery[concept]
            if score < 0.3:
                resources.extend(self._recommend_for_weak(concept, cognitive_style))
            elif score < 0.8:
                resources.extend(self._recommend_for_growing(concept, cognitive_style, interaction))
            else:
                resources.extend(self._recommend_for_strong(concept, interaction))

        # ── 2. 弱点驱动推荐 ──
        for wp in weak_points[:3]:
            concept = wp.get("concept", "")
            if concept:
                resources.append(RecommendedResource(
                    resource_type="exercise",
                    title=f"「{concept}」专项训练",
                    concept=concept,
                    reason=f"历史错误 {wp.get('occurrence_count', 0)} 次, 需要强化",
                    priority=9,
                    estimated_minutes=20,
                ))

        # ── 3. 学习风格驱动 ──
        style_resources = self._recommend_by_style(cognitive_style, interaction)
        resources.extend(style_resources)

        # ── 4. 去重 + 优先级排序 ──
        seen = set()
        unique: List[RecommendedResource] = []
        for r in resources:
            key = (r.resource_type, r.title[:30])
            if key not in seen:
                seen.add(key)
                unique.append(r)
        unique.sort(key=lambda r: (-r.priority, r.estimated_minutes))

        # ── 5. 限制数量和时长 ──
        selected = []
        total = 0
        for r in unique:
            if len(selected) >= self.MAX_RESOURCES or total + r.estimated_minutes > self.MAX_MINUTES:
                break
            selected.append(r)
            total += r.estimated_minutes

        # ── 6. 生成计划 ──
        # 今日目标
        if weak_concepts:
            today_goal = f"攻克薄弱环节: {', '.join(weak_concepts[:2])}"
        elif mastery:
            weakest = min(mastery.items(), key=lambda x: x[1]) if mastery else ("新知识", 0)
            today_goal = f"重点学习: {weakest[0]} (掌握度 {weakest[1]:.0%})"
        else:
            today_goal = "今日新知识学习"

        # 掌握度摘要
        if mastery:
            low = sum(1 for s in mastery.values() if s < 0.3)
            med = sum(1 for s in mastery.values() if 0.3 <= s < 0.8)
            high = sum(1 for s in mastery.values() if s >= 0.8)
            mastery_summary = f"已掌握 {high} 个, 进行中 {med} 个, 薄弱 {low} 个"
        else:
            mastery_summary = "首次学习"

        # 整体推理
        reasoning_parts = [
            f"学生画像: {knowledge}/{cognitive_style}/{interaction}",
            f"薄弱概念数: {len(weak_points)}",
            f"推荐策略: {len(selected)} 个资源, 总计 {total} 分钟",
        ]
        reasoning = " | ".join(reasoning_parts)

        return PersonalizedResourcePlan(
            student_id=student_id,
            today_goal=today_goal,
            recommended_resources=selected,
            total_minutes=total,
            mastery_summary=mastery_summary,
            reasoning=reasoning,
        )

    # ── 分层推荐 ────────────────────────────

    def _recommend_for_weak(
        self, concept: str, cognitive_style: str
    ) -> List[RecommendedResource]:
        """薄弱概念 (mastery < 0.3) — 基础讲解 + 大量练习"""
        resources: List[RecommendedResource] = []

        # 基础讲解
        res_type = "lecture"
        hint = {}
        if cognitive_style == "visual_dominant":
            res_type = "visual"
            hint = {"require_diagram": True, "require_mermaid": True}

        resources.append(RecommendedResource(
            resource_type=res_type,
            title=f"「{concept}」基础讲解",
            concept=concept,
            reason=f"掌握度低 ({self._get_mastery_label(0.1)}), 需要从基础开始",
            priority=10,
            estimated_minutes=15,
            content_hints=hint,
        ))

        # 练习
        resources.append(RecommendedResource(
            resource_type="exercise",
            title=f"「{concept}」基础练习",
            concept=concept,
            reason="薄弱环节需要大量练习巩固",
            priority=9,
            estimated_minutes=20,
            content_hints={"exercise_count": 5, "difficulty": "basic"},
        ))

        return resources

    def _recommend_for_growing(
        self, concept: str, cognitive_style: str, interaction: str
    ) -> List[RecommendedResource]:
        """掌握中 (0.3-0.8) — 案例 + 强化"""
        resources: List[RecommendedResource] = []

        # 案例
        resources.append(RecommendedResource(
            resource_type="code_lab",
            title=f"「{concept}」实战案例",
            concept=concept,
            reason="掌握度中等, 通过实战加深理解",
            priority=7,
            estimated_minutes=15,
        ))

        # 强化练习
        resources.append(RecommendedResource(
            resource_type="exercise",
            title=f"「{concept}」强化训练",
            concept=concept,
            reason="需要进一步巩固",
            priority=6,
            estimated_minutes=15,
            content_hints={"exercise_count": 3, "difficulty": "intermediate"},
        ))

        return resources

    def _recommend_for_strong(
        self, concept: str, interaction: str
    ) -> List[RecommendedResource]:
        """已掌握 (≥0.8) — 拓展 + 挑战"""
        resources: List[RecommendedResource] = []

        resources.append(RecommendedResource(
            resource_type="extended",
            title=f"「{concept}」高阶拓展",
            concept=concept,
            reason="已掌握, 适合拓展视野",
            priority=4,
            estimated_minutes=10,
        ))

        resources.append(RecommendedResource(
            resource_type="challenge",
            title=f"「{concept}」挑战任务",
            concept=concept,
            reason="已掌握, 挑战更高难度",
            priority=3,
            estimated_minutes=15,
            content_hints={"difficulty": "advanced"},
        ))

        return resources

    def _recommend_by_style(
        self, cognitive_style: str, interaction: str
    ) -> List[RecommendedResource]:
        """学习风格驱动 — 无条件推荐匹配的通用资源"""
        resources: List[RecommendedResource] = []

        if cognitive_style == "visual_dominant":
            resources.append(RecommendedResource(
                resource_type="visual",
                title="知识点图解总览",
                concept="",
                reason="视觉学习偏好 — 提供 Mermaid 拓扑图和 ASCII 图解",
                priority=8,
                estimated_minutes=10,
                content_hints={"require_mermaid": True, "require_ascii": True},
            ))

        if interaction == "code_sandbox":
            resources.append(RecommendedResource(
                resource_type="code_lab",
                title="自由编程实验",
                concept="",
                reason="动手实践偏好 — 提供无限制编码环境",
                priority=7,
                estimated_minutes=15,
                content_hints={"sandbox_mode": True},
            ))

        if interaction == "quiz_first":
            resources.append(RecommendedResource(
                resource_type="exercise",
                title="自测挑战",
                concept="",
                reason="做题优先偏好 — 通过测试驱动学习",
                priority=7,
                estimated_minutes=10,
                content_hints={"quiz_mode": True},
            ))

        return resources

    # ── 反馈记录 ────────────────────────────

    def record_feedback(
        self,
        student_id: str,
        resource_id: str = "",
        resource_type: str = "",
        concept: str = "",
        clicked: bool = False,
        completed: bool = False,
        score: int = 0,
        time_spent: int = 0,
    ) -> ResourceFeedback:
        """记录资源使用反馈, 用于后续优化推荐"""
        rid = resource_id or f"res_{self._resource_counter}"
        self._resource_counter += 1

        fb = ResourceFeedback(
            resource_id=rid,
            student_id=student_id,
            resource_type=resource_type,
            concept=concept,
            clicked=clicked,
            completed=completed,
            score=score,
            time_spent=time_spent,
        )

        if student_id not in self._feedback_store:
            self._feedback_store[student_id] = []
        self._feedback_store[student_id].append(fb)

        return fb

    def get_feedback_for_student(self, student_id: str) -> List[ResourceFeedback]:
        return self._feedback_store.get(student_id, [])

    # ── 辅助 ────────────────────────────────

    @staticmethod
    def _get_mastery_label(score: float) -> str:
        if score < 0.3:
            return "薄弱"
        elif score < 0.8:
            return "进行中"
        return "已掌握"
