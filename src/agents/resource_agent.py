"""
Phase 3 — ResourceAgent: 基于学习者画像和知识缺口推荐学习资源

职责:
  输入: learner profile, learning goal, knowledge gaps
  输出: 个性化资源推荐 (documentation, video, exercise, etc.)

与 ResourceRecommendationAgent 的区别:
  - ResourceAgent 是简化版，面向 pipeline demo 场景
  - 不需要 StudentMemory/mastery_map，直接基于 profile + goal + gaps 推荐
  - 输出更简洁，适合演示和测试
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

RESOURCE_CATALOG = {
    "documentation": {
        "python_networking": {
            "title": "Python Async Networking Guide",
            "reason": "从零开始理解 asyncio 和 socket 编程",
        },
        "http_protocol": {
            "title": "HTTP 协议详解",
            "reason": "理解请求/响应模型和 RESTful API",
        },
        "websocket": {
            "title": "WebSocket 实时通信指南",
            "reason": "掌握双向实时通信模式",
        },
    },
    "video": {
        "networking_basics": {
            "title": "计算机网络基础 — 从 OSI 到 TCP/IP",
            "reason": "可视化理解网络分层架构",
        },
        "python_sockets": {
            "title": "Python Socket 编程实战",
            "reason": "视频演示 socket 编程全流程",
        },
    },
    "exercise": {
        "socket_lab": {
            "title": "Socket 编程实验室",
            "reason": "动手构建 TCP 客户端/服务器",
        },
        "http_server": {
            "title": "构建简易 HTTP 服务器",
            "reason": "从零实现 HTTP 请求解析",
        },
    },
    "article": {
        "async_patterns": {
            "title": "Python 异步编程模式最佳实践",
            "reason": "深入理解 async/await 设计模式",
        },
        "network_security": {
            "title": "网络安全入门 — TLS/SSL 与加密",
            "reason": "学习网络通信安全基础",
        },
    },
    "project": {
        "chat_app": {
            "title": "构建多用户聊天室",
            "reason": "综合实践 socket + asyncio + 协议设计",
        },
        "api_client": {
            "title": "构建 REST API 客户端库",
            "reason": "实战 HTTP 客户端封装与错误处理",
        },
    },
}


@dataclass
class ResourceItem:
    """单个推荐资源"""
    type: str                         # documentation | video | exercise | article | project
    title: str                        # 资源标题
    reason: str                       # 推荐理由
    difficulty: str = "beginner"      # beginner | intermediate | advanced
    estimated_minutes: int = 30       # 预计学习时间
    url: str = ""                     # 资源链接 (可选)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "title": self.title,
            "reason": self.reason,
            "difficulty": self.difficulty,
            "estimated_minutes": self.estimated_minutes,
            "url": self.url,
        }


@dataclass
class ResourceRecommendation:
    """资源推荐结果"""
    goal: str                                    # 学习目标
    profile_summary: str                         # 画像摘要
    resources: List[ResourceItem] = field(default_factory=list)
    total_minutes: int = 0
    reasoning: str = ""                          # 推荐逻辑
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "profile_summary": self.profile_summary,
            "resources": [r.to_dict() for r in self.resources],
            "total_minutes": self.total_minutes,
            "reasoning": self.reasoning,
            "generated_at": self.generated_at,
        }


# ──────────────────────────────────────────────
# ResourceAgent
# ──────────────────────────────────────────────

class ResourceAgent:
    """
    学习资源推荐 Agent.

    基于学习者画像、学习目标和知识缺口，推荐个性化学习资源。

    使用:
        agent = ResourceAgent()
        result = agent.recommend(
            profile={"knowledge_base": "junior_dev", "cognitive_style": "visual_dominant"},
            goal="学习 Python 网络编程",
            knowledge_gaps=["socket", "asyncio", "HTTP"],
        )
    """

    def __init__(self):
        self._catalog = RESOURCE_CATALOG

    # ── 主入口 ────────────────────────────────

    def recommend(
        self,
        profile: Dict[str, str],
        goal: str = "",
        knowledge_gaps: Optional[List[str]] = None,
    ) -> ResourceRecommendation:
        """
        根据画像和目标推荐资源.

        Args:
            profile: 六维画像字典 (或 DynamicProfile.to_dict())
            goal: 学习目标描述
            knowledge_gaps: 知识缺口列表 (概念名)

        Returns:
            ResourceRecommendation
        """
        knowledge_gaps = knowledge_gaps or []

        # 画像提取
        kb_level = profile.get("knowledge_base", "junior_dev")
        cognitive = profile.get("cognitive_style", "visual_dominant")
        pace = profile.get("learning_pace", "normal")

        # 难度映射
        difficulty = self._map_difficulty(kb_level)

        # 资源选择策略
        resources = self._select_resources(
            goal=goal,
            gaps=knowledge_gaps,
            cognitive=cognitive,
            pace=pace,
            difficulty=difficulty,
        )

        # 计算总时长
        total_minutes = sum(r.estimated_minutes for r in resources)

        # 生成推理说明
        reasoning = self._generate_reasoning(
            profile=profile,
            goal=goal,
            gaps=knowledge_gaps,
            resources=resources,
        )

        return ResourceRecommendation(
            goal=goal,
            profile_summary=f"{kb_level} / {cognitive} / {pace}",
            resources=resources,
            total_minutes=total_minutes,
            reasoning=reasoning,
        )

    # ── 资源选择逻辑 ──────────────────────────

    def _select_resources(
        self,
        goal: str,
        gaps: List[str],
        cognitive: str,
        pace: str,
        difficulty: str,
    ) -> List[ResourceItem]:
        """根据策略选择资源"""
        resources: List[ResourceItem] = []

        # 知识缺口 → 资源类型偏好
        for gap in gaps:
            gap_lower = gap.lower()

            # 基础概念缺口 → 文档 + 视频
            if any(kw in gap_lower for kw in ["socket", "tcp", "ip", "network"]):
                resources.append(ResourceItem(
                    type="documentation",
                    title="Python Async Networking Guide",
                    reason=f"弥补 {gap} 知识缺口 — 系统学习网络编程基础",
                    difficulty=difficulty,
                    estimated_minutes=30,
                ))
                if cognitive in ("visual_dominant",):
                    resources.append(ResourceItem(
                        type="video",
                        title="计算机网络基础 — 从 OSI 到 TCP/IP",
                        reason=f"视觉化理解 {gap} 概念 — 适合 {cognitive} 学习者",
                        difficulty=difficulty,
                        estimated_minutes=25,
                    ))

            # 协议相关 → 文档 + 练习
            if any(kw in gap_lower for kw in ["http", "rest", "api", "protocol"]):
                resources.append(ResourceItem(
                    type="documentation",
                    title="HTTP 协议详解",
                    reason=f"深入理解 {gap} — 请求/响应模型与 RESTful 设计",
                    difficulty=difficulty,
                    estimated_minutes=25,
                ))
                resources.append(ResourceItem(
                    type="exercise",
                    title="构建简易 HTTP 服务器",
                    reason=f"动手实践 {gap} — 从零实现 HTTP 请求解析",
                    difficulty=difficulty,
                    estimated_minutes=45,
                ))

            # 异步 → 文章 + 项目
            if any(kw in gap_lower for kw in ["async", "asyncio", "coroutine", "await"]):
                resources.append(ResourceItem(
                    type="article",
                    title="Python 异步编程模式最佳实践",
                    reason=f"掌握 {gap} — 深入理解 async/await 设计模式",
                    difficulty=difficulty,
                    estimated_minutes=20,
                ))
                resources.append(ResourceItem(
                    type="project",
                    title="构建多用户聊天室",
                    reason=f"综合实践 {gap} — socket + asyncio + 协议设计",
                    difficulty="intermediate" if difficulty == "beginner" else "advanced",
                    estimated_minutes=60,
                ))

            # WebSocket → 文档
            if any(kw in gap_lower for kw in ["websocket", "ws", "real-time", "实时"]):
                resources.append(ResourceItem(
                    type="documentation",
                    title="WebSocket 实时通信指南",
                    reason=f"学习 {gap} — 掌握双向实时通信模式",
                    difficulty="intermediate",
                    estimated_minutes=30,
                ))

        # 如果没有匹配到具体资源，添加默认推荐
        if not resources:
            # 根据学习节奏添加基础资源
            if pace == "fast_track":
                resources.append(ResourceItem(
                    type="article",
                    title="Python 网络编程速查表",
                    reason="快速上手网络编程核心概念",
                    difficulty=difficulty,
                    estimated_minutes=15,
                ))
            else:
                resources.append(ResourceItem(
                    type="documentation",
                    title="Python Socket 编程入门",
                    reason="系统学习网络编程基础知识",
                    difficulty=difficulty,
                    estimated_minutes=30,
                ))
                resources.append(ResourceItem(
                    type="exercise",
                    title="Socket 编程实验室",
                    reason="动手构建 TCP 客户端/服务器",
                    difficulty=difficulty,
                    estimated_minutes=45,
                ))

        # 添加综合项目 (如果 pace 不是 fast_track)
        if pace != "fast_track" and len(resources) <= 3:
            resources.append(ResourceItem(
                type="project",
                title="构建 REST API 客户端库",
                reason="综合实战 — HTTP 客户端封装与错误处理",
                difficulty="intermediate" if difficulty == "beginner" else "advanced",
                estimated_minutes=60,
            ))

        return resources

    def _map_difficulty(self, kb_level: str) -> str:
        """知识基础映射到难度"""
        mapping = {
            "junior_dev": "beginner",
            "mid_level": "intermediate",
            "senior": "advanced",
        }
        return mapping.get(kb_level, "beginner")

    def _generate_reasoning(
        self,
        profile: Dict[str, str],
        goal: str,
        gaps: List[str],
        resources: List[ResourceItem],
    ) -> str:
        """生成推荐逻辑说明"""
        kb = profile.get("knowledge_base", "junior_dev")
        cog = profile.get("cognitive_style", "visual_dominant")

        parts = [f"学习目标: {goal}"]
        parts.append(f"学习者水平: {kb}")

        if gaps:
            parts.append(f"知识缺口: {', '.join(gaps[:5])}")

        # 认知风格偏好
        type_counts: Dict[str, int] = {}
        for r in resources:
            type_counts[r.type] = type_counts.get(r.type, 0) + 1
        type_str = ", ".join(f"{t}({c})" for t, c in type_counts.items())
        parts.append(f"推荐资源分布: {type_str} (共 {len(resources)} 项)")

        # 认知风格适配
        if cog == "visual_dominant":
            parts.append("策略: 优先视频和图解资源, 匹配视觉型学习者")
        elif cog == "text_linear":
            parts.append("策略: 优先文档和分步教程, 匹配线性阅读者")

        return " | ".join(parts)
