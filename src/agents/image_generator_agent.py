"""
Phase 8.3-F2 — ImageGeneratorAgent: AI 知识图片生成

职责:
  输入: TeachingMaterial / Chapter / concept 文本
  输出: ImageArtifact (SVG base64 / Mermaid / Markdown)

三种生成模式:
  generate_image()     — 通用知识图片 (对应 ILLUSTRATION)
  generate_diagram()   — 流程图/架构图 (对应 CREATE_DIAGRAM)
  generate_mindmap()   — 思维导图 (对应 CREATE_MINDMAP)

双模式:
  LLM 增强模式 — 调用 LLMProvider 生成 image prompt + 结构化描述
  Fallback 规则模式 — 生成 Mermaid / SVG / Markdown (零延迟, 始终可用)

Capability Layer:
  使用 ModelRouter + check_task_capability() 确保能力检查
  禁止绕过 Capability Layer
  若模型不支持: 返回明确错误信息 "当前模型 XXX 不支持图片生成，..."

约束:
  不修改 src/core/、Veritas-Core、已有 Agent interface
"""

from __future__ import annotations
import base64
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.config.model_capability import ModelCapability
from src.config.task_capability import TaskType
from src.config.model_capability import check_task_capability, CAPABILITY_LABELS
from src.config.model_router import ModelRouter, RouterResult
from src.config.model_registry import find_models_with_capability


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

@dataclass
class ImageArtifact:
    """图片生成产出."""
    path: str = ""                          # 文件路径 (SVG 文件) 或 base64 data URI
    type: str = "svg"                       # svg | mermaid | markdown | png
    prompt: str = ""                        # 生成 prompt
    model: str = ""                         # 使用的模型
    provider: str = ""                      # provider 名称
    generation_source: str = "rule"         # rule | llm
    content: str = ""                       # 图片内容 (SVG 源码/Mermaid 源码/Base64)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "type": self.type,
            "prompt": self.prompt,
            "model": self.model,
            "provider": self.provider,
            "generation_source": self.generation_source,
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ImageArtifact":
        return cls(
            path=data.get("path", ""),
            type=data.get("type", "svg"),
            prompt=data.get("prompt", ""),
            model=data.get("model", ""),
            provider=data.get("provider", ""),
            generation_source=data.get("generation_source", "rule"),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", ""),
        )

    def to_base64_uri(self) -> str:
        """转换为 base64 data URI (用于 HTML 嵌入)."""
        if self.type == "svg":
            b64 = base64.b64encode(self.content.encode("utf-8")).decode("ascii")
            return f"data:image/svg+xml;base64,{b64}"
        return self.path or ""


# ──────────────────────────────────────────────
# SVG 模板
# ──────────────────────────────────────────────

_CONCEPT_SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{color_start};stop-opacity:1"/>
      <stop offset="100%" style="stop-color:{color_end};stop-opacity:1"/>
    </linearGradient>
  </defs>
  <rect width="600" height="400" fill="url(#bg)" rx="16"/>
  <rect x="30" y="30" width="540" height="80" fill="white" opacity="0.9" rx="10"/>
  <text x="300" y="62" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="24" font-weight="bold" fill="#1a202c">{title}</text>
  <text x="300" y="88" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="14" fill="#4a5568">{subtitle}</text>
  <circle cx="300" cy="210" r="70" fill="white" opacity="0.3"/>
  <text x="300" y="205" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="36">{icon}</text>
  <text x="300" y="235" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="16" font-weight="bold" fill="#2d3748">{concept_name}</text>
  <rect x="60" y="310" width="480" height="50" fill="white" opacity="0.85" rx="8"/>
  <text x="300" y="340" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="13" fill="#4a5568">{description}</text>
</svg>"""

_DIAGRAM_SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 500">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#f7fafc;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#edf2f7;stop-opacity:1"/>
    </linearGradient>
    <marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5"
            markerWidth="6" markerHeight="6" orient="auto">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#4299e1"/>
    </marker>
  </defs>
  <rect width="700" height="500" fill="url(#bg)" rx="12"/>
  <text x="350" y="40" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="20" font-weight="bold" fill="#1a202c">{title}</text>
  {boxes}
</svg>"""

