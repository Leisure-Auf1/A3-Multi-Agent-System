"""
Memory Manager — 统一 Memory 入口

所有 Agent 通过此入口访问记忆层，避免直接操作 JSON 文件。
未来可替换底层存储 (JSON → Vector DB)。
"""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional

from .student_memory import StudentMemory, StudentMemoryStore
from .experience_memory import ExperienceMemoryStore, ExperienceRecord


class MemoryManager:
    """
    Memory 层统一入口.

    使用:
        mm = MemoryManager()
        mem = mm.get_student_memory("student_001")
        mm.update_student_memory("student_001", profile={...})
        lessons = mm.recall_experience("closures", "visual_dominant")
        mm.store_experience(problem="...", cause="...", ...)
    """

    def __init__(
        self,
        storage_root: Optional[str] = None,
        auto_seed: bool = True,
    ):
        base = Path(storage_root) if storage_root else None
        self.students = StudentMemoryStore(
            str(base / "students") if base else None
        )
        self.experience = ExperienceMemoryStore(
            str(base / "experience") if base else None
        )
        if auto_seed:
            self._ensure_seeded()

    def _ensure_seeded(self) -> None:
        """确保经验库有预置数据"""
        if self.experience.stats()["total_lessons"] == 0:
            self.experience.seed_default_lessons()

    # ── 学生记忆 ──────────────────────────

    def get_student_memory(self, student_id: str) -> StudentMemory:
        """获取或创建学生记忆"""
        return self.students.load(student_id)

    def student_exists(self, student_id: str) -> bool:
        return self.students.exists(student_id)

    def list_students(self) -> List[str]:
        return self.students.list_all()

    def update_student_memory(
        self,
        student_id: str,
        profile: Optional[Dict[str, str]] = None,
        mastery_updates: Optional[Dict[str, float]] = None,
        weak_point: Optional[Dict[str, Any]] = None,
        feedback: Optional[Dict[str, Any]] = None,
        session: Optional[Dict[str, Any]] = None,
    ) -> StudentMemory:
        """
        批量更新学生记忆.

        Args:
            student_id: 学生ID
            profile: 新画像 (可选)
            mastery_updates: 掌握度更新 (可选)
            weak_point: 弱点添加 (可选, 含 concept/error_type)
            feedback: 反馈记录 (可选, 含 node_id/score)
            session: 会话摘要 (可选)
        """
        if profile:
            self.students.update_profile(student_id, profile)

        if mastery_updates:
            self.students.update_mastery(student_id, mastery_updates)

        if weak_point:
            self.students.add_weak_point(
                student_id,
                concept=weak_point.get("concept", ""),
                error_type=weak_point.get("error_type", ""),
                occurrence_count=weak_point.get("occurrence_count", 1),
            )

        if feedback:
            self.students.add_feedback(
                student_id,
                node_id=feedback.get("node_id", ""),
                score=feedback.get("score", 0),
                issues=feedback.get("issues"),
            )

        if session:
            self.students.add_session_summary(
                student_id,
                course_id=session.get("course_id", ""),
                nodes_completed=session.get("nodes_completed", 0),
                total_score=session.get("total_score", 0.0),
                time_spent=session.get("time_spent", 0),
            )

        return self.students.load(student_id)

    def get_learning_summary(self, student_id: str) -> Dict[str, Any]:
        return self.students.get_learning_summary(student_id)

    # ── 经验记忆 ──────────────────────────

    def recall_experience(
        self,
        node_id: str = "",
        profile_type: str = "",
        query: str = "",
        limit: int = 3,
    ) -> List[ExperienceRecord]:
        """
        召回相关经验.

        优先级: query (关键词) > node_id + profile_type
        """
        if query:
            return self.experience.search_similar(query, limit=limit)
        return self.experience.get_relevant_lessons(
            node_id=node_id,
            profile_type=profile_type,
            limit=limit,
        )

    def store_experience(
        self,
        problem: str,
        cause: str,
        context: str,
        solution: str,
        source: str = "unknown",
        node_id: str = "",
        applicable_profile: str = "",
        severity: str = "MEDIUM",
    ) -> ExperienceRecord:
        """存储一条经验"""
        return self.experience.add_lesson(
            problem=problem,
            cause=cause,
            context=context,
            solution=solution,
            source=source,
            node_id=node_id,
            applicable_profile=applicable_profile,
            severity=severity,
        )

    def mark_experience_result(
        self,
        record_id: str,
        was_successful: bool,
    ) -> None:
        """标记经验使用结果"""
        self.experience.update_success_rate(record_id, was_successful)

    def get_experience_stats(self) -> Dict[str, Any]:
        return self.experience.stats()
