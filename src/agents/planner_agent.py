"""
Phase 5.2 — PlannerAgent: DynamicProfile + 课程知识结构 → LearningPlan

职责:
  根据学生六维画像和课程知识结构，自动生成个性化学习路径。
  不同画像 → 不同路线 (概念顺序/深度/练习密度/路径分叉)。

输入:
  - DynamicProfile (六维画像)
  - 课程知识结构 (topics/knowledge_nodes)

输出:
  - LearningPlan (节点序列 + 元数据 + 路线推理)
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

@dataclass
class PlanNode:
    """学习路径中的一个节点"""
    node_id: str                          # 唯一标识
    title: str                            # 节点标题
    core_concept: str                     # 核心概念
    depth: int = 1                        # 学习深度 1-3 (浅/中/深)
    estimated_minutes: int = 15           # 预计学习时间
    required_concepts: List[str] = field(default_factory=list)  # 前置知识
    exercise_count: int = 3               # 练习题数量
    teaching_strategy: str = "standard"   # standard | visual | analogy | quiz_driven
    notes: str = ""                       # 教学备注

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "title": self.title,
            "core_concept": self.core_concept,
            "depth": self.depth,
            "estimated_minutes": self.estimated_minutes,
            "required_concepts": self.required_concepts,
            "exercise_count": self.exercise_count,
            "teaching_strategy": self.teaching_strategy,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PlanNode":
        return cls(
            node_id=data["node_id"],
            title=data["title"],
            core_concept=data.get("core_concept", ""),
            depth=data.get("depth", 1),
            estimated_minutes=data.get("estimated_minutes", 15),
            required_concepts=data.get("required_concepts", []),
            exercise_count=data.get("exercise_count", 3),
            teaching_strategy=data.get("teaching_strategy", "standard"),
            notes=data.get("notes", ""),
        )


@dataclass
class LearningPlan:
    """个性化学习路径"""
    plan_id: str                                      # 规划 ID
    profile_summary: str                              # 画像摘要
    nodes: List[PlanNode] = field(default_factory=list)
    total_minutes: int = 0                            # 总时长
    strategy_rationale: str = ""                      # 路线选择理由
    alternative_paths: List[str] = field(default_factory=list)  # 备选路径描述
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "profile_summary": self.profile_summary,
            "nodes": [n.to_dict() for n in self.nodes],
            "total_minutes": self.total_minutes,
            "strategy_rationale": self.strategy_rationale,
            "alternative_paths": self.alternative_paths,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningPlan":
        nodes = [PlanNode.from_dict(n) for n in data.get("nodes", [])]
        return cls(
            plan_id=data["plan_id"],
            profile_summary=data.get("profile_summary", ""),
            nodes=nodes,
            total_minutes=data.get("total_minutes", 0),
            strategy_rationale=data.get("strategy_rationale", ""),
            alternative_paths=data.get("alternative_paths", []),
            metadata=data.get("metadata", {}),
        )


# ──────────────────────────────────────────────
# 教学策略映射表
# ──────────────────────────────────────────────

# 认知风格 → 教学策略
COGNITIVE_TEACHING_MAP = {
    "visual_dominant": "visual",     # 图解/字符画/拓扑图
    "text_linear": "standard",       # 分步拆解
    "auditory": "analogy",           # 类比/故事化
}

# 学习节奏 → 深度/练习密度调整
PACE_ADJUSTMENTS = {
    "fast_track": {"depth_offset": -1, "exercise_offset": -1, "skip_detail_nodes": True},
    "normal":     {"depth_offset": 0,  "exercise_offset": 0,  "skip_detail_nodes": False},
    "deep_dive":  {"depth_offset": 1,  "exercise_offset": 2,  "skip_detail_nodes": False},
}

# 知识基础 → 起始节点调整
BASE_START_OFFSET = {
    "junior_dev": 0,    # 从第一课开始
    "mid_level": 1,     # 跳过基础概念
    "senior": 2,        # 跳过更多
}


# ──────────────────────────────────────────────
# PlannerAgent
# ──────────────────────────────────────────────

class PlannerAgent:
    """
    个性化学习路径规划 Agent.

    使用方式:
        agent = PlannerAgent(knowledge_graph={...})
        plan = agent.plan(profile, topics=["decorators", "closures"])
    """

    # ── 预置课程知识结构示例 ──

    DEFAULT_KNOWLEDGE_GRAPH: Dict[str, Dict[str, Any]] = {
        "python_basics": {
            "title": "Python 基础",
            "topics": [
                {"id": "var_types", "title": "变量与数据类型",
                 "concept": "理解 Python 的基本数据类型和变量赋值机制",
                 "required": [], "base_depth": 2, "base_minutes": 15},
                {"id": "control_flow", "title": "条件与循环",
                 "concept": "掌握 if/else 分支和 for/while 循环",
                 "required": ["var_types"], "base_depth": 2, "base_minutes": 20},
                {"id": "functions", "title": "函数定义与调用",
                 "concept": "理解函数封装、参数传递和返回值",
                 "required": ["control_flow"], "base_depth": 2, "base_minutes": 25},
                {"id": "data_structures", "title": "列表与字典",
                 "concept": "掌握 list/dict/set/tuple 四大数据结构",
                 "required": ["var_types"], "base_depth": 2, "base_minutes": 30},
            ],
        },
        "python_advanced": {
            "title": "Python 进阶",
            "topics": [
                {"id": "closures", "title": "闭包与作用域",
                 "concept": "理解函数闭包、自由变量和 LEGB 作用域规则",
                 "required": ["functions"], "base_depth": 3, "base_minutes": 30},
                {"id": "decorators_intro", "title": "装饰器入门",
                 "concept": "理解装饰器是接受函数返回函数的语法糖",
                 "required": ["closures"], "base_depth": 3, "base_minutes": 25},
                {"id": "decorators_advanced", "title": "带参装饰器与类装饰器",
                 "concept": "掌握三层嵌套装饰器和 __call__ 类装饰器",
                 "required": ["decorators_intro"], "base_depth": 3, "base_minutes": 35},
                {"id": "generators", "title": "生成器与迭代器",
                 "concept": "理解 yield、迭代器协议和惰性求值",
                 "required": ["functions"], "base_depth": 3, "base_minutes": 25},
                  ],
        },
        "multi_agent_ai": {
            "title": "Multi-Agent AI 系统开发",
            "topics": [
                # Level 1 — LLM Fundamentals
                {"id": "llm_basics", "title": "LLM 基础原理",
                 "concept": "理解大语言模型的 token、context window、prompting 机制",
                 "required": [], "base_depth": 2, "base_minutes": 20},
                {"id": "prompt_engineering", "title": "Prompt 工程",
                 "concept": "掌握 System Prompt、Few-shot、Chain-of-Thought 设计模式",
                 "required": ["llm_basics"], "base_depth": 2, "base_minutes": 25},
                {"id": "llm_interaction", "title": "模型交互与 API",
                 "concept": "通过 API 调用 LLM，处理 streaming、rate limiting、fallback",
                 "required": ["llm_basics"], "base_depth": 2, "base_minutes": 20},
                # Level 2 — Agent Fundamentals
                {"id": "agent_loop", "title": "Agent 主循环",
                 "concept": "理解 Agent 的 observe→think→act 循环和 ReAct 模式",
                 "required": ["prompt_engineering", "llm_interaction"], "base_depth": 2, "base_minutes": 30},
                {"id": "tool_calling", "title": "Tool Calling 与 Function Calling",
                 "concept": "Agent 如何调用外部工具：search、execute、read/write 模式",
                 "required": ["agent_loop"], "base_depth": 3, "base_minutes": 30},
                {"id": "agent_planning", "title": "Agent 规划与推理",
                 "concept": "Task decomposition、goal tracking、Plan-and-Execute 策略",
                 "required": ["agent_loop"], "base_depth": 3, "base_minutes": 25},
                # Level 3 — Multi-Agent Architecture
                {"id": "agent_roles", "title": "Agent 角色分工",
                 "concept": "设计 Agent 角色：Planner、Executor、Reviewer、Logger 职责划分",
                 "required": ["agent_planning", "tool_calling"], "base_depth": 3, "base_minutes": 25},
                {"id": "agent_communication", "title": "Agent 通信模式",
                 "concept": "EventBus 事件驱动、消息队列、共享 Memory、直接调用等通信范式",
                 "required": ["agent_roles"], "base_depth": 3, "base_minutes": 30},
                {"id": "task_decomposition", "title": "任务分解与协作",
                 "concept": "大规模任务拆解为子任务、Agent 间协作调度、Orchestrator 模式",
                 "required": ["agent_roles"], "base_depth": 3, "base_minutes": 30},
                # Level 4 — Runtime Engineering
                {"id": "eventbus_arch", "title": "EventBus 架构设计",
                 "concept": "设计 Agent 事件总线：emit/sync/trace/persist 完整链路",
                 "required": ["agent_communication"], "base_depth": 3, "base_minutes": 35},
                {"id": "memory_management", "title": "Memory 管理",
                 "concept": "StudentMemory + ExperienceMemory：profile mastery EMA、经验召回、JSON→Vector 迁移",
                 "required": ["agent_communication"], "base_depth": 3, "base_minutes": 30},
                {"id": "state_persistence", "title": "状态持久化",
                 "concept": "Agent 会话状态存储、Trace 持久化、跨会话恢复",
                 "required": ["eventbus_arch"], "base_depth": 2, "base_minutes": 25},
                {"id": "trace_observability", "title": "Trace 可观测性",
                 "concept": "AgentTraceCollector：reasoning_type 标记、latency 追踪、decision 解释",
                 "required": ["eventbus_arch"], "base_depth": 2, "base_minutes": 25},
                # Level 5 — Production Optimization
                {"id": "evaluation_systems", "title": "Agent 评估体系",
                 "concept": "4-dim 评分：correctness/personalization/explainability/efficiency — RuleJudge + LLMJudge",
                 "required": ["trace_observability", "state_persistence"], "base_depth": 3, "base_minutes": 30},
                {"id": "reflection_loop", "title": "反思与改进循环",
                 "concept": "MetaReflector 根因分析 → ExperienceMemory → ImprovementLoop → 策略更新",
                 "required": ["evaluation_systems"], "base_depth": 3, "base_minutes": 30},
                {"id": "system_optimization", "title": "系统优化",
                 "concept": "吞吐量调优、成本控制、Pipeline 并行化、生产部署最佳实践",
                 "required": ["reflection_loop"], "base_depth": 2, "base_minutes": 25},
            ],
        },
    }

    # ── 课程自动检测关键词 ──
    COURSE_KEYWORDS: Dict[str, List[str]] = {
        "multi_agent_ai": [
            "multi-agent", "multi agent", "agent system", "agent 系统",
            "multiagent", "多智能体", "多 agent", "智能体开发",
            "智能体", "agent开发", "agent 开发", "ai agent",
            "llm application", "llm app", "大模型应用", "大模型开发",
            "autonomous agent", "自主 agent", "agent architecture",
            "agent 架构", "agent协作", "agent 协作", "agent",
        ],
        "python_advanced": [
            "python", "Python", "装饰器", "闭包", "生成器",
            "迭代器", "decorator", "closure", "generator",
        ],
        "python_basics": [
            "python基础", "Python基础", "入门", "变量",
            "函数", "循环", "条件", "列表", "字典",
        ],
    }

    def __init__(
        self,
        knowledge_graph: Optional[Dict[str, Dict[str, Any]]] = None,
        kb_loader: Any = None,  # CourseKnowledgeBase (optional)
    ):
        self.knowledge_graph = knowledge_graph or self.DEFAULT_KNOWLEDGE_GRAPH
        self._kb_loader = kb_loader
        self._kb_loaded = False

    # ── Knowledge Base Integration (Phase 11.5) ─

    def load_kb(
        self,
        kb_path: str = "",
        force: bool = False,
    ) -> bool:
        """
        Load the course knowledge base from file.

        When loaded, plan() will prefer KB topics over hardcoded graph.
        Falls back to DEFAULT_KNOWLEDGE_GRAPH if KB loading fails.

        Args:
            kb_path: Path to KB directory (auto-discovers if empty).
            force: Force reload even if already loaded.

        Returns:
            True if KB was loaded successfully.
        """
        if self._kb_loaded and not force:
            return True

        try:
            from src.core.course_kb_loader import CourseKnowledgeBase
            self._kb_loader = CourseKnowledgeBase(kb_path) if kb_path else CourseKnowledgeBase()
            course = self._kb_loader.load()
            if course and course.chapters:
                # Merge KB into knowledge_graph
                kb_graph = self._kb_loader.to_knowledge_graph()
                self.knowledge_graph.update(kb_graph)
                self._kb_loaded = True
                return True
        except Exception:
            pass
        return False

    @property
    def kb_available(self) -> bool:
        return self._kb_loaded and self._kb_loader is not None

    def get_kb(self) -> Any:
        """Get the loaded CourseKnowledgeBase (or None)."""
        return self._kb_loader if self._kb_loaded else None

    def plan_from_kb(
        self,
        profile: Any,
        course_id: str = "ai_ma_101",
        **kwargs,
    ) -> "LearningPlan":
        """
        Generate a learning path from the knowledge base.

        Automatically loads KB if not yet loaded.
        Falls back to hardcoded graph if KB unavailable.

        Args:
            profile: DynamicProfile instance.
            course_id: Course ID from KB.
            **kwargs: Passed to plan().

        Returns:
            LearningPlan
        """
        if not self._kb_loaded:
            self.load_kb()

        return self.plan(profile, course_id=course_id, **kwargs)

    # ── 主入口 ────────────────────────────────

    def plan(
        self,
        profile: Any,                     # DynamicProfile
        course_id: str = "",
        topic_filter: Optional[List[str]] = None,
        student_memory: Any = None,       # StudentMemory (optional)
        goal_text: str = "",              # 学生目标文本 (用于自动检测课程)
    ) -> LearningPlan:
        """
        生成个性化学习路径.

        Args:
            profile: DynamicProfile 实例
            course_id: 课程 ID (留空时从 goal_text 自动检测, 默认 "python_advanced")
            topic_filter: 可选话题过滤器
            student_memory: StudentMemory (可选, 用于读取 mastery_map)
            goal_text: 学生目标文本 (用于自动检测课程, 如 "学习 Multi-Agent AI")

        Returns:
            LearningPlan
        """
        profile_dict = profile.to_dict() if hasattr(profile, "to_dict") else profile

        # 0. 课程自动检测
        if not course_id:
            course_id = self.detect_course(goal_text, profile_dict)

        # 1. 获取课程话题
        course = self.knowledge_graph.get(course_id, {})
        all_topics = course.get("topics", [])

        # 2. 按画像过滤/重排
        if topic_filter:
            all_topics = [t for t in all_topics if t["id"] in topic_filter]

        # 3. 应用节奏调整
        pace = profile_dict.get("learning_pace", "normal")
        pace_adj = PACE_ADJUSTMENTS.get(pace, PACE_ADJUSTMENTS["normal"])

        # 4. 应用认知风格 → 教学策略
        cognitive = profile_dict.get("cognitive_style", "visual_dominant")
        teaching_strategy = COGNITIVE_TEACHING_MAP.get(cognitive, "standard")

        # 5. 应用知识基础 → 起始偏移
        knowledge = profile_dict.get("knowledge_base", "junior_dev")
        start_offset = BASE_START_OFFSET.get(knowledge, 0)

        # 5b. 读取 Memory mastery_map
        mastery = {}
        if student_memory and hasattr(student_memory, "mastery_map"):
            mastery = student_memory.mastery_map

        # 6. 构建节点 — 受 mastery_map 影响
        nodes: List[PlanNode] = []
        skipped_by_mastery: List[str] = []
        for i, topic in enumerate(all_topics):
            if i < start_offset and pace_adj["skip_detail_nodes"]:
                continue

            tid = topic["id"]

            # ── mastery 影响 ──
            topic_mastery = mastery.get(tid, -1)

            # 已掌握 (≥0.8) → 跳过或极简
            if topic_mastery >= 0.8:
                skipped_by_mastery.append(tid)
                continue

            # 掌握中 (0.5-0.8) → 降低深度
            depth_mod = 0
            if 0.5 <= topic_mastery < 0.8:
                depth_mod = -1
            elif 0 < topic_mastery <= 0.3:
                # 薄弱 → 增加深度和练习
                depth_mod = 1

            depth = max(1, min(3,
                topic.get("base_depth", 2) + pace_adj["depth_offset"] + depth_mod
            ))

            # 练习量：薄弱概念加练
            exercise_mod = 2 if 0 < topic_mastery <= 0.3 else 0
            exercise_count = max(1,
                topic.get("exercise_count", 3) + pace_adj["exercise_offset"] + exercise_mod
            )

            # 薄弱概念延长学习时间
            time_mod = 5 if 0 < topic_mastery <= 0.3 else 0
            estimated_minutes = max(10,
                topic.get("base_minutes", 20)
                + pace_adj["depth_offset"] * 5
                + time_mod
            )

            nodes.append(PlanNode(
                node_id=tid,
                title=topic["title"],
                core_concept=topic.get("concept", ""),
                depth=depth,
                estimated_minutes=estimated_minutes,
                required_concepts=topic.get("required", []),
                exercise_count=exercise_count,
                teaching_strategy=teaching_strategy,
                notes=self._generate_notes(profile_dict, topic, teaching_strategy),
            ))

        # 7. 计算总时长
        total_minutes = sum(n.estimated_minutes for n in nodes)

        # 8. 生成路线推理
        rationale = self._generate_rationale(profile_dict, nodes, pace, cognitive)

        # 补充 memory 跳过信息
        if skipped_by_mastery:
            rationale += f" | 已掌握跳过: {', '.join(skipped_by_mastery)}"

        # 9. 生成备选路径
        alternatives = self._generate_alternatives(profile_dict, all_topics)

        return LearningPlan(
            plan_id=f"plan_{course_id}_{profile_dict.get('learning_pace', 'normal')}",
            profile_summary=f"{profile_dict.get('knowledge_base')} / "
                           f"{profile_dict.get('cognitive_style')} / "
                           f"{profile_dict.get('learning_pace')}",
            nodes=nodes,
            total_minutes=total_minutes,
            strategy_rationale=rationale,
            alternative_paths=alternatives,
            metadata={
                "course_id": course_id,
                "profile": profile_dict,
                "pace_adj": pace_adj,
                "teaching_strategy": teaching_strategy,
                "start_offset": start_offset,
            },
        )

    # ── 课程检测 ──────────────────────────────

    def detect_course(
        self,
        goal_text: str = "",
        profile_dict: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        根据学生目标文本和画像推断最合适的课程.

        检测优先级:
          1. Multi-Agent AI 关键词
          2. Python 高级关键词
          3. Python 基础关键词
          4. 默认: python_advanced

        Args:
            goal_text: 学生目标文本
            profile_dict: 画像字典 (可选, 用于知识基础辅助判断)

        Returns:
            course_id
        """
        text = (goal_text or "").lower()

        # 按优先级扫描
        for course_id in ["multi_agent_ai", "python_advanced", "python_basics"]:
            keywords = self.COURSE_KEYWORDS.get(course_id, [])
            for kw in keywords:
                if kw.lower() in text:
                    return course_id

        # 无匹配: 根据知识基础选默认
        if profile_dict:
            kb = profile_dict.get("knowledge_base", "")
            if kb == "junior_dev":
                return "python_basics"
        return "python_advanced"

    # ── 辅助方法 ──────────────────────────────

    def _generate_notes(
        self,
        profile: Dict[str, str],
        topic: Dict[str, Any],
        strategy: str,
    ) -> str:
        """根据画像生成教学备注"""
        notes_parts = [f"策略: {strategy}"]

        if profile.get("cognitive_style") == "visual_dominant":
            notes_parts.append("使用 ASCII 字符画展示结构")
        if profile.get("frustration_threshold") == "low":
            notes_parts.append("温和语气, 正向反馈, 小步验证")
        if profile.get("error_prone_bias") == "magic_syntax_blind":
            notes_parts.append("每个抽象语法配 ❌/✅ 对比")

        return "; ".join(notes_parts)

    def _generate_rationale(
        self,
        profile: Dict[str, str],
        nodes: List[PlanNode],
        pace: str,
        cognitive: str,
    ) -> str:
        """生成路线选择理由"""
        pace_desc = {
            "fast_track": "快速通道 — 跳过冗余铺垫, 直击核心",
            "normal": "标准路径 — 循序渐进",
            "deep_dive": "深潜模式 — 每个概念深挖底层",
        }
        cog_desc = {
            "visual_dominant": "视觉图解驱动",
            "text_linear": "文本线性阅读",
            "auditory": "类比故事驱动",
        }

        parts = [
            f"路线: {pace_desc.get(pace, '标准')}",
            f"风格: {cog_desc.get(cognitive, '标准')}",
            f"节点数: {len(nodes)}",
        ]

        if profile.get("frustration_threshold") == "low":
            parts.append("额外: 高频正向反馈, 每节点 ≤ 2 个新概念")

        return " | ".join(parts)

    def _generate_alternatives(
        self,
        profile: Dict[str, str],
        all_topics: List[Dict[str, Any]],
    ) -> List[str]:
        """生成备选路径"""
        alts = []

        # 备选 1: 不同的深度
        if profile.get("learning_pace") != "deep_dive":
            alts.append("深潜路线: 每个节点增加底层原理演示 (推荐给底层控)")
        if profile.get("learning_pace") != "fast_track":
            alts.append("快速路线: 跳过细节, 直接实战驱动 (推荐给赶时间者)")

        # 备选 2: 不同的教学风格
        cognitive = profile.get("cognitive_style", "")
        if cognitive != "visual_dominant":
            alts.append("视觉路线: 全部使用拓扑图和 ASCII 图解")
        if cognitive != "text_linear":
            alts.append("文本路线: 线性分步拆解, 代码注释铺满")

        return alts

    # ── 批量生成 ──────────────────────────────

    def plan_for_multiple_profiles(
        self,
        profiles: List[Dict[str, str]],
        course_id: str = "python_advanced",
    ) -> Dict[str, LearningPlan]:
        """
        为多个画像批量生成学习路径.
        用于展示 "同一课程, 不同路径" 的效果.
        """
        from src.core.agent_router import DynamicProfile

        plans = {}
        for pdata in profiles:
            if isinstance(pdata, DynamicProfile):
                profile = pdata
            else:
                profile = DynamicProfile(**pdata)
            plan = self.plan(profile, course_id=course_id)
            plans[plan.plan_id] = plan
        return plans