_MINDMAP_SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 600">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#f0fff4;stop-opacity:1"/>
      <stop offset="100%" style="stop-color:#e6fffa;stop-opacity:1"/>
    </linearGradient>
  </defs>
  <rect width="800" height="600" fill="url(#bg)" rx="12"/>
  <!-- Center node -->
  <circle cx="400" cy="300" r="60" fill="#38a169" opacity="0.9"/>
  <text x="400" y="295" text-anchor="middle" font-family="Arial, sans-serif"
        font-size="14" font-weight="bold" fill="white">{root_title}</text>
  {branches}
</svg>"""


# ──────────────────────────────────────────────
# 颜色方案
# ──────────────────────────────────────────────

_COLOR_SCHEMES = {
    "beginner": ("#48bb78", "#38a169", "🌱"),
    "intermediate": ("#4299e1", "#3182ce", "📘"),
    "advanced": ("#9f7aea", "#805ad5", "🔮"),
}

_MINDMAP_COLORS = [
    ("#3182ce", "#2b6cb0"), ("#38a169", "#2f855a"),
    ("#d69e2e", "#b7791f"), ("#e53e3e", "#c53030"),
    ("#805ad5", "#6b46c1"), ("#dd6b20", "#c05621"),
]


# ──────────────────────────────────────────────
# ImageGeneratorAgent
# ──────────────────────────────────────────────

class ImageGeneratorAgent:
    """
    AI 知识图片生成 Agent.

    三种生成模式:
      - generate_image(): 概念配图
      - generate_diagram(): 流程图/架构图
      - generate_mindmap(): 思维导图

    使用方式:
        agent = ImageGeneratorAgent()
        agent.set_llm_provider(provider)  # 可选
        artifact = agent.generate_image(concept="Python decorators")
    """

    def __init__(self):
        self._llm_provider = None  # LLMProvider (optional, backward compat)
        self._orchestrator = None  # Phase 9.3-B
        self._router = ModelRouter()

    # ── LLM Provider Injection ─────

    def set_llm_provider(self, provider: Any) -> None:
        """注入 LLMProvider 以启用 LLM 增强图片生成 (None = 纯规则模式)."""
        self._llm_provider = provider

    def set_orchestrator(self, orchestrator: Any) -> None:
        """Phase 9.3-B: inject OrchestratorRuntime (preferred over llm_provider)."""
        self._orchestrator = orchestrator

    # ── 主入口 ────────────────────

    def generate_image(
        self,
        concept: str = "",
        material: Any = None,
        provider: str = "",
        model: str = "",
    ) -> ImageArtifact:
        """
        生成知识概念配图.

        Args:
            concept: 概念文本
            material: TeachingMaterial (可选, 含更多上下文)
            provider: 可选指定 provider
            model: 可选指定 model

        Returns:
            ImageArtifact
        """
        topic = concept
        if material is not None:
            material_dict = material.to_dict() if hasattr(material, "to_dict") else material
            topic = concept or material_dict.get("title", "知识概念")

        # ── Capability check ──
        if provider and model:
            supported, err = check_task_capability(provider, model, "generate_image")
            if not supported:
                # Find alternative models
                alt_text = self._capability_error_text("generate_image")
                return ImageArtifact(
                    type="error",
                    prompt=topic,
                    model=model,
                    provider=provider,
                    generation_source="error",
                    content=err or "",
                    metadata={"alternatives": alt_text},
                )

        return self._generate_illustration(topic, provider, model)

    def generate_diagram(
        self,
        concept: str,
        provider: str = "",
        model: str = "",
    ) -> ImageArtifact:
        """
        生成流程图/架构图.

        Args:
            concept: 概念文本
            provider: 可选指定 provider
            model: 可选指定 model

        Returns:
            ImageArtifact (Mermaid 文本 或 SVG)
        """
        # ── Capability check ──
        if provider and model:
            supported, err = self._check_image_capability(provider, model, TaskType.CREATE_DIAGRAM)
            if not supported:
                return self._capability_error_artifact(concept, provider, model,
                                                       TaskType.CREATE_DIAGRAM, err)

        return self._generate_diagram_content(concept, provider, model)

    def generate_mindmap(
        self,
        material: Any,
        provider: str = "",
        model: str = "",
    ) -> ImageArtifact:
        """
        生成思维导图.

        Args:
            material: TeachingMaterial 实例或 dict
            provider: 可选指定 provider
            model: 可选指定 model

        Returns:
            ImageArtifact (Mermaid mindmap 或 SVG)
        """
        material_dict = material.to_dict() if hasattr(material, "to_dict") else material

        # ── Capability check ──
        if provider and model:
            supported, err = self._check_image_capability(provider, model, TaskType.CREATE_MINDMAP)
            if not supported:
                return self._capability_error_artifact(
                    material_dict.get("title", ""), provider, model,
                    TaskType.CREATE_MINDMAP, err,
                )

        return self._generate_mindmap_content(material_dict, provider, model)

    # ── Capability Layer ──────────

    def _check_image_capability(
        self,
        provider: str,
        model: str,
        task_type: str,
    ) -> Tuple[bool, Optional[str]]:
        """Check capability via Capability Layer (禁止绕过)."""
        return check_task_capability(provider, model, task_type)

    def _capability_error_text(self, task: str) -> str:
        """Generate user-friendly capability error with alternatives."""
        try:
            capable = self._router.find_models(task)
            if capable:
                names = [m.display_name for m in capable[:3]]
                return f"当前模型不支持图片生成。支持此能力的模型: {', '.join(names)}"
        except Exception:
            pass
        return "当前模型不支持图片生成。请配置支持 IMAGE_GENERATION 的模型。"

    def _capability_error_artifact(
        self,
        concept: str,
        provider: str,
        model: str,
        task_type: str,
        err: Optional[str] = None,
    ) -> ImageArtifact:
        """Return ImageArtifact with capability error message."""
        provider_label = {"openai": "OpenAI", "deepseek": "DeepSeek",
                          "spark": "讯飞星火", "mock": "Mock", "rule": "Rule"}.get(provider, provider)
        model_display = f"{provider_label} {model}" if model else provider_label

        alt_text = self._capability_error_text(task_type)
        message = (
            f"当前模型 {model_display} 不支持图片生成。"
            f"系统正在寻找支持该能力的模型。\n{alt_text}"
        )
        if err:
            message = f"{err}\n{alt_text}"

        return ImageArtifact(
            type="error",
            prompt=concept,
            model=model,
            provider=provider,
            generation_source="error",
            content=message,
            metadata={
                "error": "capability_unsupported",
                "task": task_type,
                "alternatives": alt_text,
            },
        )

    def get_capable_models(self, task_type: str = "") -> list:
        """Get models capable of image generation for a specific task."""
        if task_type:
            return self._router.find_models(task_type)
        return find_models_with_capability(ModelCapability.IMAGE_GENERATION)

    def get_recommended_model(self, task_type: str = "",
                              preferred_provider: str = "") -> RouterResult:
        """Get recommended model for image generation tasks."""
        return self._router.select_model(task_type, preferred_provider=preferred_provider)

    # ── 配图生成 (illustration) ───

    IMAGE_PROMPT_TEMPLATE = """你是一个教育插画设计师。请为以下知识概念设计配图描述:

