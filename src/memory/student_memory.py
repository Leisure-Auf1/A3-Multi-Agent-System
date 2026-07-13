"""
Memory Layer — 学生长期学习状态存储

每个学生一个 JSON 文件，位于 storage/memory/students/<student_id>.json
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ──────────────────────────────────────────────
# 数据模型
# ──────────────────────────────────────────────

@dataclass
class StudentMemory:
    """学生长期学习记忆"""

    student_id: str

    # 画像历史 — 随时间演变
    profile_history: List[Dict[str, str]] = field(default_factory=list)

    # 学习弱点 — 反复出错的概念/错误类型
    weak_points: List[Dict[str, Any]] = field(default_factory=list)

    # 学习行为模式 — 来自多次交互的统计
    learning_behavior: Dict[str, Any] = field(default_factory=lambda: {
        "avg_pace": "normal",
        "preferred_style": "visual_dominant",
        "frustration_pattern": "medium",
        "interaction_count": 0,
        "avg_score": 0.0,
        "time_of_day_preference": "",
    })

    # 掌握度图 — concept → mastery (0.0-1.0)
    mastery_map: Dict[str, float] = field(default_factory=dict)

    # 反馈历史 — node_id → 最新评分
    feedback_history: List[Dict[str, Any]] = field(default_factory=list)

    # 学习会话摘要
    session_summaries: List[Dict[str, Any]] = field(default_factory=list)

    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "profile_history": self.profile_history,
            "weak_points": self.weak_points,
            "learning_behavior": self.learning_behavior,
            "mastery_map": self.mastery_map,
            "feedback_history": self.feedback_history,
            "session_summaries": self.session_summaries,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StudentMemory":
        return cls(
            student_id=data["student_id"],
            profile_history=data.get("profile_history", []),
            weak_points=data.get("weak_points", []),
            learning_behavior=data.get("learning_behavior", {}),
            mastery_map=data.get("mastery_map", {}),
            feedback_history=data.get("feedback_history", []),
            session_summaries=data.get("session_summaries", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


# ──────────────────────────────────────────────
# 存储层
# ──────────────────────────────────────────────

class StudentMemoryStore:
    """
    学生长期记忆的 JSON 文件存储.

    路径: storage/memory/students/<student_id>.json

    使用:
        store = StudentMemoryStore()
        mem = store.load("student_001")
        store.update_mastery("student_001", {"closures": 0.8, "decorators": 0.2})
        summary = store.get_learning_summary("student_001")
    """

    def __init__(self, storage_dir: Optional[str] = None):
        if storage_dir:
            self._dir = Path(storage_dir)
        else:
            # 相对于项目根
            base = Path(__file__).resolve().parent.parent.parent
            self._dir = base / "storage" / "memory" / "students"
        self._dir.mkdir(parents=True, exist_ok=True)

    def _file(self, student_id: str) -> Path:
        return self._dir / f"{student_id}.json"

    # ── CRUD ──────────────────────────────

    def exists(self, student_id: str) -> bool:
        return self._file(student_id).exists()

    def save(self, memory: StudentMemory) -> None:
        """保存或更新学生记忆"""
        memory.updated_at = datetime.now(timezone.utc).isoformat()
        self._file(memory.student_id).write_text(
            json.dumps(memory.to_dict(), ensure_ascii=False, indent=2)
        )

    def load(self, student_id: str) -> StudentMemory:
        """加载学生记忆, 不存在则创建并持久化"""
        f = self._file(student_id)
        if f.exists():
            return StudentMemory.from_dict(
                json.loads(f.read_text())
            )
        mem = StudentMemory(student_id=student_id)
        self.save(mem)  # 立即持久化
        return mem

    def delete(self, student_id: str) -> None:
        f = self._file(student_id)
        if f.exists():
            f.unlink()

    def list_all(self) -> List[str]:
        """列出所有学生 ID"""
        return [
            f.stem for f in self._dir.glob("*.json")
            if f.stem  # skip hidden
        ]

    # ── 画像操作 ──────────────────────────

    def update_profile(
        self,
        student_id: str,
        profile: Dict[str, str],
        record_history: bool = True,
    ) -> StudentMemory:
        """
        更新学生画像.

        Args:
            student_id: 学生 ID
            profile: DynamicProfile 字典
            record_history: 是否记录历史

        Returns:
            更新后的 StudentMemory
        """
        mem = self.load(student_id)

        if record_history and profile:
            mem.profile_history.append({
                **profile,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            # 只保留最近 10 条
            if len(mem.profile_history) > 10:
                mem.profile_history = mem.profile_history[-10:]

        # 更新行为统计
        beh = mem.learning_behavior
        beh["interaction_count"] += 1
        if profile.get("cognitive_style"):
            beh["preferred_style"] = profile["cognitive_style"]
        if profile.get("learning_pace"):
            beh["avg_pace"] = profile["learning_pace"]

        self.save(mem)
        return mem

    # ── 弱点管理 ──────────────────────────

    def add_weak_point(
        self,
        student_id: str,
        concept: str,
        error_type: str = "",
        occurrence_count: int = 1,
        last_seen: Optional[str] = None,
    ) -> StudentMemory:
        """
        添加或更新学习弱点.

        Args:
            student_id: 学生 ID
            concept: 薄弱概念
            error_type: 错误类型
            occurrence_count: 出现次数
        """
        mem = self.load(student_id)
        ts = last_seen or datetime.now(timezone.utc).isoformat()

        # 查找已有弱点
        for wp in mem.weak_points:
            if wp.get("concept") == concept and wp.get("error_type") == error_type:
                wp["occurrence_count"] = wp.get("occurrence_count", 0) + occurrence_count
                wp["last_seen"] = ts
                self.save(mem)
                return mem

        # 新弱点
        mem.weak_points.append({
            "concept": concept,
            "error_type": error_type,
            "occurrence_count": occurrence_count,
            "first_seen": ts,
            "last_seen": ts,
        })

        # 排序 — 出现次数多排前面
        mem.weak_points.sort(
            key=lambda w: w.get("occurrence_count", 0), reverse=True
        )
        # 最多保留 20 条
        if len(mem.weak_points) > 20:
            mem.weak_points = mem.weak_points[:20]

        self.save(mem)
        return mem

    # ── 掌握度 ────────────────────────────

    def update_mastery(
        self,
        student_id: str,
        updates: Dict[str, float],
    ) -> StudentMemory:
        """
        更新掌握度.

        Args:
            student_id: 学生 ID
            updates: {concept: mastery_score} (0.0-1.0)
        """
        mem = self.load(student_id)
        for concept, score in updates.items():
            # 指数加权移动平均 (α=0.5)
            old = mem.mastery_map.get(concept, 0.5)
            mem.mastery_map[concept] = round(old * 0.5 + score * 0.5, 2)

        self.save(mem)
        return mem

    # ── 反馈记录 ──────────────────────────

    def add_feedback(
        self,
        student_id: str,
        node_id: str,
        score: int,
        issues: Optional[List[str]] = None,
    ) -> StudentMemory:
        """添加 UserSim 反馈记录"""
        mem = self.load(student_id)
        mem.feedback_history.append({
            "node_id": node_id,
            "score": score,
            "issues": issues or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # 保留最近 20 条
        if len(mem.feedback_history) > 20:
            mem.feedback_history = mem.feedback_history[-20:]

        # 更新平均分
        scores = [f["score"] for f in mem.feedback_history]
        mem.learning_behavior["avg_score"] = round(sum(scores) / len(scores), 1)

        self.save(mem)
        return mem

    def add_session_summary(
        self,
        student_id: str,
        course_id: str,
        nodes_completed: int,
        total_score: float,
        time_spent: int = 0,
    ) -> StudentMemory:
        """添加学习会话摘要"""
        mem = self.load(student_id)
        mem.session_summaries.append({
            "course_id": course_id,
            "nodes_completed": nodes_completed,
            "total_score": total_score,
            "time_spent": time_spent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        if len(mem.session_summaries) > 10:
            mem.session_summaries = mem.session_summaries[-10:]
        self.save(mem)
        return mem

    # ── 汇总 ──────────────────────────────

    def get_learning_summary(self, student_id: str) -> Dict[str, Any]:
        """生成学习摘要"""
        mem = self.load(student_id)

        # Top 掌握概念 (score ≥ 0.7)
        strengths = [
            {"concept": c, "mastery": s}
            for c, s in sorted(mem.mastery_map.items(), key=lambda x: -x[1])
            if s >= 0.7
        ]

        # Top 薄弱概念 (score ≤ 0.3 或 在 weak_points 中)
        weaknesses_from_mastery = [
            {"concept": c, "mastery": s}
            for c, s in sorted(mem.mastery_map.items(), key=lambda x: x[1])
            if s <= 0.3
        ]
        weaknesses_from_reports = [
            {"concept": w["concept"], "count": w["occurrence_count"]}
            for w in mem.weak_points[:5]
        ]

        # 学习统计
        beh = mem.learning_behavior
        sessions = len(mem.session_summaries)
        avg_score = beh.get("avg_score", 0)

        return {
            "student_id": student_id,
            "total_interactions": beh.get("interaction_count", 0),
            "avg_score": avg_score,
            "total_sessions": sessions,
            "preferred_style": beh.get("preferred_style", ""),
            "avg_pace": beh.get("avg_pace", "normal"),
            "strengths": strengths[:5],
            "weaknesses_mastery": weaknesses_from_mastery[:5],
            "weaknesses_reported": weaknesses_from_reports,
            "recent_feedback": mem.feedback_history[-3:] if mem.feedback_history else [],
            "latest_profile": mem.profile_history[-1] if mem.profile_history else {},
            "last_updated": mem.updated_at,
        }
