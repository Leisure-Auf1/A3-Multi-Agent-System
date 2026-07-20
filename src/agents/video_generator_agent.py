"""
Phase 8.3-F3 — VideoGeneratorAgent: AI 教学视频生成基础能力

职责:
  输入: TeachingMaterial (from ContentGeneratorAgent)
  输出: VideoArtifact (含 VideoScript + .srt 字幕 + 分镜 JSON)

三层输出:
  generate_script()    — VideoScript (分镜 + 旁白 + 视觉提示词)
  generate_video()     — VideoArtifact (视频脚本 + .srt 字幕文件)
  Image 联动           — scene.visual_prompt 可调用 ImageGeneratorAgent 生成关键帧

双模式:
  LLM 增强模式 — 调用 LLMProvider 生成教学分镜 + 旁白 + 视觉提示词
  Fallback 规则模式 — 生成 Markdown 脚本 + .srt 字幕 + 分镜 JSON (零延迟)

Capability Layer:
  使用 ModelRouter + check_task_capability()
  ModelCapability.VIDEO_GENERATION → TaskType.GENERATE_TEACHING_VIDEO
  禁止绕过 Capability Layer 直接调用模型

约束:
  不修改 src/core/、Veritas-Core、已有 Agent interface
"""

from __future__ import annotations
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.config.model_capability import ModelCapability
from src.config.task_capability import TaskType
from src.config.model_capability import check_task_capability
from src.config.model_router import ModelRouter, RouterResult
from src.config.model_registry import find_models_with_capability


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

@dataclass
class VideoScene:
    """单个视频场景/分镜."""
    scene_id: str                            # e.g. "scene_01"
    title: str                               # 场景标题
    narration: str = ""                      # 旁白文本
    visual_prompt: str = ""                  # 视觉提示词 (用于图片/视频生成)
    duration: int = 15                       # 时长 (秒)
    image_reference: str = ""                # Phase 8.3-F2: 关键帧图片路径或 base64 URI

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "title": self.title,
            "narration": self.narration,
            "visual_prompt": self.visual_prompt,
            "duration": self.duration,
            "image_reference": self.image_reference,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoScene":
        return cls(
            scene_id=data.get("scene_id", ""),
            title=data.get("title", ""),
            narration=data.get("narration", ""),
            visual_prompt=data.get("visual_prompt", ""),
            duration=data.get("duration", 15),
            image_reference=data.get("image_reference", ""),
        )