[概念]
{concept}

[上下文]
{context}

请生成图片 prompt 和配图方案，输出 JSON:
{{
  "image_prompt": "详细的图片生成 prompt (英文, 适合 DALL-E/Midjourney)",
  "description": "配图的中文说明",
  "style": "minimalist|diagram|realistic|cartoon",
  "elements": ["元素1", "元素2"]
}}

只输出 JSON。"""

    def _generate_illustration(
        self,
        concept: str,
        provider: str = "",
        model: str = "",
    ) -> ImageArtifact:
        """生成概念配图."""
        # ── Try LLM for prompt generation ──
        llm_prompt = ""
        if self._llm_provider is not None:
            try:
                llm_prompt = self._generate_prompt_with_llm(concept, "")
            except Exception:
                pass

        # ── Generate SVG ──
        color_start, color_end, icon = _COLOR_SCHEMES.get("intermediate", _COLOR_SCHEMES["beginner"])

        svg_content = _CONCEPT_SVG_TEMPLATE.format(
            color_start=color_start,
            color_end=color_end,
            title=concept[:40],
            subtitle="知识概念图解",
            icon=icon,
            concept_name=concept[:30],
            description=llm_prompt[:80] or f"{concept} 的核心知识点",
        )

        svg_path = self._save_svg(svg_content, prefix="a3_img_")

        return ImageArtifact(
            path=svg_path,
            type="svg",
            prompt=llm_prompt or concept,
            model=model or "rule",
            provider=provider or "rule",
            generation_source="llm" if llm_prompt else "rule",
            content=svg_content,
            metadata={"concept": concept, "style": "gradient_card"},
        )

    def _generate_prompt_with_llm(self, concept: str, context: str) -> str:
        """Use LLM to generate image prompt."""
        if self._llm_provider is None:
            return ""

        prompt = self.IMAGE_PROMPT_TEMPLATE.format(
            concept=concept,
            context=context or "无额外上下文",
        )

        try:
            resp = self._llm_provider.generate(
                prompt=prompt,
                system_prompt="你是一个专业的教育插画设计师。输出纯 JSON。",
                temperature=0.3,
                max_tokens=512,
            )
            if not resp.success:
                return ""

            content = resp.content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:]) if len(lines) > 2 else content
                if content.endswith("```"):
                    content = content[:-3]

            data = json.loads(content)
            return data.get("image_prompt", data.get("description", ""))
        except Exception:
            return ""

    # ── 流程图/架构图 (diagram) ───

    DIAGRAM_MERMAID_TEMPLATE = """graph TD
    A[{title}] --> B[概念理解]
    A --> C[核心原理]
    B --> D[基础概念]
    B --> E[进阶概念]
    C --> F[实现机制]
    C --> G[应用场景]
    D --> H[示例1]
    D --> I[示例2]
    E --> J[高级应用]
    F --> K[代码实现]
