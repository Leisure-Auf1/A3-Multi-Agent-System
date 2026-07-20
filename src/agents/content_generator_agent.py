"""
Phase 8.3-A — ContentGeneratorAgent: 基于用户画像和 Planner 学习计划生成个性化教材

职责:
  输入: DynamicProfile + LearningPlan
  输出: TeachingMaterial (title, chapters, learning_objectives, concepts,
         explanation, examples, exercises, summary)

双模式:
  LLM 增强模式 — 调用 LLMProvider 生成高质量个性化教材
  Fallback 规则模式 — 基于计划节点生成结构化教材 (零延迟, 可解释)
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

@dataclass
class ConceptItem:
    """单个概念"""
    name: str
    description: str
    difficulty: str = "beginner"  # beginner | intermediate | advanced
    related: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "difficulty": self.difficulty,
            "related": self.related,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConceptItem":
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            difficulty=data.get("difficulty", "beginner"),
            related=data.get("related", []),
        )


@dataclass
class ExampleItem:
    """单个示例"""
    title: str
    code: str = ""
    explanation: str = ""
    expected_output: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "code": self.code,
            "explanation": self.explanation,
            "expected_output": self.expected_output,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExampleItem":
        return cls(
            title=data.get("title", ""),
            code=data.get("code", ""),
            explanation=data.get("explanation", ""),
            expected_output=data.get("expected_output", ""),
        )


@dataclass
class ExerciseItem:
    """单个练习"""
    question: str
    answer: str = ""
    hint: str = ""
    type: str = "open"  # open | multiple_choice | fill_blank | coding

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "hint": self.hint,
            "type": self.type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExerciseItem":
        return cls(
            question=data.get("question", ""),
            answer=data.get("answer", ""),
            hint=data.get("hint", ""),
            type=data.get("type", "open"),
        )


@dataclass
class Chapter:
    """教材中的一个章节"""
    chapter_id: str
    title: str
    explanation: str = ""
    concepts: List[ConceptItem] = field(default_factory=list)
    examples: List[ExampleItem] = field(default_factory=list)
    exercises: List[ExerciseItem] = field(default_factory=list)
    estimated_minutes: int = 20
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chapter_id": self.chapter_id,
            "title": self.title,
            "explanation": self.explanation,
            "concepts": [c.to_dict() for c in self.concepts],
            "examples": [e.to_dict() for e in self.examples],
            "exercises": [ex.to_dict() for ex in self.exercises],
            "estimated_minutes": self.estimated_minutes,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Chapter":
        return cls(
            chapter_id=data.get("chapter_id", ""),
            title=data.get("title", ""),
            explanation=data.get("explanation", ""),
            concepts=[ConceptItem.from_dict(c) for c in data.get("concepts", [])],
            examples=[ExampleItem.from_dict(e) for e in data.get("examples", [])],
            exercises=[ExerciseItem.from_dict(ex) for ex in data.get("exercises", [])],
            estimated_minutes=data.get("estimated_minutes", 20),
            summary=data.get("summary", ""),
        )


@dataclass
class TeachingMaterial:
    """完整教材输出"""
    material_id: str
    title: str
    learning_objectives: List[str] = field(default_factory=list)
    chapters: List[Chapter] = field(default_factory=list)
    overall_summary: str = ""
    target_profile: str = ""            # 画像摘要
    total_estimated_minutes: int = 0
    generation_source: str = "rule"     # rule | llm
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material_id": self.material_id,
            "title": self.title,
            "learning_objectives": self.learning_objectives,
            "chapters": [ch.to_dict() for ch in self.chapters],
            "overall_summary": self.overall_summary,
            "target_profile": self.target_profile,
            "total_estimated_minutes": self.total_estimated_minutes,
            "generation_source": self.generation_source,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TeachingMaterial":
        return cls(
            material_id=data.get("material_id", ""),
            title=data.get("title", ""),
            learning_objectives=data.get("learning_objectives", []),
            chapters=[Chapter.from_dict(ch) for ch in data.get("chapters", [])],
            overall_summary=data.get("overall_summary", ""),
            target_profile=data.get("target_profile", ""),
            total_estimated_minutes=data.get("total_estimated_minutes", 0),
            generation_source=data.get("generation_source", "rule"),
            metadata=data.get("metadata", {}),
        )


# ──────────────────────────────────────────────
# 教学策略映射 (fallback 规则模式)
# ──────────────────────────────────────────────

TEACHING_STRATEGY_EXPLANATIONS = {
    "visual": "采用图解方式，配合流程图和拓扑图直观展示概念",
    "standard": "分步骤拆解，每个概念逐步深入",
    "analogy": "通过类比和故事化叙述讲解抽象概念",
    "quiz_driven": "以问题驱动，先提问再解答",
}

# 认知风格 → 概念展开模板
CONCEPT_TEMPLATES = {
    "visual_dominant": "通过可视化方式理解 {concept}，配合图示和流程图",
    "text_linear": "按步骤逐层深入理解 {concept}，从基础到进阶",
    "auditory": "用类比和故事来讲解 {concept}，帮助建立直觉",
}

# 知识基础 → 解释深度
KB_DEPTH_MAP = {
    "junior_dev": "beginner",
    "mid_level": "intermediate",
    "senior": "advanced",
}


# ──────────────────────────────────────────────
# ContentGeneratorAgent
# ──────────────────────────────────────────────

class ContentGeneratorAgent:
    """
    个性化教材生成 Agent.

    基于学生画像 (DynamicProfile) 和 PlannerAgent 学习计划 (LearningPlan)
    生成完整的个性化教材，包含章节、概念、示例、练习和总结。

    使用方式:
        agent = ContentGeneratorAgent()
        material = agent.generate_material(profile, plan)
    """

    def __init__(self):
        self._llm_provider = None  # LLMProvider (optional, backward compat)
        self._orchestrator = None  # OrchestratorRuntime (preferred)

    # ── LLM Provider Injection ─────

    def set_llm_provider(self, provider: Any) -> None:
        """注入 LLMProvider 以启用 LLM 增强教材生成 (None = 纯规则模式)."""
        self._llm_provider = provider

    def set_orchestrator(self, orchestrator: Any) -> None:
        """注入 OrchestratorRuntime (Phase 9.3-B, 优先于 llm_provider)."""
        self._orchestrator = orchestrator

    # ── 主入口 ────────────────────

    def generate_material(
        self,
        profile: Any,       # DynamicProfile or dict
        plan: Any,          # LearningPlan or dict
        topic_focus: Optional[str] = None,
        student_goal: Any = None,  # Phase 8.3-D2: StudentGoal
    ) -> TeachingMaterial:
        """
        根据画像和学习计划生成个性化教材.

        LLM 可用时优先使用 LLM 生成高质量教材，失败时回退到规则模式。

        Args:
            profile: DynamicProfile 实例或 dict
            plan: LearningPlan 实例或 dict
            topic_focus: 可选主题焦点 (从 plan 的标题提取)
            student_goal: Phase 8.3-D2 — StudentGoal, 用于目标导向教材定制

        Returns:
            TeachingMaterial
        """
        # 统一为 dict
        profile_dict = profile.to_dict() if hasattr(profile, "to_dict") else profile
        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else plan

        # 尝试 LLM 生成
        if self._llm_provider is not None:
            try:
                material = self._generate_with_llm(profile_dict, plan_dict, topic_focus, student_goal)
                if material is not None:
                    return material
            except Exception:
                pass  # fallback to rule

        # 回退到规则模式
        return self.fallback_generate(profile_dict, plan_dict, topic_focus, student_goal)

    # ── LLM 增强生成 ──────────────

    LLM_GENERATE_PROMPT = """你是一个个性化教材编写专家。请根据以下学生画像和学习计划，生成一份完整的个性化教材。