@dataclass
class VideoScript:
    """完整视频脚本 — 所有场景的集合."""
    script_id: str
    title: str
    topic: str = ""
    total_duration: int = 0                  # 总时长 (秒)
    scenes: List[VideoScene] = field(default_factory=list)
    subtitle: str = ""                       # .srt 格式字幕
    generation_source: str = "rule"          # rule | llm
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "script_id": self.script_id,
            "title": self.title,
            "topic": self.topic,
            "total_duration": self.total_duration,
            "scenes": [s.to_dict() for s in self.scenes],
            "subtitle": self.subtitle,
            "generation_source": self.generation_source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoScript":
        return cls(
            script_id=data.get("script_id", ""),
            title=data.get("title", ""),
            topic=data.get("topic", ""),
            total_duration=data.get("total_duration", 0),
            scenes=[VideoScene.from_dict(s) for s in data.get("scenes", [])],
            subtitle=data.get("subtitle", ""),
            generation_source=data.get("generation_source", "rule"),
            metadata=data.get("metadata", {}),
        )

    def to_srt(self) -> str:
        """Generate SRT subtitle file content."""
        lines = []
        start_ts = 0.0
        for i, scene in enumerate(self.scenes, 1):
            end_ts = start_ts + scene.duration
            start_str = _seconds_to_srt_time(start_ts)
            end_str = _seconds_to_srt_time(end_ts)
            lines.append(f"{i}")
            lines.append(f"{start_str} --> {end_str}")
            # Split narration into subtitle-sized chunks (~60 chars per sub)
            narration = scene.narration or scene.title
            chunks = [narration[j:j + 60] for j in range(0, len(narration), 60)]
            for chunk in chunks:
                lines.append(chunk.strip())
            lines.append("")
            start_ts = end_ts
        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Generate Markdown script document."""
        md_lines = [
            f"# {self.title}",
            "",
            f"**Topic:** {self.topic}",
            f"**Duration:** {self.total_duration}s ({self.total_duration // 60}m {self.total_duration % 60}s)",
            f"**Scenes:** {len(self.scenes)}",
            f"**Source:** {self.generation_source}",
            "",
            "---",
            "",
        ]
        for scene in self.scenes:
            md_lines.append(f"## 🎬 {scene.scene_id}: {scene.title}")
            md_lines.append(f"*Duration: {scene.duration}s*")
            md_lines.append("")
            if scene.narration:
                md_lines.append(f"**🎙 Narration:** {scene.narration}")
                md_lines.append("")
            if scene.visual_prompt:
                md_lines.append(f"**🖼 Visual:** {scene.visual_prompt}")
                md_lines.append("")
            if scene.image_reference:
                md_lines.append(f"**📷 Keyframe:** {scene.image_reference[:80]}...")
                md_lines.append("")
            md_lines.append("---")
            md_lines.append("")
        return "\n".join(md_lines)


@dataclass
class VideoArtifact:
    """视频生成产出."""
    path: str = ""                               # .srt 字幕文件路径 或 Markdown 脚本路径
    type: str = "script"                         # script | markdown | srt
    prompt: str = ""                             # 生成 prompt
    model: str = ""                              # 使用的模型
    provider: str = ""                           # provider 名称
    generation_source: str = "rule"              # rule | llm
    script: Optional[Dict[str, Any]] = None      # VideoScript dict
    srt_path: str = ""                           # .srt 文件路径
    markdown_path: str = ""                      # Markdown 脚本文件路径
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
            "script": self.script,
            "srt_path": self.srt_path,
            "markdown_path": self.markdown_path,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoArtifact":
        return cls(
            path=data.get("path", ""),
            type=data.get("type", "script"),
            prompt=data.get("prompt", ""),
            model=data.get("model", ""),
            provider=data.get("provider", ""),
            generation_source=data.get("generation_source", "rule"),
            script=data.get("script"),
            srt_path=data.get("srt_path", ""),
            markdown_path=data.get("markdown_path", ""),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", ""),
        )


# ──────────────────────────────────────────────
# 辅助函数
# ──────────────────────────────────────────────

def _seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ──────────────────────────────────────────────
# VideoGeneratorAgent
# ──────────────────────────────────────────────

class VideoGeneratorAgent:
    """
    AI 教学视频生成 Agent.

    两个生成接口:
      generate_script(material) → VideoScript (分镜 + 旁白 + 视觉提示词)
      generate_video(script)    → VideoArtifact (Markdown 脚本 + .srt 字幕)

    Image 联动:
      scene.visual_prompt 可调用 ImageGeneratorAgent 生成关键帧

    使用方式:
        agent = VideoGeneratorAgent()
        agent.set_llm_provider(provider)   # 可选
        script = agent.generate_script(material)
        artifact = agent.generate_video(script)
    """

    def __init__(self):
        self._llm_provider = None  # LLMProvider (optional, backward compat)
        self._orchestrator = None  # Phase 9.3-B
        self._router = ModelRouter()
        self._image_agent = None   # Phase 8.3-F2: ImageGeneratorAgent (lazy)

    # ── LLM Provider Injection ─────

    def set_llm_provider(self, provider: Any) -> None:
        """注入 LLMProvider 以启用 LLM 增强视频生成 (None = 纯规则模式)."""
        self._llm_provider = provider

    def set_orchestrator(self, orchestrator: Any) -> None:
        """Phase 9.3-B: inject OrchestratorRuntime (preferred over llm_provider)."""
        self._orchestrator = orchestrator

    def set_image_agent(self, agent: Any) -> None:
        """Phase 8.3-F2: 注入 ImageGeneratorAgent 用于生成关键帧."""
        self._image_agent = agent

    # ── 主入口 ────────────────────

    def generate_script(
        self,
        material: Any,
        provider: str = "",
        model: str = "",
    ) -> VideoScript:
        """
        从 TeachingMaterial 生成视频脚本.

        生成完整的教学视频分镜：封面、章节展开、总结。
        包含旁白文本和视觉提示词。

        Args:
            material: TeachingMaterial 实例或 dict
            provider: 可选指定 provider
            model: 可选指定 model

        Returns:
            VideoScript
        """
        material_dict = material.to_dict() if hasattr(material, "to_dict") else material

        if not material_dict:
            raise ValueError("TeachingMaterial 不能为空")

        # ── Try LLM path ──
        if self._llm_provider is not None:
            try:
                script = self._generate_script_with_llm(material_dict)
                if script is not None:
                    return script
            except Exception:
                pass

        # ── Fallback rule-based ──
        return self.fallback_generate_script(material_dict)

    def generate_video(
        self,
        script: Any,
        provider: str = "",
        model: str = "",
        output_dir: str = "",
    ) -> VideoArtifact:
        """
        从 VideoScript 生成 VideoArtifact.

        产出:
          - Markdown 视频脚本文件
          - .srt 字幕文件
          - 分镜 JSON 文件

        Args:
            script: VideoScript 实例或 dict
            provider: 可选指定 provider
            model: 可选指定 model
            output_dir: 可选输出目录

        Returns:
            VideoArtifact
        """
        script_obj = script
        if not isinstance(script_obj, VideoScript):
            script_obj = VideoScript.from_dict(script)

        return self._render_video_artifact(script_obj, output_dir, provider, model)

    # ── LLM 增强脚本生成 ──────────

    LLM_SCRIPT_PROMPT = """你是一个专业的教学视频导演。请根据以下教材内容，设计一份完整的教学视频分镜脚本。