"""

    def _generate_diagram_content(
        self,
        concept: str,
        provider: str = "",
        model: str = "",
    ) -> ImageArtifact:
        """生成流程图/架构图内容."""
        # ── Try LLM for prompt generation ──
        llm_prompt = ""
        if self._llm_provider is not None:
            try:
                llm_prompt = self._generate_prompt_with_llm(
                    f"流程图: {concept}", "生成 Mermaid 流程图"
                )
            except Exception:
                pass

        # ── Fallback: Mermaid diagram ──
        mermaid_content = self.DIAGRAM_MERMAID_TEMPLATE.format(
            title=concept[:30],
        )

        # Also generate SVG representation
        boxes = self._build_diagram_boxes(concept)
        svg_content = _DIAGRAM_SVG_TEMPLATE.format(
            title=f"流程图 — {concept[:40]}",
            boxes=boxes,
        )
        svg_path = self._save_svg(svg_content, prefix="a3_diagram_")

        return ImageArtifact(
            path=svg_path,
            type="mermaid",
            prompt=llm_prompt or concept,
            model=model or "rule",
            provider=provider or "rule",
            generation_source="llm" if llm_prompt else "rule",
            content=mermaid_content,
            metadata={
                "mermaid": mermaid_content,
                "svg_path": svg_path,
                "concept": concept,
            },
        )

    def _build_diagram_boxes(self, concept: str) -> str:
        """Build SVG box elements for a diagram."""
        boxes = []
        nodes = [
            (concept[:20], 350, 100, 120, 40),
            ("核心概念", 180, 220, 100, 40),
            ("实现机制", 520, 220, 100, 40),
            ("示例1", 120, 340, 90, 36),
            ("示例2", 240, 340, 90, 36),
            ("应用场景", 520, 340, 100, 36),
            ("代码实现", 640, 340, 90, 36),
        ]
        colors = ["#3182ce", "#38a169", "#805ad5", "#d69e2e", "#e53e3e", "#dd6b20"]

        for i, (text, x, y, w, h) in enumerate(nodes):
            color = colors[i % len(colors)]
            boxes.append(
                f'  <rect x="{x - w // 2}" y="{y - h // 2}" width="{w}" height="{h}" '
                f'fill="{color}" opacity="0.85" rx="8"/>'
            )
            boxes.append(
                f'  <text x="{x}" y="{y + 4}" text-anchor="middle" font-family="Arial, sans-serif" '
                f'font-size="12" fill="white">{text[:12]}</text>'
            )

        # Arrows
        arrows = [
            (350, 120, 180, 200), (350, 120, 520, 200),
            (180, 240, 120, 320), (180, 240, 240, 320),
            (520, 240, 520, 320), (520, 240, 640, 320),
        ]
        for x1, y1, x2, y2 in arrows:
            boxes.append(
                f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke="#4299e1" stroke-width="2" marker-end="url(#arrow)"/>'
            )

        return "\n".join(boxes)

    # ── 思维导图 (mindmap) ─────────

    MINDMAP_MERMAID_TEMPLATE = """mindmap
  root(({root_title}))
    {branches}
