"""
Phase 8.3-E2-B — Task Capability Mapping

Maps A3 Agent task types to required ModelCapability sets.
Used by ModelRouter and check_task_capability() for
capability-driven model selection.

Design:
- TaskType enum for all agent tasks
- TASK_REQUIREMENTS maps each task to required capabilities
- Used by ModelRouter.find_models(task) and check_task_capability()

Constraints: does NOT modify Veritas-Core or src/core/
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, List

from .model_capability import ModelCapability


# ──────────────────────────────────────────────
# Task Types
# ──────────────────────────────────────────────

class TaskType(str, Enum):
    """A3 Agent task types — each requires a subset of model capabilities."""

    GENERATE_PROFILE = "generate_profile"       # 画像提取
    GENERATE_PLAN = "generate_plan"             # 学习路径规划
    GENERATE_MATERIAL = "generate_material"      # AI 教材生成
    GENERATE_IMAGE = "generate_image"            # 图片生成
    GENERATE_PPT = "generate_ppt"                # PPT 文档生成
    GENERATE_VIDEO = "generate_video"            # 教学视频生成
    GRADE_ANSWER = "grade_answer"               # 作业评分
    ANALYZE_ERROR = "analyze_error"             # 错误分析
    RAG_RETRIEVAL = "rag_retrieval"             # 知识检索
    CHAT = "chat"                               # 通用对话
    # Phase 8.3-E3-A — multimodal task types
    CREATE_DIAGRAM = "create_diagram"            # 图表/流程图创建
    CREATE_MINDMAP = "create_mindmap"            # 思维导图
    GENERATE_PDF = "generate_pdf"                # PDF 教材导出
    EXPORT_TEXTBOOK = "export_textbook"          # 完整教材导出
    GENERATE_VIDEO_SCRIPT = "generate_video_script"  # 教学视频脚本
    GENERATE_TEACHING_VIDEO = "generate_teaching_video"  # 教学视频生成
    IMAGE_UNDERSTANDING = "image_understanding"   # 图片理解与分析
    VIDEO_UNDERSTANDING = "video_understanding"   # 视频理解与分析


C = ModelCapability  # shorthand

# ──────────────────────────────────────────────
# Task → Required Capabilities
# ──────────────────────────────────────────────

TASK_REQUIREMENTS: Dict[str, List[ModelCapability]] = {

    # 画像提取: basic text generation
    TaskType.GENERATE_PROFILE: [
        C.TEXT_GENERATION,
    ],

    # 学习路径规划: text + reasoning for complex planning
    TaskType.GENERATE_PLAN: [
        C.TEXT_GENERATION,
        C.REASONING,
    ],

    # 教材生成: text + long context for comprehensive material
    TaskType.GENERATE_MATERIAL: [
        C.TEXT_GENERATION,
        C.LONG_CONTEXT,
    ],

    # 图片生成: requires image generation capability
    TaskType.GENERATE_IMAGE: [
        C.IMAGE_GENERATION,
    ],

    # PPT 生成: document generation + tool calling for structured output
    TaskType.GENERATE_PPT: [
        C.PPT_GENERATION,
        C.TOOL_CALLING,
    ],

    # 视频生成: video generation + long context for scripts
    TaskType.GENERATE_VIDEO: [
        C.VIDEO_GENERATION,
    ],

    # 作业评分: text + reasoning for accurate grading
    TaskType.GRADE_ANSWER: [
        C.TEXT_GENERATION,
        C.REASONING,
    ],

    # 错误分析: text + reasoning for root cause analysis
    TaskType.ANALYZE_ERROR: [
        C.TEXT_GENERATION,
        C.REASONING,
    ],

    # 知识检索: text generation (embedding handled by separate vector store)
    TaskType.RAG_RETRIEVAL: [
        C.TEXT_GENERATION,
    ],

    # 通用对话: minimal requirement
    TaskType.CHAT: [
        C.TEXT_GENERATION,
    ],

    # ── Phase 8.3-E3-A: Multimodal task requirements ──

    # 图表创建: image generation + text
    TaskType.CREATE_DIAGRAM: [
        C.IMAGE_GENERATION,
        C.TEXT_GENERATION,
    ],

    # 思维导图: image generation (structured visual)
    TaskType.CREATE_MINDMAP: [
        C.IMAGE_GENERATION,
    ],

    # PDF导出: document generation (PDF-specific)
    TaskType.GENERATE_PDF: [
        C.PDF_GENERATION,
    ],

    # 完整教材导出: document + long context
    TaskType.EXPORT_TEXTBOOK: [
        C.DOCUMENT_GENERATION,
        C.LONG_CONTEXT,
    ],

    # 视频脚本: text + reasoning (script writing, no video gen needed)
    TaskType.GENERATE_VIDEO_SCRIPT: [
        C.TEXT_GENERATION,
        C.REASONING,
    ],

    # 教学视频: actual video generation
    TaskType.GENERATE_TEACHING_VIDEO: [
        C.VIDEO_GENERATION,
    ],

    # 图片理解: image input (vision) + text
    TaskType.IMAGE_UNDERSTANDING: [
        C.IMAGE_INPUT,
        C.TEXT_GENERATION,
    ],

    # 视频理解: video input + text
    TaskType.VIDEO_UNDERSTANDING: [
        C.VIDEO_INPUT,
        C.TEXT_GENERATION,
    ],
}


# ──────────────────────────────────────────────
# Task Labels (for UI display)
# ──────────────────────────────────────────────

TASK_LABELS: Dict[str, str] = {
    TaskType.GENERATE_PROFILE: "画像提取",
    TaskType.GENERATE_PLAN: "学习路径规划",
    TaskType.GENERATE_MATERIAL: "AI教材生成",
    TaskType.GENERATE_IMAGE: "图片生成",
    TaskType.GENERATE_PPT: "PPT文档生成",
    TaskType.GENERATE_VIDEO: "教学视频生成",
    TaskType.GRADE_ANSWER: "作业评分",
    TaskType.ANALYZE_ERROR: "错误分析",
    TaskType.RAG_RETRIEVAL: "知识检索",
    TaskType.CHAT: "通用对话",
    # Phase 8.3-E3-A
    TaskType.CREATE_DIAGRAM: "图表/流程图创建",
    TaskType.CREATE_MINDMAP: "思维导图",
    TaskType.GENERATE_PDF: "PDF教材导出",
    TaskType.EXPORT_TEXTBOOK: "完整教材导出",
    TaskType.GENERATE_VIDEO_SCRIPT: "教学视频脚本",
    TaskType.GENERATE_TEACHING_VIDEO: "教学视频生成",
    TaskType.IMAGE_UNDERSTANDING: "图片理解与分析",
    TaskType.VIDEO_UNDERSTANDING: "视频理解与分析",
}
