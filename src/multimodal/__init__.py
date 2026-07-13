"""
A3 v4 — MultiModal Resource Protocol: 统一学习资源协议

LearningResource 统一协议:
  type × format × content × visual_prompt × difficulty × target_profile_dim

支持 9 类资源:
  course_note | mind_map | ppt_deck | video_script | image_asset
  | animation_desc | code_lab | exercise | extended_reading
"""

from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ResourceType(str, Enum):
    """资源类型"""
    COURSE_NOTE = "course_note"           # Markdown 课程笔记
    MIND_MAP = "mind_map"                # Mermaid 思维导图
    PPT_DECK = "ppt_deck"                # PPT 课件
    VIDEO_SCRIPT = "video_script"        # 视频分镜脚本
    IMAGE_ASSET = "image_asset"          # 教学图片素材
    ANIMATION_DESC = "animation_desc"    # 动画生成描述 (Manim/Remotion)
    CODE_LAB = "code_lab"                # 代码实验
    EXERCISE = "exercise"                # 习题
    EXTENDED_READING = "extended_reading"  # 扩展阅读


class ResourceFormat(str, Enum):
    MARKDOWN = "markdown"
    MERMAID = "mermaid"
    PPTX = "pptx"
    JSON = "json"          # 结构化描述 (动画/图片 prompt)
    PYTHON = "python"
    TEXT = "text"


@dataclass
class LearningResource:
    """统一学习资源协议 — 所有资源类型的通用容器"""
    resource_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    type: ResourceType = ResourceType.COURSE_NOTE
    format: ResourceFormat = ResourceFormat.MARKDOWN
    title: str = ""
    description: str = ""
    content: str = ""                           # 核心内容
    visual_prompt: Optional[str] = None         # AI 图像/视频生成 prompt
    difficulty: float = 0.5                     # 0.0-1.0
    estimated_minutes: int = 15
    target_profile_dim: Optional[str] = None    # 针对的画像维度
    prerequisite_concepts: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "type": self.type.value,
            "format": self.format.value,
            "title": self.title,
            "description": self.description,
            "content": self.content,
            "visual_prompt": self.visual_prompt,
            "difficulty": self.difficulty,
            "estimated_minutes": self.estimated_minutes,
            "target_profile_dim": self.target_profile_dim,
            "prerequisite_concepts": self.prerequisite_concepts,
            "keywords": self.keywords,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LearningResource":
        rt = data.get("type", "course_note")
        rf = data.get("format", "markdown")
        if isinstance(rt, str):
            rt = ResourceType(rt)
        if isinstance(rf, str):
            rf = ResourceFormat(rf)
        return cls(
            resource_id=data.get("resource_id", uuid.uuid4().hex[:12]),
            type=rt,
            format=rf,
            title=data.get("title", ""),
            description=data.get("description", ""),
            content=data.get("content", ""),
            visual_prompt=data.get("visual_prompt"),
            difficulty=data.get("difficulty", 0.5),
            estimated_minutes=data.get("estimated_minutes", 15),
            target_profile_dim=data.get("target_profile_dim"),
            prerequisite_concepts=data.get("prerequisite_concepts", []),
            keywords=data.get("keywords", []),
            metadata=data.get("metadata", {}),
        )

    def to_renderable(self) -> Dict[str, Any]:
        """生成 Dashboard 渲染所需的结构化数据。"""
        base = self.to_dict()
        # 根据类型添加渲染提示
        render_hints = {
            ResourceType.COURSE_NOTE: {"icon": "📄", "color": "#3b82f6"},
            ResourceType.MIND_MAP: {"icon": "🧠", "color": "#8b5cf6"},
            ResourceType.PPT_DECK: {"icon": "📊", "color": "#f59e0b"},
            ResourceType.VIDEO_SCRIPT: {"icon": "🎬", "color": "#ef4444"},
            ResourceType.IMAGE_ASSET: {"icon": "🖼️", "color": "#10b981"},
            ResourceType.ANIMATION_DESC: {"icon": "✨", "color": "#ec4899"},
            ResourceType.CODE_LAB: {"icon": "💻", "color": "#06b6d4"},
            ResourceType.EXERCISE: {"icon": "✏️", "color": "#f97316"},
            ResourceType.EXTENDED_READING: {"icon": "📚", "color": "#84cc16"},
        }
        base["render_hint"] = render_hints.get(self.type, {"icon": "📝", "color": "#6b7280"})
        return base


# ── 资源生成器注册表 ──

class ResourceGeneratorRegistry:
    """
    插件式资源生成器注册表。

    设计:
      - 每个生成器实现 generate(context) → LearningResource 接口
      - 注册表管理所有生成器，支持动态添加/移除
      - 避免硬编码资源生成逻辑
    """

    def __init__(self):
        self._generators: Dict[ResourceType, List[Callable[..., Any]]] = {}

    def register(self, resource_type: ResourceType, generator: Callable[..., Any]) -> None:
        """注册资源生成器。"""
        if resource_type not in self._generators:
            self._generators[resource_type] = []
        self._generators[resource_type].append(generator)

    def generate(
        self, resource_type: ResourceType, context: Dict[str, Any]
    ) -> List[LearningResource]:
        """调用所有匹配类型的生成器。"""
        generators = self._generators.get(resource_type, [])
        results = []
        for gen in generators:
            try:
                resource = gen(context)
                if resource:
                    results.append(resource)
            except Exception as e:
                # 单个生成器失败不影响其他
                pass
        return results

    def generate_all(
        self, context: Dict[str, Any], preferred_types: Optional[List[ResourceType]] = None
    ) -> List[LearningResource]:
        """根据偏好类型批量生成。"""
        types = preferred_types or list(ResourceType)
        results = []
        for rt in types:
            results.extend(self.generate(rt, context))
        return results

    @property
    def registered_types(self) -> List[str]:
        return [rt.value for rt in self._generators.keys()]