[学生画像]
{profile_text}

[学习计划]
{plan_text}

[主题焦点]
{topic_focus}

请生成一份完整教材，输出纯 JSON：

{{
  "title": "教材标题 (与学习目标相关)",
  "learning_objectives": ["目标1", "目标2", "目标3"],
  "chapters": [
    {{
      "chapter_id": "ch1",
      "title": "章节标题",
      "explanation": "详细解释 (2-4段)",
      "concepts": [
        {{"name": "概念名", "description": "概念解释", "difficulty": "beginner|intermediate|advanced", "related": ["关联概念"]}}
      ],
      "examples": [
        {{"title": "示例标题", "code": "代码 (如有)", "explanation": "示例说明", "expected_output": "预期输出"}}
      ],
      "exercises": [
        {{"question": "练习题", "answer": "答案", "hint": "提示", "type": "open|multiple_choice|fill_blank|coding"}}
      ],
      "estimated_minutes": 30,
      "summary": "章节小结"
    }}
  ],
  "overall_summary": "整体总结 (2-3句)"
}}

要求:
- 根据画像的 cognitive_style 调整教学风格 (visual_dominant: 注重图解, text_linear: 分步讲解, auditory: 类比故事)
- 根据 knowledge_base 调整深度 (junior_dev: 基础, mid_level: 进阶, senior: 高级)
- 根据 error_prone_bias 重点覆盖薄弱领域
- 练习数量根据 learning_pace 调整 (fast_track: 1-2, normal: 2-3, deep_dive: 3-5)
- 所有内容用中文编写

