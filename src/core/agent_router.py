"""
Phase 5 — AgentRouter: 双引擎靶向割接路由

将 A3 系统接入生产级双引擎架构:
  前场 — 讯飞星火 (合规): ContentAgent / ProfileAgent / OnboardingAgent
  后场 — 核心引擎: SandboxValidator / MetaReflector / UserSimAgent

动态画像合约:
  该合约在路由层生效, 影响前场 Agent 的 System Prompt 注入,
  而非替换 UserSim 的规则引擎画像。
"""

from __future__ import annotations
import json
import os
import urllib.request
import ssl
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
# 动态画像合约
# ──────────────────────────────────────────────

@dataclass
class DynamicProfile:
    """AgentRouter 层的学生动态画像 (生产环境配置)"""
    knowledge_base: str = "junior_dev"          # junior_dev | mid_level | senior
    cognitive_style: str = "visual_dominant"    # visual_dominant | text_linear | auditory
    error_prone_bias: str = "magic_syntax_blind" # 最容易犯的错误类型
    learning_pace: str = "fast_track"           # fast_track | normal | deep_dive
    interaction_preference: str = "code_sandbox" # code_sandbox | quiz_first | passive_read
    frustration_threshold: str = "low"          # low | medium | high

    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_base": self.knowledge_base,
            "cognitive_style": self.cognitive_style,
            "error_prone_bias": self.error_prone_bias,
            "learning_pace": self.learning_pace,
            "interaction_preference": self.interaction_preference,
            "frustration_threshold": self.frustration_threshold,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DynamicProfile":
        return cls(**{k: data.get(k, "") for k in cls.__dataclass_fields__})

    def to_system_prompt_hint(self) -> str:
        """生成注入 ContentAgent System Prompt 的画像提示"""
        hints = {
            "visual_dominant": "该学生是视觉主导型——请大量使用 ASCII 字符画、Mermaid 拓扑图和代码对比块。",
            "text_linear": "该学生偏好线性阅读——请使用分步拆解的非代码论述结构。",
            "auditory": "该学生是听觉型——请在讲解中加入大量类比和故事化表达。",
        }
        pace = {
            "fast_track": "学习节奏极快——跳过冗余铺垫, 直击核心原理。",
            "normal": "正常节奏——逐步推进概念。",
            "deep_dive": "深度学习——每个概念都要深挖底层。",
        }
        parts = [
            hints.get(self.cognitive_style, ""),
            pace.get(self.learning_pace, ""),
            f"挫败阈值: {self.frustration_threshold}——"
            + ("极易受挫, 请用极度温和的语气, 频繁给予正向反馈。"
               if self.frustration_threshold == "low" else "正常容忍度。"),
        ]
        return "\n".join(p for p in parts if p)


# ──────────────────────────────────────────────
# AgentRouter — 双引擎靶向割接
# ──────────────────────────────────────────────

class AgentRouter:
    """
    双引擎路由控制器.

    前场 Agent (评委可见): → 讯飞星火
    后场 Agent (后台自愈): → 核心引擎
    """

    FRONTEND_AGENTS = {"ContentAgent", "ProfileAgent", "OnboardingAgent"}
    BACKEND_AGENTS = {"SandboxValidator", "MetaReflector", "UserSimAgent"}

    def __init__(
        self,
        xf_spark_api_key: Optional[str] = None,
        xf_spark_base_url: Optional[str] = None,
        core_engine_api_key: Optional[str] = None,
        core_engine_base_url: Optional[str] = None,
    ):
        # 讯飞星火 — 前场合规引擎
        self.xf_spark_api_key = xf_spark_api_key or os.getenv(
            "XF_SPARK_API_KEY", ""
        )
        self.xf_spark_base_url = xf_spark_base_url or os.getenv(
            "XF_SPARK_BASE_URL",
            "https://spark-api.xf-yun.com/v1/chat/completions",
        )

        # Core 引擎 — 后场沙箱自愈
        self.core_api_key = core_engine_api_key or os.getenv(
            "DEEPSEEK_API_KEY", ""
        )
        self.core_base_url = core_engine_base_url or os.getenv(
            "CORE_ENGINE_URL",
            "https://api.deepseek.com/v1",
        )

    def route_request(
        self, agent_role: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        靶向路由.

        Args:
            agent_role: Agent 角色名
            payload: 请求载荷 {model, messages, temperature, ...}

        Returns:
            API 响应 dict
        """
        if agent_role in self.FRONTEND_AGENTS:
            return self._dispatch_to_spark(payload)
        elif agent_role in self.BACKEND_AGENTS:
            return self._dispatch_to_core(payload)
        return self._dispatch_to_core(payload)  # 兜底

    def _dispatch_to_spark(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """前场 → 讯飞星火"""
        return self._call_api(
            api_key=self.xf_spark_api_key,
            base_url=self.xf_spark_base_url,
            payload=payload,
            label="Spark",
        )

    def _dispatch_to_core(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """后场 → DeepSeek"""
        return self._call_api(
            api_key=self.core_api_key,
            base_url=self.core_base_url,
            payload=payload,
            label="Core",
        )

    def _call_api(
        self,
        api_key: str,
        base_url: str,
        payload: Dict[str, Any],
        label: str = "API",
    ) -> Dict[str, Any]:
        """通用 API 调用"""
        if not api_key:
            return {
                "error": f"{label} API key not configured",
                "choices": [{"message": {"content": ""}}],
            }

        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        ctx = ssl.create_default_context()
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
                return json.loads(resp.read())
        except Exception as e:
            return {
                "error": f"{label} dispatch failed: {e}",
                "choices": [{"message": {"content": ""}}],
            }

    def build_routed_prompt(
        self,
        agent_role: str,
        base_prompt: str,
        profile: Optional[DynamicProfile] = None,
    ) -> str:
        """
        构建带路由注入的 Prompt.

        前场 Agent 会额外注入动态画像的 System Prompt 提示.
        """
        if agent_role in self.FRONTEND_AGENTS and profile:
            hint = profile.to_system_prompt_hint()
            return base_prompt + f"\n\n# Dynamic Student Profile\n{hint}"
        return base_prompt


# ──────────────────────────────────────────────
# 默认配置
# ──────────────────────────────────────────────

DEFAULT_PROFILE = DynamicProfile(
    knowledge_base="junior_dev",
    cognitive_style="visual_dominant",
    error_prone_bias="magic_syntax_blind",
    learning_pace="fast_track",
    interaction_preference="code_sandbox",
    frustration_threshold="low",
)


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("╔══════════════════════════════╗")
    print("║  AgentRouter — 双引擎路由   ║")
    print("╚══════════════════════════════╝")
    print()

    router = AgentRouter()
    print(f"前场 Agents: {router.FRONTEND_AGENTS}")
    print(f"后场 Agents: {router.BACKEND_AGENTS}")
    print()

    profile = DEFAULT_PROFILE
    print("默认画像:")
    for k, v in profile.to_dict().items():
        print(f"  {k}: {v}")
    print()

    prompt = router.build_routed_prompt(
        "ContentAgent", "You are a tutor.", profile
    )
    print(f"路由注入后 Prompt ({len(prompt)} chars):")
    print(prompt[-300:])