[教材标题]
{title}

[学习目标]
{objectives}

[章节内容]
{chapters}

[整体总结]
{summary}

请生成一份完整的视频脚本，输出纯 JSON：

{{
  "title": "视频标题",
  "topic": "主题",
  "scenes": [
    {{
      "scene_id": "scene_01",
      "title": "场景标题",
      "narration": "此场景的旁白文本 (中文, 1-3句)",
      "visual_prompt": "视觉提示词 (英文, 适合 AI 视频模型, 描述画面内容)",
      "duration": 15
    }}
  ]
}}

要求:
- scene_01 为片头 (标题介绍, 30-45秒)
- 每个章节生成 2-3 个场景
- 概念 → visual_prompt 描述教学图表
- 示例 → visual_prompt 描述代码演示画面
- 练习 → visual_prompt 描述互动练习画面
- 最后 scene 为总结 (30秒)
- narration 用中文编写
- visual_prompt 用英文编写 (适合 Sora/Veo)
- 总共 {scene_count_target} 个场景
- duration: 片头 30-45秒, 内容 15-25秒, 总结 30秒

只输出 JSON，不要任何额外文本。"""

    def _generate_script_with_llm(
        self,
        material: Dict[str, Any],
    ) -> Optional[VideoScript]:
        """使用 LLMProvider 生成视频分镜脚本."""
        if self._llm_provider is None:
            return None

        title = material.get("title", "教学视频")
        objectives = json.dumps(
            material.get("learning_objectives", []),
            ensure_ascii=False,
        )
        chapters = material.get("chapters", [])

        chapters_text = self._build_chapters_text(chapters)
        summary = material.get("overall_summary", "")

        scene_count_target = max(5, len(chapters) * 3 + 2)
        prompt = self.LLM_SCRIPT_PROMPT.format(
            title=title,
            objectives=objectives,
            chapters=chapters_text,
            summary=summary,
            scene_count_target=scene_count_target,
        )

        try:
            resp = self._llm_provider.generate(
                prompt=prompt,
                system_prompt="你是一个专业的教学视频导演。输出纯 JSON。",
                temperature=0.3,
                max_tokens=2048,
            )
            if not resp.success:
                return None

            content = resp.content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:]) if len(lines) > 2 else content
                if content.endswith("```"):
                    content = content[:-3]

            data = json.loads(content)

            if "scenes" not in data:
                return None

            scenes = []
            total_dur = 0
            for s in data.get("scenes", []):
                dur = s.get("duration", 15)
                total_dur += dur
                scenes.append(VideoScene(
                    scene_id=s.get("scene_id", f"scene_{len(scenes) + 1:02d}"),
                    title=s.get("title", ""),
                    narration=s.get("narration", ""),
                    visual_prompt=s.get("visual_prompt", ""),
                    duration=dur,
                ))

            script_id = f"vscript_{id(scenes) % 100000:05d}"

            return VideoScript(
                script_id=script_id,
                title=data.get("title", title),
                topic=data.get("topic", material.get("title", "")),
                total_duration=total_dur,
                scenes=scenes,
                generation_source="llm",
                metadata={"prompt_method": "llm"},
            )
        except Exception:
            return None

    # ── Fallback 规则脚本生成 ──────

    def fallback_generate_script(
        self,
        material: Dict[str, Any],
    ) -> VideoScript:
        """
        基于规则生成视频分镜脚本 (零延迟, 始终可用).

        自动从 TeachingMaterial 的章节、概念、示例、练习中提取内容，
        组织为视频分镜结构。
        """
        title = material.get("title", "教学视频")
        chapters = material.get("chapters", [])
        objectives = material.get("learning_objectives", [])
        summary = material.get("overall_summary", "")
        script_id = f"vscript_{hash(title) % 100000:05d}"

        scenes: List[VideoScene] = []
        scene_num = 1

        # ── Scene 1: 片头 ──
        objective_text = "; ".join(objectives[:3]) if objectives else "掌握核心知识点"
        scenes.append(VideoScene(
            scene_id=f"scene_{scene_num:02d}",
            title=f"🎬 片头: {title}",
            narration=f"欢迎来到《{title}》。本课程将带你学习{objective_text}。让我们开始吧！",
            visual_prompt=f"Title animation: \"{title}\" with educational icons, warm colors",
            duration=30,
        ))
        scene_num += 1

        # ── 章节场景: 每个章节 2-3 个场景 ──
        for ch in chapters:
            ch_title = ch.get("title", "")
            ch_expl = ch.get("explanation", "")
            concepts = ch.get("concepts", [])
            examples = ch.get("examples", [])
            exercises = ch.get("exercises", [])

            # 章节介绍
            concept_names = [c.get("name", "") for c in concepts[:3]]
            narration = (
                f"接下来我们学习{ch_title}。"
                + (f"核心概念包括: {'、'.join(concept_names)}。" if concept_names else "")
            )
            scenes.append(VideoScene(
                scene_id=f"scene_{scene_num:02d}",
                title=f"📖 {ch_title}",
                narration=narration,
                visual_prompt=f"Title card: \"{ch_title}\" with {', '.join(concept_names[:2]) or 'key concepts'} illustrated as clean diagrams",
                duration=20,
            ))
            scene_num += 1

            # 概念详解
            for c in concepts[:2]:
                c_name = c.get("name", "")
                c_desc = c.get("description", "")
                scenes.append(VideoScene(
                    scene_id=f"scene_{scene_num:02d}",
                    title=f"📌 概念: {c_name}",
                    narration=f"{c_name} — {c_desc}。这是理解本课程的关键知识点。",
                    visual_prompt=f"Educational diagram: {c_name} - {c_desc}, clean minimalist style, highlighting key points",
                    duration=15,
                ))
                scene_num += 1

            # 示例演示
            for e in examples[:1]:
                e_title = e.get("title", "")
                e_expl = e.get("explanation", "")
                e_code = e.get("code", "")
                scenes.append(VideoScene(
                    scene_id=f"scene_{scene_num:02d}",
                    title=f"💡 示例: {e_title}",
                    narration=f"让我们通过一个示例来理解: {e_title}。{e_expl}",
                    visual_prompt=(
                        f"Code demo: {e_title}, showing code on screen with syntax highlighting, "
                        f"code snippet: {e_code[:60] if e_code else ''}"
                    ),
                    duration=20,
                ))
                scene_num += 1

            # 练习
            for ex in exercises[:1]:
                q = ex.get("question", "")
                scenes.append(VideoScene(
                    scene_id=f"scene_{scene_num:02d}",
                    title=f"✏️ 练习",
                    narration=f"现在请思考: {q}",
                    visual_prompt=f"Quiz card: \"{q[:60]}\" with thought bubble icons, interactive feel",
                    duration=15,
                ))
                scene_num += 1

        # ── 总结 ──
        summary_text = summary if summary else f"本次课程涵盖了{len(chapters)}个章节，共{len(scenes)}个知识场景。"
        scenes.append(VideoScene(
            scene_id=f"scene_{scene_num:02d}",
            title="🎯 总结",
            narration=(
                f"以上就是《{title}》的全部内容。{summary_text}"
                "希望你能学以致用，我们下次再见！"
            ),
            visual_prompt=f"Summary slide: key takeaways from \"{title}\", modern flat design, checkmark icons",
            duration=30,
        ))

        total_dur = sum(s.duration for s in scenes)

        return VideoScript(
            script_id=script_id,
            title=title,
            topic=material.get("title", ""),
            total_duration=total_dur,
            scenes=scenes,
            generation_source="rule",
            metadata={
                "chapter_count": len(chapters),
                "concept_count": sum(len(ch.get("concepts", [])) for ch in chapters),
            },
        )

    # ── Video Artifact 渲染 ─────────

    def _render_video_artifact(
        self,
        script: VideoScript,
        output_dir: str = "",
        provider: str = "",
        model: str = "",
    ) -> VideoArtifact:
        """将 VideoScript 渲染为 VideoArtifact (Markdown + .srt + JSON)."""
        # 生成 .srt 字幕
        script.subtitle = script.to_srt()

        # 保存文件
        use_dir = output_dir if output_dir else tempfile.mkdtemp(prefix="a3_video_")
        if output_dir:
            os.makedirs(use_dir, exist_ok=True)

        # Markdown 脚本
        md_path = os.path.join(use_dir, f"{script.script_id}.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(script.to_markdown())

        # .srt 字幕
        srt_path = os.path.join(use_dir, f"{script.script_id}.srt")
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(script.subtitle)

        # 分镜 JSON
        json_path = os.path.join(use_dir, f"{script.script_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(script.to_dict(), f, ensure_ascii=False, indent=2)

        return VideoArtifact(
            path=md_path,
            type="script",
            prompt=f"教学视频: {script.title}",
            model=model or "rule",
            provider=provider or "rule",
            generation_source=script.generation_source,
            script=script.to_dict(),
            srt_path=srt_path,
            markdown_path=md_path,
            metadata={
                "json_path": json_path,
                "output_dir": use_dir,
                "scene_count": len(script.scenes),
                "total_duration": script.total_duration,
            },
        )

    # ── 辅助方法 ──────────────────

    def _build_chapters_text(self, chapters: list) -> str:
        """Build chapters text for LLM prompt."""
        lines = []
        for ch in chapters:
            ch_title = ch.get("title", "")
            ch_expl = ch.get("explanation", "")[:150]
            concepts = [c.get("name", "") for c in ch.get("concepts", [])]
            examples = [e.get("title", "") for e in ch.get("examples", [])]

            lines.append(f"## {ch_title}")
            if ch_expl:
                lines.append(f"  解释: {ch_expl}")
            if concepts:
                lines.append(f"  概念: {', '.join(concepts)}")
            if examples:
                lines.append(f"  示例: {', '.join(examples)}")
            lines.append("")
        return "\n".join(lines) if lines else "无章节"

    def check_video_capability(
        self,
        provider: str,
        model: str = "",
    ) -> Tuple[bool, Optional[str]]:
        """
        检查指定 provider/model 是否支持视频生成.

        使用 check_task_capability() 进行能力检查。
        禁止绕过 Capability Layer。

        Returns:
            (supported: bool, error_message: Optional[str])
        """
        return check_task_capability(provider, model, TaskType.GENERATE_TEACHING_VIDEO)

    def get_recommended_model(
        self,
        preferred_provider: str = "",
    ) -> RouterResult:
        """获取推荐用于视频生成的模型."""
        return self._router.select_model(
            TaskType.GENERATE_TEACHING_VIDEO,
            preferred_provider=preferred_provider,
        )

    def get_capable_models(self) -> list:
        """获取所有支持视频生成的模型."""
        return self._router.find_models(TaskType.GENERATE_TEACHING_VIDEO)

    def get_capable_providers(self) -> List[str]:
        """获取所有支持视频生成的 provider."""
        return self._router.get_capable_providers(TaskType.GENERATE_TEACHING_VIDEO)

    # ── Image 联动 (Phase 8.3-F2) ──

    def generate_keyframes(
        self,
        script: VideoScript,
        provider: str = "",
        model: str = "",
    ) -> VideoScript:
        """
        为视频脚本生成关键帧图片.

        对每个场景调用 ImageGeneratorAgent 生成配图，
        存入 scene.image_reference。

        Args:
            script: VideoScript 实例
            provider: 图片生成 provider
            model: 图片生成 model

        Returns:
            VideoScript (含 image_reference)
        """
        if self._image_agent is None:
            # Lazy import — no hard dependency
            try:
                from src.agents.image_generator_agent import ImageGeneratorAgent
                self._image_agent = ImageGeneratorAgent()
            except ImportError:
                return script  # No image agent available

        for scene in script.scenes:
            if not scene.image_reference and scene.visual_prompt:
                try:
                    artifact = self._image_agent.generate_image(
                        concept=scene.visual_prompt[:100],
                        provider=provider,
                        model=model,
                    )
                    scene.image_reference = artifact.path or artifact.to_base64_uri()
                except Exception:
                    pass  # Keyframe generation is optional

        return script

    @staticmethod
    def capability_error_message(provider: str, model: str) -> str:
        """生成 capability 不足的错误消息."""
        provider_label = {
            "openai": "OpenAI", "deepseek": "DeepSeek",
            "spark": "讯飞星火", "mock": "Mock", "rule": "Rule",
            "google": "Google", "anthropic": "Anthropic",
        }.get(provider, provider)
        model_display = f"{provider_label} {model}" if model else provider_label

        router = ModelRouter()
        try:
            capable = router.find_models(TaskType.GENERATE_TEACHING_VIDEO)
            if capable:
                names = [m.display_name for m in capable[:3]]
                return (
                    f"当前模型 {model_display} 不支持视频生成，"
                    f"系统正在寻找支持该能力的模型。\n推荐: {', '.join(names)}"
                )
        except Exception:
            pass
        return f"当前模型 {model_display} 不支持视频生成，系统正在寻找支持该能力的模型。"