只输出 JSON，不要任何额外文本。"""

    def _generate_with_llm(
        self,
        profile: Dict[str, Any],
        plan: Dict[str, Any],
        topic_focus: Optional[str] = None,
        student_goal: Any = None,  # Phase 8.3-D2
    ) -> Optional[TeachingMaterial]:
        """
        使用 LLMProvider 生成教材.
        Phase 8.3-D2: 如果 student_goal 存在，注入目标上下文到 LLM prompt。
        """
        if self._llm_provider is None:
            return None

        # 从 profile 提取关键信息
        profile_data = profile.get("profile", profile)
        kb = profile_data.get("knowledge_base", "junior_dev")
        cog = profile_data.get("cognitive_style", "visual_dominant")
        pace = profile_data.get("learning_pace", "normal")
        error_bias = profile_data.get("error_prone_bias", "")

        # 构建 profile 文本
        profile_text = (
            f"knowledge_base: {kb}\n"
            f"cognitive_style: {cog}\n"
            f"learning_pace: {pace}\n"
            f"error_prone_bias: {error_bias}\n"
            f"interaction_preference: {profile_data.get('interaction_preference', 'code_sandbox')}\n"
            f"frustration_threshold: {profile_data.get('frustration_threshold', 'medium')}"
        )

        # 构建 plan 文本
        nodes = plan.get("nodes", [])
        plan_lines = []
        for n in nodes:
            plan_lines.append(
                f"  - [{n.get('node_id', '')}] {n.get('title', '')}: "
                f"{n.get('core_concept', '')} "
                f"(depth={n.get('depth', 1)}, {n.get('estimated_minutes', 15)}min, "
                f"strategy={n.get('teaching_strategy', 'standard')})"
            )
        plan_text = (
            f"plan_id: {plan.get('plan_id', '')}\n"
            f"strategy: {plan.get('strategy_rationale', '')}\n"
            f"nodes:\n" + "\n".join(plan_lines) if plan_lines else "无特殊节点"
        )

        focus = topic_focus or plan.get("plan_id", "学习材料")

        prompt = self.LLM_GENERATE_PROMPT.format(
            profile_text=profile_text,
            plan_text=plan_text,
            topic_focus=focus,
        )

        try:
            # Phase 9.3-B: try orchestrator first, fall back to old provider
            if self._orchestrator is not None:
                result = self._orchestrator.execute(
                    task_type="generate_material",
                    prompt=prompt,
                    agent_name="ContentGeneratorAgent",
                    system_prompt="你是一个专业的教材编写专家。输出纯 JSON。",
                    temperature=0.3,
                    max_tokens=2048,
                )
                if result.success and result.content:
                    resp_content = result.content
                else:
                    return None
            elif self._llm_provider is not None:
                resp = self._llm_provider.generate(
                    prompt=prompt,
                    system_prompt="你是一个专业的教材编写专家。输出纯 JSON。",
                    temperature=0.3,
                    max_tokens=2048,
                )
                if not resp.success:
                    return None
                resp_content = resp.content
            else:
                return None

            content = resp_content.strip()
            # Strip markdown code fences
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:]) if len(lines) > 2 else content
                if content.endswith("```"):
                    content = content[:-3]

            data = json.loads(content)

            # Validate required fields
            if "title" not in data:
                return None

            material = self._dict_to_material(data, profile, plan)
            material.generation_source = "llm"
            return material

        except Exception:
            return None

    # ── Fallback 规则生成 ──────────

    def fallback_generate(
        self,
        profile: Dict[str, Any],
        plan: Dict[str, Any],
        topic_focus: Optional[str] = None,
        student_goal: Any = None,  # Phase 8.3-D2
    ) -> TeachingMaterial:
        """
        基于规则生成教材 (零延迟, 始终可用).

        根据 plan 中的节点和 profile 中的画像自动构建教材结构。
        Phase 8.3-D2: 如果 student_goal 存在，在标题和总结中体现目标。
        """
        profile_data = profile.get("profile", profile)
        kb = profile_data.get("knowledge_base", "junior_dev")
        cog = profile_data.get("cognitive_style", "visual_dominant")
        pace = profile_data.get("learning_pace", "normal")
        error_bias = profile_data.get("error_prone_bias", "")

        # 提取 plan 节点
        nodes = plan.get("nodes", [])
        plan_id = plan.get("plan_id", "material_default")

        # Phase 8.3-D2 — Extract goal context
        goal_target = ""
        goal_category = ""
        goal_pending_concepts: List[str] = []
        if student_goal is not None:
            goal_target = getattr(student_goal, "target", "")
            goal_category = getattr(student_goal, "category", "")
            goal_pending_concepts = getattr(
                student_goal, "get_pending_concepts", lambda: []
            )()

        # 构建标题 — include goal context
        if goal_target:
            title = f"🎯 {goal_target} — {topic_focus or '专项学习教材'}"
        else:
            title = topic_focus or f"个性化学习教材 — {plan.get('profile_summary', '')}"
        if not title or title == "个性化学习教材 — ":
            if nodes:
                title = f"个性化学习教材 — {nodes[0].get('title', '基础知识')}"
            else:
                title = "个性化学习教材"

        # 学习目标 — include goal targets
        learning_objectives = []
        if goal_target:
            learning_objectives.append(
                f"🎯 长期目标: {goal_target}"
            )
        for n in nodes:
            concept = n.get("core_concept", "")
            if concept:
                learning_objectives.append(f"理解并掌握 {concept}")

        # 章节: 每个 plan node → 一个 chapter
        chapters: List[Chapter] = []
        for i, node in enumerate(nodes):
            nid = node.get("node_id", f"ch{i + 1}")
            ntitle = node.get("title", f"第{i + 1}章")
            concept_text = node.get("core_concept", "")
            strategy = node.get("teaching_strategy", "standard")
            depth = node.get("depth", 1)
            est_min = node.get("estimated_minutes", 20)

            # 概念
            concepts = self._build_concepts(node, depth, cog)

            # 解释
            explanation = self._build_explanation(node, strategy, cog, depth)

            # 示例
            examples = self._build_examples(node, depth, kb)

            # 练习
            exercises = self._build_exercises(node, pace, depth)
            # 根据 pace 调整练习数量
            pace_limits = {"fast_track": 1, "normal": 3, "deep_dive": 5}
            max_ex = pace_limits.get(pace, 3)
            exercises = exercises[:max_ex]

            # 小结
            summary = self._build_summary(node, strategy)

            chapters.append(Chapter(
                chapter_id=nid,
                title=ntitle,
                explanation=explanation,
                concepts=concepts,
                examples=examples,
                exercises=exercises,
                estimated_minutes=est_min,
                summary=summary,
            ))

        # 整体总结 — include goal progress
        overall_summary = self._build_overall_summary(profile_data, nodes)
        if student_goal is not None:
            goal_progress = getattr(student_goal, "progress", 0.0)
            overall_summary += (
                f" 📚 当前目标进度: {goal_progress:.0%} — "
                f"继续加油，离目标更近一步！"
            )

        total_min = sum(ch.estimated_minutes for ch in chapters)

        profile_summary = f"{kb} / {cog} / {pace}"

        return TeachingMaterial(
            material_id=f"mat_{plan_id}",
            title=title,
            learning_objectives=learning_objectives,
            chapters=chapters,
            overall_summary=overall_summary,
            target_profile=profile_summary,
            total_estimated_minutes=total_min,
            generation_source="rule",
            metadata={
                "node_count": len(nodes),
                "chapter_count": len(chapters),
                "error_bias_covered": error_bias != "",
            },
        )

    # ── Fallback 构建辅助 ──────────

    def _build_concepts(
        self,
        node: Dict[str, Any],
        depth: int,
        cognitive: str,
    ) -> List[ConceptItem]:
        """根据节点构建概念列表"""
        concept_text = node.get("core_concept", "")
        if not concept_text:
            return []

        difficulty = "beginner"
        if depth >= 3:
            difficulty = "advanced"
        elif depth >= 2:
            difficulty = "intermediate"

        template = CONCEPT_TEMPLATES.get(cognitive, CONCEPT_TEMPLATES["text_linear"])
        description = template.format(concept=concept_text)

        # 拆分核心概念 (按逗号或"和"切)
        parts = [concept_text]
        for sep in ["和", "与", "、", "，", ","]:
            new_parts = []
            for p in parts:
                new_parts.extend(p.split(sep))
            parts = [p.strip() for p in new_parts if p.strip()]

        concepts = []
        for p in parts[:3]:  # 最多3个概念
            concepts.append(ConceptItem(
                name=p[:50],
                description=description if p == parts[0]
                else f"理解 {p} — 作为 {parts[0]} 的相关概念",
                difficulty=difficulty,
                related=[x for x in parts if x != p][:2],
            ))

        return concepts

    def _build_explanation(
        self,
        node: Dict[str, Any],
        strategy: str,
        cognitive: str,
        depth: int,
    ) -> str:
        """根据节点构建解释文本"""
        concept = node.get("core_concept", "")
        title = node.get("title", "")
        strategy_note = TEACHING_STRATEGY_EXPLANATIONS.get(strategy, "分步讲解")

        depth_label = {1: "基础", 2: "进阶", 3: "深入"}.get(depth, "基础")

        parts = [
            f"# {title}",
            f"本章将{depth_label}讲解 **{concept}**。",
            f"教学方式: {strategy_note}。",
        ]

        # cognitive style adjustments
        if cognitive == "visual_dominant":
            parts.append(
                "建议在学习时绘制流程图或思维导图，\n"
                "将抽象概念可视化以加深理解。"
            )
        elif cognitive == "text_linear":
            parts.append(
                "建议按照以下顺序逐步学习:\n"
                "1. 先理解核心定义\n"
                "2. 再通过示例验证\n"
                "3. 最后动手练习"
            )
        elif cognitive == "auditory":
            parts.append(
                "可以将这个概念类比为日常生活中的场景，\n"
                "通过类比建立直觉理解。"
            )

        # depth adjustments
        if depth >= 3:
            parts.append(
                "\n## 高级要点\n"
                "- 深入原理和底层实现\n"
                "- 常见陷阱和边界情况\n"
                "- 性能考量和最佳实践"
            )

        # error bias coverage
        error_bias = node.get("notes", "")
        if error_bias:
            parts.append(f"\n## 注意事项\n{error_bias}")

        return "\n\n".join(parts)

    def _build_examples(
        self,
        node: Dict[str, Any],
        depth: int,
        kb: str,
    ) -> List[ExampleItem]:
        """根据节点构建示例"""
        title = node.get("title", "概念")
        concept = node.get("core_concept", "")

        examples = []

        # 基础示例
        examples.append(ExampleItem(
            title=f"{title} — 基础示例",
            code=f"# 理解 {concept} 的基础用法\n# TODO: 根据具体概念补充代码",
            explanation=f"这是一个基础示例，展示 {concept} 的核心用法。",
            expected_output="按预期输出结果",
        ))

        # 进阶示例 (depth >= 2)
        if depth >= 2:
            examples.append(ExampleItem(
                title=f"{title} — 进阶示例",
                code=f"# {concept} 的进阶用法\n# 涵盖更多场景和组合使用",
                explanation=f"展示 {concept} 在实际项目中的进阶应用。",
                expected_output="进阶结果展示",
            ))

        # 高级示例 (depth >= 3 or senior)
        if depth >= 3 or kb == "senior":
            examples.append(ExampleItem(
                title=f"{title} — 高级示例",
                code=f"# {concept} 的高级用法与最佳实践",
                explanation=f"深入 {concept} 的高级特性和性能优化。",
                expected_output="优化后的结果",
            ))

        return examples

    def _build_exercises(
        self,
        node: Dict[str, Any],
        pace: str,
        depth: int,
    ) -> List[ExerciseItem]:
        """根据节点构建练习题"""
        concept = node.get("core_concept", "")
        title = node.get("title", "")

        exercises = []

        # 基础练习
        exercises.append(ExerciseItem(
            question=f"请用自己的话解释 {concept} 是什么？",
            answer=f"{concept} 是... (根据学习内容填写)",
            hint=f"思考 {title} 章节中的核心概念定义",
            type="open",
        ))

        # 填空练习
        exercises.append(ExerciseItem(
            question=f"{concept} 主要用于 ____ 场景，其核心机制是 ____。",
            answer=f"具体应用, 核心机制描述",
            hint=f"回顾 {title} 章节的示例",
            type="fill_blank",
        ))

        # coding 练习 (如果深度足够)
        if depth >= 2:
            exercises.append(ExerciseItem(
                question=f"编写代码演示 {concept} 的用法：\n输入: 给定的测试数据\n输出: 期望的处理结果",
                answer="参考章节示例代码",
                hint=f"先写出基本框架，再填入 {concept} 核心逻辑",
                type="coding",
            ))

        # 选择题
        exercises.append(ExerciseItem(
            question=f"关于 {concept}，以下说法正确的是：\n"
                     "A. 选项一\nB. 选项二\nC. 选项三\nD. 选项四",
            answer="正确答案",
            hint="仔细阅读章节解释部分",
            type="multiple_choice",
        ))

        # deep_dive 额外练习
        if pace == "deep_dive":
            exercises.append(ExerciseItem(
                question=f"思考题: {concept} 在实际项目中有哪些应用场景？"
                         "请设计一个综合案例。",
                answer="综合案例分析",
                hint="结合已学知识，设计一个端到端的应用",
                type="open",
            ))

        return exercises

    def _build_summary(self, node: Dict[str, Any], strategy: str) -> str:
        """构建章节小结"""
        title = node.get("title", "")
        concept = node.get("core_concept", "")
        notes = node.get("notes", "")

        parts = [f"本章学习了 **{title}**，核心概念是 **{concept}**。"]

        if notes:
            parts.append(f"重点提示: {notes}")

        parts.append("建议在掌握本章内容后，完成所有练习题以巩固理解。")

        return " ".join(parts)

    def _build_overall_summary(
        self,
        profile: Dict[str, Any],
        nodes: List[Dict[str, Any]],
    ) -> str:
        """构建整体总结"""
        kb = profile.get("knowledge_base", "junior_dev")
        node_titles = [n.get("title", "") for n in nodes[:5]]

        kb_labels = {
            "junior_dev": "初学者",
            "mid_level": "进阶学习者",
            "senior": "高级开发者",
        }

        label = kb_labels.get(kb, "学习者")
        topics = " → ".join(node_titles) if node_titles else "相关知识"

        return (
            f"本教材针对{label}设计，涵盖了 {topics} 的核心内容。\n"
            f"共 {len(nodes)} 个章节，建议按照顺序学习，每完成一章后完成对应练习。\n"
            f"掌握这些概念后，请继续探索更深入的主题。"
        )

    # ── LLM 结果转模型 ─────────────

    def _dict_to_material(
        self,
        data: Dict[str, Any],
        profile: Dict[str, Any],
        plan: Dict[str, Any],
    ) -> TeachingMaterial:
        """将 LLM 返回的 dict 转换为 TeachingMaterial"""
        profile_data = profile.get("profile", profile)
        kb = profile_data.get("knowledge_base", "junior_dev")
        cog = profile_data.get("cognitive_style", "visual_dominant")
        pace = profile_data.get("learning_pace", "normal")

        chapters = []
        for ch_data in data.get("chapters", []):
            chapters.append(Chapter(
                chapter_id=ch_data.get("chapter_id", ""),
                title=ch_data.get("title", ""),
                explanation=ch_data.get("explanation", ""),
                concepts=[ConceptItem.from_dict(c) for c in ch_data.get("concepts", [])],
                examples=[ExampleItem.from_dict(e) for e in ch_data.get("examples", [])],
                exercises=[ExerciseItem.from_dict(ex) for ex in ch_data.get("exercises", [])],
                estimated_minutes=ch_data.get("estimated_minutes", 20),
                summary=ch_data.get("summary", ""),
            ))

        total_min = sum(ch.estimated_minutes for ch in chapters)

        return TeachingMaterial(
            material_id=f"mat_{plan.get('plan_id', 'llm_gen')}",
            title=data.get("title", "个性化教材"),
            learning_objectives=data.get("learning_objectives", []),
            chapters=chapters,
            overall_summary=data.get("overall_summary", ""),
            target_profile=f"{kb} / {cog} / {pace}",
            total_estimated_minutes=total_min,
            generation_source="llm",
            metadata={"llm_generated": True},
        )
