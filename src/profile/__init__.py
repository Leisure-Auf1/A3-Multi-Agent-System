"""
A3 v4 — DynamicStudentProfile: 10 维动态学生画像

每个维度独立追踪: value × confidence × evidence × update_time
支持:
  - 置信度指数衰减 (7d 无新证据 → 0.9/day)
  - 证据冲突检测
  - 画像差异对比 (ProfileDiff)
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional


class ProfileDimension(str, Enum):
    """10 维学生画像"""
    # ── 认知维度 (原保留) ──
    KNOWLEDGE_BASE = "knowledge_base"              # 知识基础
    LEARNING_GOAL = "learning_goal"                # 学习目标
    COGNITIVE_STYLE = "cognitive_style"            # 认知风格
    LEARNING_PACE = "learning_pace"                # 学习节奏
    WEAK_POINTS = "weak_points"                   # 薄弱知识点
    RESOURCE_PREFERENCE = "resource_preference"    # 资源偏好
    # ── 行为维度 (新增) ──
    LEARNING_MOTIVATION = "learning_motivation"    # 学习动机
    ATTENTION_PATTERN = "attention_pattern"        # 注意力模式
    TIME_FRAGMENTATION = "time_fragmentation"      # 时间碎片化程度
    SELF_REGULATION = "self_regulation"            # 自我调节能力


# ── 维度值类型定义 ──
DIMENSION_TYPES: Dict[str, str] = {
    "knowledge_base": "str",        # "junior_dev" | "mid_level" | "senior"
    "learning_goal": "str",         # "multi_agent_ai" | "rag_systems" | ...
    "cognitive_style": "str",       # "visual_dominant" | "text_preferred" | "code_sandbox"
    "learning_pace": "str",         # "slow_track" | "steady" | "fast_track"
    "weak_points": "list",          # ["tokenization", "attention", ...]
    "resource_preference": "str",   # "note" | "mindmap" | "code_lab" | ...
    "learning_motivation": "str",   # "intrinsic" | "extrinsic" | "none"
    "attention_pattern": "str",     # "sustained" | "pulsed" | "fragmented"
    "time_fragmentation": "float",  # 0.0-1.0 (0=大块时间, 1=极度碎片)
    "self_regulation": "float",     # 0.0-1.0
}


@dataclass
class ProfileEntry:
    """单个画像维度的值 — 带置信度和证据"""
    dimension: ProfileDimension
    value: Any                          # str / float / list
    confidence: float = 0.5             # 0.0-1.0
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "value": self.value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProfileEntry":
        return cls(
            dimension=ProfileDimension(data["dimension"]),
            value=data.get("value"),
            confidence=data.get("confidence", 0.5),
            evidence=data.get("evidence", []),
            updated_at=data.get("updated_at", ""),
        )


@dataclass
class DynamicStudentProfile:
    """
    动态学生画像 — 每个维度独立生命周期。

    使用:
        profile = DynamicStudentProfile(student_id="xiao_lin")
        profile.update_dimension(
            ProfileDimension.COGNITIVE_STYLE,
            "visual_dominant", 0.90,
            {"source": "对话", "detail": "学生说'我更擅长看图学习'"}
        )
        profile.decay_stale_dimensions()  # 衰减长时未更新的维度
    """

    student_id: str
    dimensions: Dict[str, ProfileEntry] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_activity_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def update_dimension(
        self,
        dimension: ProfileDimension,
        new_value: Any,
        confidence: float,
        evidence: Dict[str, Any],
    ) -> None:
        """
        更新单个维度。

        更新策略:
          1. 维度不存在 → 新建
          2. 新值 == 旧值 → confidence = max(旧, 新) + 0.05
          3. 新值 ≠ 旧值 → 标记冲突, confidence = (旧 * 0.3 + 新 * 0.7)
             (新证据权重更高)
        """
        key = dimension.value
        evidence["timestamp"] = datetime.now(timezone.utc).isoformat()

        if key not in self.dimensions:
            self.dimensions[key] = ProfileEntry(
                dimension=dimension,
                value=new_value,
                confidence=confidence,
                evidence=[evidence],
            )
        else:
            entry = self.dimensions[key]
            entry.evidence.append(evidence)
            entry.updated_at = datetime.now(timezone.utc).isoformat()

            if entry.value == new_value:
                # 证据一致 → 置信度上升
                entry.confidence = min(1.0, max(entry.confidence, confidence) + 0.05)
            else:
                # 证据矛盾 → 新证据权重大
                entry.confidence = round(entry.confidence * 0.3 + confidence * 0.7, 2)
                entry.value = new_value

        self.last_activity_at = datetime.now(timezone.utc).isoformat()

    def decay_stale_dimensions(self, stale_days: int = 7, decay_factor: float = 0.9) -> None:
        """
        衰减长期未更新的维度置信度。

        confidence_new = confidence_old × decay_factor^(days_since_update / stale_days)
        """
        now = datetime.now(timezone.utc)
        for entry in self.dimensions.values():
            try:
                updated = datetime.fromisoformat(entry.updated_at)
            except (ValueError, TypeError):
                continue
            days_since = (now - updated).days
            if days_since > stale_days:
                decay = decay_factor ** (days_since / stale_days)
                entry.confidence = round(entry.confidence * decay, 2)
                if entry.confidence < 0.1:
                    entry.confidence = 0.1  # 底线

    def get_high_confidence_dimensions(self, min_confidence: float = 0.5) -> Dict[str, Any]:
        """获取置信度 ≥ min_confidence 的维度 (供 Planner 消费)。"""
        return {
            k: e.value for k, e in self.dimensions.items()
            if e.confidence >= min_confidence
        }

    def get_dimension(self, dimension: ProfileDimension) -> Optional[ProfileEntry]:
        return self.dimensions.get(dimension.value)

    @property
    def global_confidence(self) -> float:
        """全局画像可信度 (所有维度均值)。"""
        if not self.dimensions:
            return 0.0
        return round(
            sum(e.confidence for e in self.dimensions.values()) / len(self.dimensions), 2
        )

    def diff(self, previous: "DynamicStudentProfile") -> "ProfileDiff":
        """画像差异对比 — 用于 Dashboard 展示学生成长轨迹。"""
        changes: List[Dict[str, Any]] = []
        for key, entry in self.dimensions.items():
            prev = previous.dimensions.get(key)
            if prev and prev.value != entry.value:
                changes.append({
                    "dimension": key,
                    "old_value": prev.value,
                    "new_value": entry.value,
                    "confidence_delta": round(entry.confidence - prev.confidence, 2),
                })
        return ProfileDiff(
            student_id=self.student_id,
            changes=changes,
            previous_global_confidence=previous.global_confidence,
            current_global_confidence=self.global_confidence,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "dimensions": {k: v.to_dict() for k, v in self.dimensions.items()},
            "global_confidence": self.global_confidence,
            "created_at": self.created_at,
            "last_activity_at": self.last_activity_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DynamicStudentProfile":
        profile = cls(
            student_id=data.get("student_id", ""),
            created_at=data.get("created_at", ""),
            last_activity_at=data.get("last_activity_at", ""),
        )
        for key, entry_data in data.get("dimensions", {}).items():
            profile.dimensions[key] = ProfileEntry.from_dict(entry_data)
        return profile

    @classmethod
    def create_default(cls, student_id: str) -> "DynamicStudentProfile":
        """为新学生创建带默认值的画像。"""
        profile = cls(student_id=student_id)
        defaults = [
            (ProfileDimension.KNOWLEDGE_BASE, "junior_dev", 0.3),
            (ProfileDimension.COGNITIVE_STYLE, "text_preferred", 0.3),
            (ProfileDimension.LEARNING_PACE, "steady", 0.3),
            (ProfileDimension.RESOURCE_PREFERENCE, "note", 0.3),
            (ProfileDimension.LEARNING_MOTIVATION, "extrinsic", 0.3),
            (ProfileDimension.ATTENTION_PATTERN, "pulsed", 0.3),
            (ProfileDimension.TIME_FRAGMENTATION, 0.5, 0.3),
            (ProfileDimension.SELF_REGULATION, 0.5, 0.3),
        ]
        for dim, val, conf in defaults:
            profile.dimensions[dim.value] = ProfileEntry(
                dimension=dim, value=val, confidence=conf,
                evidence=[{"source": "system", "detail": "默认初始化"}],
            )
        return profile


@dataclass
class ProfileDiff:
    """画像差异对比"""
    student_id: str
    changes: List[Dict[str, Any]] = field(default_factory=list)
    previous_global_confidence: float = 0.0
    current_global_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "changes": self.changes,
            "previous_global_confidence": self.previous_global_confidence,
            "current_global_confidence": self.current_global_confidence,
        }
