"""A3 Agent 模块 — 学生入口与个性化引擎"""
from .profile_agent import ProfileAgent, ProfileExtractionResult
from .planner_agent import PlannerAgent, LearningPlan, PlanNode
from .resource_agent import ResourceAgent, ResourceItem, ResourceRecommendation
from .reflection_agent import ReflectionAgent, ReflectionResult
from .resource_generation_agent import ResourceGenerationAgent
from .resource_recommendation_agent import ResourceRecommendationAgent, RecommendedResource, PersonalizedResourcePlan
from .conversation_profile_agent import ConversationProfileAgent
from .tutor_agent import TutorAgent, TutorContext, TutorResponse
from .evaluation_agent import EvaluationAgent, QuizQuestion, QuizResult, StudentAnswer, ErrorAnalysis
from .content_generator_agent import (
    ContentGeneratorAgent, TeachingMaterial, Chapter,
    ConceptItem, ExampleItem, ExerciseItem,
)
# Phase 8.3-D2 — StudentGoal
from .student_goal import (
    StudentGoal, Milestone, GoalCategory, TargetLevel,
    CAREER_PATHS, EXAM_PATHS,
)
# Phase 8.3-F1 — PPT Generator
from .ppt_generator_agent import (
    PPTGeneratorAgent, PPTStructure, SlideItem,
)
# Phase 8.3-F2 — Image Generator
from .image_generator_agent import (
    ImageGeneratorAgent, ImageArtifact,
)
# Phase 8.3-F3 — Video Generator
from .video_generator_agent import (
    VideoGeneratorAgent, VideoScript, VideoScene, VideoArtifact,
)

__all__ = [
    "ProfileAgent", "ProfileExtractionResult",
    "PlannerAgent", "LearningPlan", "PlanNode",
    "ResourceAgent", "ResourceItem", "ResourceRecommendation",
    "ReflectionAgent", "ReflectionResult",
    "ResourceGenerationAgent",
    "ResourceRecommendationAgent", "RecommendedResource", "PersonalizedResourcePlan",
    "ConversationProfileAgent",
    "TutorAgent", "TutorContext", "TutorResponse",
    "EvaluationAgent", "QuizQuestion", "QuizResult", "StudentAnswer",
    "ErrorAnalysis",
    "ContentGeneratorAgent", "TeachingMaterial", "Chapter",
    "ConceptItem", "ExampleItem", "ExerciseItem",
    # Phase 8.3-D2
    "StudentGoal", "Milestone", "GoalCategory", "TargetLevel",
    "CAREER_PATHS", "EXAM_PATHS",
    # Phase 8.3-F1
    "PPTGeneratorAgent", "PPTStructure", "SlideItem",
    # Phase 8.3-F2
    "ImageGeneratorAgent", "ImageArtifact",
    # Phase 8.3-F3
    "VideoGeneratorAgent", "VideoScript", "VideoScene", "VideoArtifact",
]
