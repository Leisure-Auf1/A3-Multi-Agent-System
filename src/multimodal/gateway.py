"""
Phase 9.5 — Gateway Router

Routes resource generation requests to appropriate providers.
Applies cost control, quota checks, and fallback strategy.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field

from .artifact import ResourceArtifact, ResourceType, ArtifactStatus
from .providers.base import BaseProvider, ProviderResult
from .providers.text_provider import TextProvider
from .providers.image_provider import ImageProvider
from .providers.ppt_provider import PPTProvider
from .providers.code_provider import CodeProvider
from .cost import CostController, QuotaExceededError
from .validator import ContentValidator


@dataclass
class GenerateRequest:
    """Unified generation request."""
    student_id: str = ""
    resource_type: ResourceType = ResourceType.DOCUMENT
    topic: str = ""
    title: str = ""
    concepts: List[str] = field(default_factory=list)
    profile: Dict[str, Any] = field(default_factory=dict)
    learning_goal: str = ""
    student_level: str = "beginner"
    user_tier: str = "free"         # free | pro


class MultimodalGateway:
    """Central gateway for multimodal resource generation."""

    def __init__(self, user_tier: str = "free"):
        self.cost = CostController(user_tier)
        self.validator = ContentValidator()
        self._providers: Dict[ResourceType, BaseProvider] = {}

        # Register default providers
        self.register(ResourceType.DOCUMENT, TextProvider())
        self.register(ResourceType.MINDMAP, TextProvider())    # Text→Mermaid
        self.register(ResourceType.EXERCISE, TextProvider())
        self.register(ResourceType.CODE_LAB, CodeProvider())
        self.register(ResourceType.SLIDES, PPTProvider())
        self.register(ResourceType.VIDEO_SCRIPT, TextProvider())
        self.register(ResourceType.ILLUSTRATION, ImageProvider())

    def register(self, resource_type: ResourceType, provider: BaseProvider):
        """Register a provider for a resource type."""
        self._providers[resource_type] = provider

    def generate(self, request: GenerateRequest) -> ResourceArtifact:
        """Full generation pipeline: check quota → generate → validate."""
        artifact = ResourceArtifact(
            student_id=request.student_id,
            resource_type=request.resource_type,
            title=request.title or request.topic,
            topic=request.topic,
            status=ArtifactStatus.GENERATING,
        )

        # Step 0: Quota check
        if not self.cost.can_generate(request.resource_type):
            artifact.mark_failed("Quota exceeded for this resource type")
            return artifact

        # Step 1: Get provider
        provider = self._providers.get(request.resource_type)
        if provider is None:
            artifact.mark_failed(f"No provider for {request.resource_type.value}")
            return artifact

        # Step 2: Generate
        try:
            result = provider.generate(
                topic=request.topic,
                title=request.title,
                concepts=request.concepts,
                profile=request.profile,
                learning_goal=request.learning_goal,
                student_level=request.student_level,
            )
            artifact.content = result.content
            artifact.content_format = result.content_format
            artifact.file_path = result.file_path or ""
            artifact.media_urls = result.media_urls
            artifact.tokens_used = result.tokens_used
            artifact.cost_usd = result.cost_usd
            artifact.provider = result.provider_name
        except Exception as e:
            artifact.mark_failed(f"Generation failed: {str(e)}")
            return artifact

        # Step 3: Validate
        artifact.status = ArtifactStatus.VALIDATING
        validation = self.validator.validate(artifact)
        if not validation.passed:
            artifact.validation_errors = validation.errors
            if validation.is_critical:
                artifact.mark_failed("Validation failed (critical)")
                return artifact

        # Step 4: Activate
        artifact.mark_active()
        self.cost.record_usage(request.resource_type, artifact.tokens_used)
        return artifact

    def generate_all(self, student_id: str, topic: str, concepts: List[str],
                     profile: Dict[str, Any] = None,
                     types: List[ResourceType] = None,
                     user_tier: str = "free") -> Dict[str, ResourceArtifact]:
        """Generate all requested resource types for a topic."""
        profile = profile or {}
        types = types or list(ResourceType)
        results = {}

        for rtype in types:
            req = GenerateRequest(
                student_id=student_id,
                resource_type=rtype,
                topic=topic,
                title=f"{topic} - {rtype.value.replace('_', ' ').title()}",
                concepts=concepts,
                profile=profile,
                user_tier=user_tier,
            )
            results[rtype.value] = self.generate(req)

        return results
