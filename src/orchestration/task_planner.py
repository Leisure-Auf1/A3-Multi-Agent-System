"""
Phase 9.3-A — Task Planner

Maps user requests and agent contexts to TaskType for model routing.

Usage:
    from src.orchestration.task_planner import TaskPlanner

    planner = TaskPlanner()
    task = planner.plan("帮我生成一份Python入门教材")
    # → TaskType.GENERATE_MATERIAL

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from src.config.task_capability import TaskType, TASK_LABELS


# ── Keyword → TaskType mapping ─────────────────────

# Ordered by specificity — more specific patterns first
_TASK_PATTERNS: List[tuple] = [
    # PPT generation
    (r"ppt|幻灯片|课件|演示文稿", TaskType.GENERATE_PPT),
    # Video generation
    (r"视频|录制|录课|动画", TaskType.GENERATE_VIDEO),
    # PDF export
    (r"导出.*pdf|pdf.*导出|打印|另存为pdf", TaskType.GENERATE_PDF),
    # Textbook export
    (r"教材导出|完整.*教材|导出.*教材", TaskType.EXPORT_TEXTBOOK),
    # Diagram / mindmap — BEFORE generic image (more specific)
    (r"流程图|架构图|示意图|图表|关系图", TaskType.CREATE_DIAGRAM),
    (r"思维导图|脑图|知识图谱", TaskType.CREATE_MINDMAP),
    # Image generation — AFTER specific diagram patterns
    (r"图片|插图|配图|生成.*图|画.*图", TaskType.GENERATE_IMAGE),
    # Material generation
    (r"教材|课程|讲义|教程|生成.*内容|教学.*内容", TaskType.GENERATE_MATERIAL),
    # Plan generation
    (r"规划|计划|路线|路径|安排|学习.*方案|制定", TaskType.GENERATE_PLAN),
    # Error analysis
    (r"错误.*分析|错题.*分析|分析.*错误|为什么.*错|错因", TaskType.ANALYZE_ERROR),
    # Grade answer
    (r"评分|打分|批改|评价|批阅", TaskType.GRADE_ANSWER),
    # Profile
    (r"画像|能力.*评估|水平.*测试|测试.*水平|学习.*诊断|测评", TaskType.GENERATE_PROFILE),
    # Video script
    (r"视频.*脚本|脚本.*视频|配音|旁白", TaskType.GENERATE_VIDEO_SCRIPT),
    # Teaching video
    (r"教学.*视频|课程.*视频|讲解.*视频", TaskType.GENERATE_TEACHING_VIDEO),
    # Image understanding
    (r"看.*图|图片.*分析|图片.*理解|识别.*图|图中|这张图", TaskType.IMAGE_UNDERSTANDING),
    # Video understanding
    (r"视频.*分析|视频.*理解|这个视频", TaskType.VIDEO_UNDERSTANDING),
    # RAG
    (r"搜索|查询|检索|查找|知识点", TaskType.RAG_RETRIEVAL),
]


# ── Agent → TaskType default mapping ──────────────

_AGENT_TASK_MAP: Dict[str, TaskType] = {
    "ProfileAgent":           TaskType.GENERATE_PROFILE,
    "PlannerAgent":           TaskType.GENERATE_PLAN,
    "ContentGeneratorAgent":  TaskType.GENERATE_MATERIAL,
    "PPTGeneratorAgent":      TaskType.GENERATE_PPT,
    "ImageGeneratorAgent":    TaskType.GENERATE_IMAGE,
    "VideoGeneratorAgent":    TaskType.GENERATE_VIDEO,
    "EvaluationAgent":        TaskType.GRADE_ANSWER,
    "ReflectionAgent":        TaskType.ANALYZE_ERROR,
    "ResourceAgent":          TaskType.RAG_RETRIEVAL,
    "TutorAgent":             TaskType.CHAT,
}


class TaskPlanner:
    """
    Plans which TaskType a user request maps to.

    Two modes:
    1. Explicit: agent_name → TaskType (via _AGENT_TASK_MAP)
    2. Inferred: user text → keyword matching → TaskType
    """

    def plan(
        self,
        user_request: str = "",
        agent_name: str = "",
        task_hint: str = "",
    ) -> TaskType:
        """
        Determine the TaskType for a request.

        Priority:
        1. task_hint (if it's a valid TaskType value)
        2. agent_name mapping
        3. user_request keyword matching
        4. default: CHAT

        Args:
            user_request: User's natural language request
            agent_name: Name of the calling agent (e.g. 'ContentGeneratorAgent')
            task_hint: Explicit task type hint

        Returns:
            TaskType value
        """
        # 1. Explicit task hint
        if task_hint:
            try:
                return TaskType(task_hint)
            except ValueError:
                pass

        # 2. Agent name mapping
        if agent_name:
            task = _AGENT_TASK_MAP.get(agent_name)
            if task:
                return task

        # 3. Keyword matching from user request
        if user_request:
            for pattern, task_type in _TASK_PATTERNS:
                if re.search(pattern, user_request, re.IGNORECASE):
                    return task_type

        # 4. Default
        return TaskType.CHAT

    def get_task_label(self, task_type: str) -> str:
        """Get human-readable label for a task type."""
        return TASK_LABELS.get(task_type, task_type)

    def get_required_capabilities(self, task_type: str) -> list:
        """Get required ModelCapability flags for a task type."""
        from src.config.task_capability import TASK_REQUIREMENTS
        return TASK_REQUIREMENTS.get(task_type, [])
