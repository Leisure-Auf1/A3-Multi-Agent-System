"""
Phase 8.3-D2 — StudentGoal Model

Long-term learning goal management. Defines the data model for what
a student is learning *for* — career target, exam target, skill target.

Constituent of PlannerAgent goal-driven routing, ContentGeneratorAgent
goal-driven material selection, and ResourceAgent goal-driven recommendations.

NOT part of Veritas-Core — this is A3 project-level domain logic.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum


# ──────────────────────────────────────────────
# Goal Types
# ──────────────────────────────────────────────

class GoalCategory(str, Enum):
    """What kind of long-term target the student is aiming for."""
    CAREER = "career"           # 职业发展 (e.g. "成为 Python 后端工程师")
    EXAM = "exam"               # 考试/认证 (e.g. "通过 CKA", "考研")
    SKILL = "skill"             # 技能掌握 (e.g. "掌握 Multi-Agent 系统开发")
    PROJECT = "project"         # 项目产出 (e.g. "构建一个智能客服系统")
    GENERAL = "general"         # 通用学习 (default, no specific target)


# ──────────────────────────────────────────────
# Goal Target Types (sub-classification)
# ──────────────────────────────────────────────

class TargetLevel(str, Enum):
    """Mastery level target for exams and skill goals."""
    BEGINNER = "beginner"       # 入门理解
    INTERMEDIATE = "intermediate"  # 熟练运用
    ADVANCED = "advanced"       # 专家级掌握
    CERTIFIED = "certified"     # 通过认证


# ──────────────────────────────────────────────
# Career Path Presets
# ──────────────────────────────────────────────

CAREER_PATHS: Dict[str, Dict[str, Any]] = {
    "python_backend": {
        "label": "Python 后端工程师",
        "target_skills": ["python", "flask", "fastapi", "database", "api_design", "docker"],
        "recommended_course": "python_advanced",
        "description": "掌握 Python 后端开发全栈，能够独立设计 RESTful API 并部署上线。",
        "difficulty": "intermediate",
    },
    "ai_engineer": {
        "label": "AI 应用工程师",
        "target_skills": ["python", "machine_learning", "llm", "rag", "agent_framework"],
        "recommended_course": "multi_agent_ai",
        "description": "能够使用大语言模型构建 Agent 应用，掌握 RAG、Tool Calling、Multi-Agent 协作。",
        "difficulty": "advanced",
    },
    "data_analyst": {
        "label": "数据分析师",
        "target_skills": ["python", "pandas", "numpy", "matplotlib", "sql", "statistics"],
        "recommended_course": "python_basics",
        "description": "使用 Python 进行数据清洗、分析和可视化。",
        "difficulty": "beginner",
    },
    "fullstack_dev": {
        "label": "全栈开发者",
        "target_skills": ["python", "javascript", "react", "api_design", "database", "devops"],
        "recommended_course": "python_advanced",
        "description": "掌握前后端全流程开发，能够独立交付完整 Web 应用。",
        "difficulty": "advanced",
    },
    "ml_engineer": {
        "label": "机器学习工程师",
        "target_skills": ["python", "machine_learning", "deep_learning", "numpy", "pytorch", "mlops"],
        "recommended_course": "python_ai_engineer",
        "description": "掌握机器学习全流程：数据处理、模型训练、评估、部署。",
        "difficulty": "advanced",
    },
}

EXAM_PATHS: Dict[str, Dict[str, Any]] = {
    "pcep": {
        "label": "PCEP (Python Certified Entry-Level)",
        "target_skills": ["python_basics", "control_flow", "functions", "data_types"],
        "recommended_course": "python_basics",
        "description": "Python 入门级认证，验证基础编程能力。",
        "difficulty": "beginner",
    },
    "cka": {
        "label": "CKA (Certified Kubernetes Administrator)",
        "target_skills": ["kubernetes", "docker", "linux", "networking", "storage"],
        "recommended_course": "python_advanced",
        "description": "Kubernetes 管理员认证，验证集群管理能力。",
        "difficulty": "advanced",
    },
    "ai_certificate": {
        "label": "AI Agent 开发认证",
        "target_skills": ["agent_framework", "llm", "tool_calling", "rag", "multi_agent"],
        "recommended_course": "multi_agent_ai",
        "description": "掌握 Multi-Agent AI 系统开发全流程。",
        "difficulty": "advanced",
    },
}


# ──────────────────────────────────────────────
# Milestone Model
# ──────────────────────────────────────────────

@dataclass
class Milestone:
    """A measurable checkpoint within a long-term goal."""
    milestone_id: str
    title: str                          # e.g. "完成 Python 基础语法学习"
    description: str = ""
    target_concepts: List[str] = field(default_factory=list)  # concepts to master
    target_mastery: float = 0.8         # 0.0-1.0 mastery threshold
    estimated_days: int = 0             # estimated days to complete
    completed: bool = False
    completed_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "milestone_id": self.milestone_id,
            "title": self.title,
            "description": self.description,
            "target_concepts": self.target_concepts,
            "target_mastery": self.target_mastery,
            "estimated_days": self.estimated_days,
            "completed": self.completed,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Milestone":
        return cls(
            milestone_id=data.get("milestone_id", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            target_concepts=data.get("target_concepts", []),
            target_mastery=data.get("target_mastery", 0.8),
            estimated_days=data.get("estimated_days", 0),
            completed=data.get("completed", False),
            completed_at=data.get("completed_at", ""),
        )


# ──────────────────────────────────────────────
# StudentGoal Model
# ──────────────────────────────────────────────

@dataclass
class StudentGoal:
    """
    Long-term learning goal for a student.

    Captures WHY the student is learning — career path, exam target,
    or specific skill mastery target. Used by PlannerAgent for
    goal-driven routing, ContentGeneratorAgent for goal-aligned
    materials, and ResourceAgent for career/exam-oriented recommendations.

    Fields:
        goal_id:       Unique identifier
        student_id:    Owner student
        category:      GoalCategory (career | exam | skill | project | general)
        target:        Human-readable target description
        target_level:  TargetLevel (beginner | intermediate | advanced | certified)
        milestones:    Checkpoint milestones with concept targets
        deadline:      Optional deadline ISO date
        progress:      Overall progress 0.0-1.0 (computed from milestones)
        metadata:      Extensible metadata (career_path, exam_path presets, etc.)
    """

    goal_id: str
    student_id: str
    category: str = "general"           # GoalCategory value
    target: str = ""                    # e.g. "成为 Python 后端工程师"
    target_level: str = "beginner"      # TargetLevel value
    milestones: List[Milestone] = field(default_factory=list)
    deadline: str = ""                  # ISO date string, optional
    progress: float = 0.0               # 0.0-1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # ── Computed ──────────────────────────

    @property
    def total_milestones(self) -> int:
        return len(self.milestones)

    @property
    def completed_milestones(self) -> int:
        return sum(1 for m in self.milestones if m.completed)

    @property
    def estimated_total_days(self) -> int:
        return sum(m.estimated_days for m in self.milestones)

    @property
    def is_overdue(self) -> bool:
        """Check if deadline has passed."""
        if not self.deadline:
            return False
        try:
            from datetime import date as dt_date
            return dt_date.fromisoformat(self.deadline) < dt_date.today()
        except (ValueError, TypeError):
            return False

    @property
    def days_remaining(self) -> Optional[int]:
        """Days until deadline, or None if no deadline."""
        if not self.deadline:
            return None
        try:
            from datetime import date as dt_date
            delta = dt_date.fromisoformat(self.deadline) - dt_date.today()
            return delta.days
        except (ValueError, TypeError):
            return None

    # ── Methods ───────────────────────────

    def recompute_progress(self) -> float:
        """Recompute overall progress from milestone completion."""
        if not self.milestones:
            self.progress = 0.0
        else:
            completed_weight = sum(
                1.0 for m in self.milestones if m.completed
            )
            self.progress = round(completed_weight / len(self.milestones), 2)
        return self.progress

    def check_milestones_against_mastery(
        self,
        mastery_map: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        Check which milestones are met based on current mastery_map.

        Returns:
            {
                "newly_completed": [...milestone_ids],
                "still_pending": [...milestone_ids],
                "progress_before": float,
                "progress_after": float,
            }
        """
        progress_before = self.progress
        newly_completed = []

        for m in self.milestones:
            if m.completed:
                continue
            if not m.target_concepts:
                continue
            # All target concepts must meet threshold
            all_met = all(
                mastery_map.get(c, 0.0) >= m.target_mastery
                for c in m.target_concepts
            )
            if all_met:
                m.completed = True
                m.completed_at = datetime.now(timezone.utc).isoformat()
                newly_completed.append(m.milestone_id)

        progress_after = self.recompute_progress()

        return {
            "newly_completed": newly_completed,
            "still_pending": [
                m.milestone_id for m in self.milestones if not m.completed
            ],
            "progress_before": progress_before,
            "progress_after": progress_after,
        }

    def get_next_milestone(self) -> Optional[Milestone]:
        """Get the first uncompleted milestone."""
        for m in self.milestones:
            if not m.completed:
                return m
        return None

    def get_pending_concepts(self) -> List[str]:
        """Collect all concepts from uncompleted milestones."""
        concepts = []
        for m in self.milestones:
            if not m.completed:
                concepts.extend(m.target_concepts)
        return list(dict.fromkeys(concepts))  # dedup preserving order

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "student_id": self.student_id,
            "category": self.category,
            "target": self.target,
            "target_level": self.target_level,
            "milestones": [m.to_dict() for m in self.milestones],
            "deadline": self.deadline,
            "progress": self.progress,
            "completed_milestones": self.completed_milestones,
            "total_milestones": self.total_milestones,
            "estimated_total_days": self.estimated_total_days,
            "is_overdue": self.is_overdue,
            "days_remaining": self.days_remaining,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StudentGoal":
        milestones = [
            Milestone.from_dict(m) for m in data.get("milestones", [])
        ]
        return cls(
            goal_id=data.get("goal_id", ""),
            student_id=data.get("student_id", ""),
            category=data.get("category", "general"),
            target=data.get("target", ""),
            target_level=data.get("target_level", "beginner"),
            milestones=milestones,
            deadline=data.get("deadline", ""),
            progress=data.get("progress", 0.0),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    @classmethod
    def from_preset(
        cls,
        student_id: str,
        category: str,
        preset_id: str,
        deadline: str = "",
    ) -> Optional["StudentGoal"]:
        """
        Create a StudentGoal from a preset career/exam path.

        Args:
            student_id: Student ID
            category: "career" or "exam"
            preset_id: Key in CAREER_PATHS or EXAM_PATHS
            deadline: Optional deadline

        Returns:
            StudentGoal or None if invalid preset
        """
        if category == "career":
            preset = CAREER_PATHS.get(preset_id)
        elif category == "exam":
            preset = EXAM_PATHS.get(preset_id)
        else:
            return None

        if preset is None:
            return None

        import uuid

        # Generate milestones from target skills
        milestones = []
        for i, skill in enumerate(preset.get("target_skills", [])):
            milestones.append(Milestone(
                milestone_id=f"ms_{preset_id}_{i + 1}",
                title=f"掌握 {skill.replace('_', ' ').title()}",
                description=f"达到 {preset.get('label', '')} 所需的 {skill} 能力",
                target_concepts=[skill],
                target_mastery=0.8,
                estimated_days=7 if preset.get("difficulty") == "advanced" else 5,
            ))

        goal = cls(
            goal_id=uuid.uuid4().hex[:16],
            student_id=student_id,
            category=category,
            target=preset.get("label", ""),
            target_level=preset.get("difficulty", "beginner"),
            milestones=milestones,
            deadline=deadline,
            metadata={
                "preset_id": preset_id,
                "preset_type": category,
                "recommended_course": preset.get("recommended_course", ""),
                "description": preset.get("description", ""),
            },
        )
        goal.recompute_progress()
        return goal