"""

    def _generate_mindmap_content(
        self,
        material: Dict[str, Any],
        provider: str = "",
        model: str = "",
    ) -> ImageArtifact:
        """生成思维导图."""
        title = material.get("title", "学习地图")
        chapters = material.get("chapters", [])

        # Build Mermaid mindmap
        branches = []
        for ch in chapters:
            ch_title = ch.get("title", "")
            concepts = [c.get("name", "") for c in ch.get("concepts", [])]
            branches.append(f"    {ch_title[:20]}")
            for concept in concepts[:3]:
                branches.append(f"      {concept[:15]}")

        mermaid_content = self.MINDMAP_MERMAID_TEMPLATE.format(
            root_title=title[:30],
            branches="\n".join(branches) if branches else "    概念1\n    概念2",
        )

        # Build SVG mindmap
        svg_content = self._build_mindmap_svg(title, chapters)
        svg_path = self._save_svg(svg_content, prefix="a3_mindmap_")

        return ImageArtifact(
            path=svg_path,
            type="mermaid",
            prompt=f"思维导图: {title}",
            model=model or "rule",
            provider=provider or "rule",
            generation_source="rule",
            content=mermaid_content,
            metadata={
                "mermaid": mermaid_content,
                "svg_path": svg_path,
                "chapter_count": len(chapters),
            },
        )

    def _build_mindmap_svg(self, title: str, chapters: list) -> str:
        """Build SVG mindmap from chapters."""
        branches = []
        cx, cy = 400, 300
        radius = 180

        for i, ch in enumerate(chapters[:6]):
            angle = (i * 360 / min(len(chapters), 6)) - 90
            import math
            rad = math.radians(angle)
            bx = cx + radius * math.cos(rad)
            by = cy + radius * math.sin(rad)

            color_fill, color_stroke = _MINDMAP_COLORS[i % len(_MINDMAP_COLORS)]
            ch_title = ch.get("title", "")[:14]

            # Line from center
            branches.append(
                f'  <line x1="{cx}" y1="{cy}" x2="{bx}" y2="{by}" '
                f'stroke="{color_stroke}" stroke-width="2" opacity="0.6"/>'
            )
            # Branch node
            branches.append(
                f'  <rect x="{bx - 55}" y="{by - 18}" width="110" height="36" '
                f'fill="{color_fill}" opacity="0.85" rx="18"/>'
            )
            branches.append(
                f'  <text x="{bx}" y="{by + 5}" text-anchor="middle" '
                f'font-family="Arial, sans-serif" font-size="12" fill="white">{ch_title}</text>'
            )

        return _MINDMAP_SVG_TEMPLATE.format(
            root_title=title[:20],
            branches="\n".join(branches),
        )

    # ── 文件保存 ──────────────────

    def _save_svg(self, svg_content: str, prefix: str = "a3_img_") -> str:
        """Save SVG content to temp file and return path."""
        fd, file_path = tempfile.mkstemp(suffix=".svg", prefix=prefix)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(svg_content)
        return file_path

    # ── 辅助方法 ──────────────────

    @staticmethod
    def capability_error_message(provider: str, model: str, task_type: str) -> str:
        """生成 capability 不足的错误消息."""
        provider_label = {"openai": "OpenAI", "deepseek": "DeepSeek",
                          "spark": "讯飞星火", "mock": "Mock", "rule": "Rule"}.get(provider, provider)
        model_display = f"{provider_label} {model}" if model else provider_label

        router = ModelRouter()
        try:
            capable = router.find_models(task_type)
            if capable:
                names = [m.display_name for m in capable[:3]]
                return (
                    f"当前模型 {model_display} 不支持图片生成，"
                    f"系统正在寻找支持该能力的模型。\n推荐: {', '.join(names)}"
                )
        except Exception:
            pass

        return f"当前模型 {model_display} 不支持图片生成，系统正在寻找支持该能力的模型。"
