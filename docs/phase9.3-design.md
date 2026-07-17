# Phase 9.3 — Multimodal Generation Gateway: Design

> **Version:** 1.0 | **Date:** 2026-07-17 | **Type:** Design-Only (no code)  
> **Constraint:** Zero Veritas-Core V7 API changes | Zero Runtime modifications  
> **Existing Foundation:** `src/agents/resource_generation_agent.py` (Phase 11, 508 LOC)

---

## 1. Current State

### 1.1 Existing ResourceGenerationAgent

```
ResourceGenerationAgent
├── CourseNotes       📄  → Markdown (structured sections)
├── MindMap           🧠  → Mermaid JSON (nodes + edges)
├── Exercise          ✏️  → Questions + rubrics
├── CodeLab           💻  → Runnable code with expected output
├── VideoScript       🎬  → Narration script (scenes + dialogue)
└── ExtendedReading   📖  → Curated references from KB
```

**Architecture:** Rule-based generation + optional LLM enrichment via `self.llm.generate()`.

### 1.2 What's Missing

| Gap | Phase 9.3 Target |
|:----|:-----------------|
| PPT 课件 | New resource type |
| 图片生成 (diagrams, illustrations) | Multimodal Gateway → external API |
| 音频生成 (narration TTS) | Multimodal Gateway → external API |
| 统一 abstraction over multiple backends | Gateway pattern |
| 离线全降级策略 | Rule-based fallback chain |
| Agent 协作编排 | Collaboration flow spec |
| 资源质量验证 | Validation pipeline |

---

## 2. Architecture Design

### 2.1 Multimodal Gateway Abstraction

```
┌───────────────────────────────────────────────────────────┐
│               Multimodal Gateway (NEW)                     │
│                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ TextGateway  │  │ ImageGateway│  │ AudioGateway │       │
│  │ (LLM API)   │  │ (DALL-E,    │  │ (TTS API)   │       │
│  │             │  │  StableDiff)│  │             │       │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │
│         │                │                │               │
│  ┌──────┴────────────────┴────────────────┴──────┐       │
│  │         GatewayRouter                          │       │
│  │  • Provider selection (env var / config)       │       │
│  │  • Rate limiting + retry                      │       │
│  │  • Cost tracking                              │       │
│  │  • Fallback chain: API → Rule → Placeholder   │       │
│  └──────────────────────┬───────────────────────┘       │
│                         │                               │
└─────────────────────────┼───────────────────────────────┘
                          │
                          ▼
┌───────────────────────────────────────────────────────────┐
│          ResourceGenerationAgent (ENHANCED)                │
│                                                           │
│  RESOURCE_TYPES:                                          │
│    📄 document      → CourseNotes (Markdown)               │
│    🧠 mindmap       → MindMap (Mermaid JSON)               │
│    ✏️ exercise      → Exercises                            │
│    💻 code          → CodeLab                              │
│    🎬 video         → VideoScript                          │
│    📖 reading       → ExtendedReading                      │
│    📊 slides        → PPT 课件 (NEW)                       │
│    🖼️ illustration  → 概念插图 (NEW, via ImageGateway)     │
│                                                           │
│  Pipeline:                                                │
│    Knowledge Base ─→ ResourceGenerationAgent               │
│                         │                                 │
│                         ├─→ Rule-based (always available)  │
│                         ├─→ LLM-enriched (optional)        │
│                         ├─→ Image generation (optional)    │
│                         └─→ Audio narration (optional)     │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### 2.2 Gateway Module Structure

```
src/multimodal/               ← NEW directory
├── __init__.py
├── gateway.py                # GatewayRouter, GatewayConfig
├── text_gateway.py           # TextGateway (LLM API adapter)
├── image_gateway.py          # ImageGateway (DALL-E, StableDiffusion, etc.)
├── audio_gateway.py          # AudioGateway (TTS: OpenAI, ElevenLabs, Edge)
├── fallback.py               # Rule-based fallback generators
└── types.py                  # Shared types: GenerationRequest, GenerationResult
```

---

## 3. Resource Types — Complete Catalog

### 3.1 New: 📊 PPT Slides

```python
@dataclass
class PPTSlides:
    """Generated presentation slides resource."""
    title: str
    topic: str
    slides: List[SlideData]       # Each slide = {title, bullets, notes, image_prompt}
    total_slides: int
    format: str = "markdown"      # "markdown" | "pptx_json" | "reveal_html"
    image_prompts: List[str]      # Prompts for illustration generation
    estimated_duration_minutes: int = 20

@dataclass
class SlideData:
    slide_number: int
    title: str
    bullets: List[str]
    speaker_notes: str
    image_prompt: Optional[str]   # If illustration desired
    layout: str = "title_and_body"  # title_and_body | two_column | big_image
```

### 3.2 New: 🖼️ Concept Illustration

```python
@dataclass
class ConceptIllustration:
    """AI-generated concept illustration."""
    prompt: str
    image_url: Optional[str]        # Generated image URL
    image_base64: Optional[str]     # Fallback: base64 placeholder
    style: str = "educational"      # educational | diagram | infographic
    alt_text: str = ""
    generation_status: str = "pending"  # pending | generated | failed | fallback
```

### 3.3 Existing: 6 Types Already Implemented

See `src/agents/resource_generation_agent.py` for CourseNotes, MindMap, Exercise, CodeLab, VideoScript, ExtendedReading.

---

## 4. Multimodal API Integration Strategy

### 4.1 Provider Configuration

```yaml
# A3 config (e.g., config.yaml or env vars)
multimodal:
  text:
    provider: deepseek           # deepseek | openai | mock
    model: deepseek-v4-pro
    api_key: ${DEEPSEEK_API_KEY}
    base_url: https://api.deepseek.com/v1

  image:
    provider: fal                # fal | openai | stability | mock
    model: FLUX.2-Klein-9B
    api_key: ${FAL_KEY}
    max_images_per_request: 4
    default_style: educational

  audio:
    provider: edge               # edge | openai | elevenlabs | mock
    voice: zh-CN-XiaoxiaoNeural
    language: zh-CN

  fallback:
    image_placeholder_style: geometric   # geometric | emoji | ascii
    audio_fallback_text: "Audio generation unavailable. Please read the script below."
```

### 4.2 API Route Design

```
POST   /api/v2/resources/generate          → Generate all resource types for a topic
POST   /api/v2/resources/generate/notes    → Generate course notes
POST   /api/v2/resources/generate/slides   → Generate PPT slides
POST   /api/v2/resources/generate/mindmap  → Generate mind map
POST   /api/v2/resources/generate/exercise → Generate exercises
POST   /api/v2/resources/generate/codelab  → Generate code lab
POST   /api/v2/resources/generate/illustration → Generate concept illustration
GET    /api/v2/resources/status/{task_id}  → Check generation status (async)
GET    /api/v2/resources/list              → List available resources for a course
```

### 4.3 Request/Response Contracts

```python
# ── Generate All ──
class GenerateAllRequest:
    topic: str
    concepts: List[str]
    student_level: str = "beginner"
    resource_types: List[str] = ["document", "mindmap", "exercise"]
    enrich: bool = False          # Use LLM enrichment
    generate_images: bool = False  # Use ImageGateway
    generate_audio: bool = False   # Use AudioGateway

class GenerateAllResponse:
    task_id: str
    resources: Dict[str, Any]     # {resource_type: resource_data}
    images: List[ConceptIllustration]
    status: str                   # "complete" | "partial" | "fallback"
    warnings: List[str]           # "Image API unavailable — using placeholder"
```

---

## 5. Agent Collaboration Flow

### 5.1 Full Learning Pipeline

```
Student Input (goal + profile)
        │
        ▼
┌───────────────────┐
│   ProfileAgent    │ ──→ DynamicProfile (6 dimensions)
└───────┬───────────┘
        │ profile
        ▼
┌───────────────────┐
│   PlannerAgent    │ ──→ LearningPlan (nodes + path)
└───────┬───────────┘
        │ plan nodes
        ▼
┌───────────────────┐
│  ResourceAgent    │ ──→ ResourcePlan (recommended resources)
└───────┬───────────┘
        │ resource specs
        ▼
┌───────────────────────────────┐
│  ResourceGenerationAgent      │  ← Phase 9.3 ENHANCED
│                               │
│  Input:  LearningPlan nodes   │
│          Student profile      │
│          Resource plan        │
│                               │
│  ┌─────────────────────────┐  │
│  │ 1. Text Generation      │  │  → CourseNotes, ExtendedReading
│  │    (rule + LLM enrich)  │  │
│  ├─────────────────────────┤  │
│  │ 2. Visual Generation    │  │  → MindMap, Slides, Illustrations
│  │    (rule + ImageGateway)│  │
│  ├─────────────────────────┤  │
│  │ 3. Interactive Gen      │  │  → Exercises, CodeLabs
│  │    (rule + LLM enrich)  │  │
│  ├─────────────────────────┤  │
│  │ 4. Media Generation     │  │  → VideoScript, Audio
│  │    (rule + AudioGateway)│  │
│  └───────────┬─────────────┘  │
│              │                │
└──────────────┼────────────────┘
               │ all resources
               ▼
┌───────────────────┐
│   TutorAgent      │ ──→ Uses generated resources in tutoring session
└───────┬───────────┘
        │ learning session
        ▼
┌───────────────────┐
│ EvaluationAgent   │ ──→ Quiz on learning content, identifies gaps
└───────┬───────────┘
        │ evaluation result
        ▼
┌───────────────────┐
│ ReflectionAgent   │ ──→ Post-learning reflection, update StudentMemory
└───────────────────┘
```

### 5.2 Conditional Resource Generation

```
PlannerAgent determines LearningPlan
        │
        ├─→ plan_node.type == "theory"
        │     └─→ generate: CourseNotes + MindMap + ExtendedReading
        │
        ├─→ plan_node.type == "practice"
        │     └─→ generate: Exercises + CodeLab
        │
        ├─→ plan_node.type == "visual"
        │     └─→ generate: Slides + Illustrations + MindMap
        │
        └─→ plan_node.type == "deep_dive"
              └─→ generate: VideoScript + ExtendedReading + CodeLab
```

---

## 6. Offline Fallback Strategy

### 6.1 Fallback Chain

```
Request: generate_illustration("neural network diagram", style="educational")
        │
        ├─→ Try: FAL Image API (FLUX.2-Klein-9B)
        │     ├─ Success → Return image URL ✅
        │     └─ Fail (network, API key, rate limit)
        │         │
        │         ├─→ Try: Placeholder generation (rule-based SVG/ASCII)
        │         │     └─→ Return geometric SVG placeholder ✅
        │         │
        │         └─→ Try: Unicode art fallback
        │               └─→ Return emoji-based diagram ✅ (always available)
```

### 6.2 Fallback Rules per Resource Type

| Resource | Primary | Fallback 1 | Fallback 2 (Always) |
|:---------|:--------|:-----------|:---------------------|
| CourseNotes | LLM-enriched | Rule-based template | Hardcoded template |
| MindMap | LLM-generated | Rule-based (concept→node mapping) | Static topic tree |
| Slides | LLM-enriched + Image API | Rule-based + placeholder images | Text-only markdown |
| Illustration | Image API (FAL/DALL-E) | Geometric SVG | Unicode diagram |
| Exercises | LLM-generated | Rule-based template | 3-question MCQ fallback |
| CodeLab | LLM-generated | Rule-based scaffold | Hello-world template |
| VideoScript | LLM-enriched | Rule-based scene builder | Template with blanks |
| Audio | TTS API | Pre-recorded placeholder | Text-only "Read aloud" |
| ExtendedReading | KB query + LLM curate | KB direct query | Static reading list |

### 6.3 Placeholder Image System

```python
# Geometric SVG placeholders — zero API dependency
PLACEHOLDER_TEMPLATES = {
    "educational": '<svg>... geometric diagram ...</svg>',
    "diagram":    '<svg>... flowchart placeholder ...</svg>',
    "infographic": '<svg>... data viz placeholder ...</svg>',
    "concept_map": '<svg>... node-link diagram ...</svg>',
}

def generate_placeholder_image(topic: str, style: str) -> str:
    """Generate a geometric SVG placeholder. Always available."""
    tmpl = PLACEHOLDER_TEMPLATES.get(style, PLACEHOLDER_TEMPLATES["educational"])
    return tmpl.replace("{topic}", topic)
```

---

## 7. Data Models (Complete)

### 7.1 GenerationRequest (Unified)

```python
@dataclass
class GenerationRequest:
    """Unified request for any resource generation."""
    request_id: str
    resource_type: str          # "document" | "slides" | "mindmap" | ...
    topic: str
    concepts: List[str]
    student_level: str = "beginner"
    learning_style: str = "visual_dominant"
    language: str = "zh-CN"
    enrich: bool = False        # Use LLM
    generate_media: bool = False # Use image/audio APIs
    max_resources: int = 5
    context: Dict[str, Any] = field(default_factory=dict)
```

### 7.2 GenerationResult (Unified)

```python
@dataclass
class GenerationResult:
    """Unified result from any resource generation."""
    request_id: str
    resource_type: str
    status: str                 # "success" | "partial" | "fallback" | "failed"
    data: Any                   # Resource-specific dataclass instance
    media_urls: List[str]       # Generated image/audio URLs
    fallback_used: List[str]    # Which fallbacks were activated
    warnings: List[str]
    generation_time_ms: int
    tokens_used: int = 0
    cost_estimate_usd: float = 0.0
```

---

## 8. A3Workflow Integration

### 8.1 New Handler Registration

```python
# In A3Workflow.__init__ (minimal diff)
class A3Workflow:
    def __init__(self, ...):
        # Existing agents ... unchanged
        self.resource_gen = ResourceGenerationAgent(llm_provider=llm_provider)
        self.gateway = MultimodalGateway(config)  # NEW — optional

    # NEW handler method
    def _generate_resources(self, ctx: AgentContext):
        """Generate all resources for the current learning plan."""
        plan = ctx.get("learning_plan")
        profile = ctx.get("profile")

        request = GenerationRequest(
            resource_type="all",
            topic=plan.topic,
            concepts=plan.concepts,
            student_level=profile.knowledge_base,
            learning_style=profile.cognitive_style,
            enrich=self._llm_provider is not None,
            generate_media=self.gateway is not None,
        )

        result = self.resource_gen.generate_all(request)
        ctx.set("resources", result)

        # Record to learning history
        from src.data.learning_records import record_agent_action
        record_agent_action(
            user_id=ctx.student_id,
            agent="resource_generation",
            action="generate_all",
            result={"types": list(result.data.keys())},
            duration_ms=result.generation_time_ms,
        )
```

---

## 9. Error Handling & Resilience

### 9.1 Failure Modes

| Failure | Detection | Recovery |
|:--------|:----------|:---------|
| LLM API timeout | 10s timeout | Switch to `enrich=False` (rule only) |
| Image API rate limit | HTTP 429 | Use placeholder + queue retry |
| Image API auth failure | HTTP 401/403 | Log warning → fallback to placeholder |
| Audio API unavailable | Connection error | Generate text script only |
| KB file missing | FileNotFoundError | Empty list + warning |
| Generation takes too long | >30s wall clock | Return partial result + async completion |

### 9.2 Retry Strategy

```python
# Exponential backoff for API calls
RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay_ms": 1000,
    "max_delay_ms": 10000,
    "backoff_factor": 2.0,
    "retryable_statuses": [429, 500, 502, 503],
}
```

---

## 10. Testing Plan

### 10.1 Unit Tests (30+ tests)

```
tests/test_phase9_multimodal.py

TestMultimodalGateway:
  test_gateway_router_selects_text_provider    # Config-based provider selection
  test_gateway_router_selects_image_provider
  test_gateway_router_selects_audio_provider
  test_fallback_chain_activates_on_failure     # API fail → placeholder
  test_fallback_chain_no_retry_on_auth_error   # Don't retry 401
  test_rate_limit_backoff                      # Retry with exponential delay
  test_cost_tracking_accumulates               # Cost counter increments

TestImageGateway:
  test_generate_illustration_with_mock_api     # Mock API returns image
  test_generate_illustration_fallback_placeholder  # API fail → SVG
  test_placeholder_geometric_generation        # Rule-based SVG
  test_batch_generation_limits                 # Max images per batch

TestAudioGateway:
  test_generate_narration_with_mock
  test_fallback_to_text_script

TestPPTGeneration:
  test_generate_slides_rule_based              # Without LLM
  test_generate_slides_llm_enriched            # With mock LLM
  test_slide_data_structure_valid              # All fields populated
  test_slide_count_within_limits               # Max 30 slides

TestResourceAgentEnhanced:
  test_generate_all_resource_types             # All 8 types
  test_generate_all_with_media                 # Including images
  test_generate_all_offline_mode               # Zero API calls
  test_partial_generation_returns_warnings     # Some types fail
  test_resource_type_filtering                 # Only requested types
```

### 10.2 Integration Tests

```
TestAgentCollaboration:
  test_full_pipeline_profile_to_resources      # Profile → Plan → Resources
  test_planner_triggers_correct_resource_types # Conditional generation
  test_tutor_uses_generated_resources          # TutorAgent consumes output
  test_evaluation_uses_generated_exercises     # Quiz from generated content

TestAPIRoutes:
  test_generate_endpoint_returns_all_types
  test_generate_specific_type_endpoint
  test_async_status_endpoint
  test_list_resources_endpoint
```

### 10.3 Regression Guard

- All 1064 existing tests must pass unchanged
- `test_resource_generation_agent.py` (existing 15+ tests) must pass
- Zero import errors from new modules when offline

---

## 11. Implementation Order

### Phase 9.3a — Types + Gateway Framework
```
src/multimodal/types.py          # GenerationRequest, GenerationResult, dataclasses
src/multimodal/gateway.py        # GatewayRouter, GatewayConfig
src/multimodal/fallback.py       # Placeholder generators (SVG, templates)
```

### Phase 9.3b — Gateways
```
src/multimodal/text_gateway.py   # LLM API adapter
src/multimodal/image_gateway.py  # Image generation adapter
src/multimodal/audio_gateway.py  # TTS adapter
```

### Phase 9.3c — Enhanced Agent + API
```
src/agents/resource_generation_agent.py  # Add PPT, Illustration, gateway integration
src/api/routes/resources.py              # Resource generation API endpoints
```

### Phase 9.3d — Tests
```
tests/test_phase9_multimodal.py   # 30+ new tests
```

---

## 12. Constraints Compliance

| Constraint | Compliance |
|:-----------|:-----------|
| Zero Veritas-Core V7 API changes | ✅ Gateway is A3-level, uses `veritas.llm.LLMProvider` unchanged |
| Zero Runtime modifications | ✅ No new Runtime states/hooks |
| Rule-based fallback always available | ✅ All 8 resource types have rule fallback |
| Backward compatible | ✅ Existing `ResourceGenerationAgent` API unchanged — new methods are additive |
| 1064 tests must pass | ✅ No existing file modifications; all new code is additive |

---

## 13. Summary

| Dimension | Current | Phase 9.3 Target |
|:----------|:-------:|:----------------:|
| Resource types | 6 | 8 (+PPT, +Illustration) |
| Gateway abstraction | None | 3 gateways (Text/Image/Audio) |
| API fallback | None | 3-layer fallback chain |
| Offline capability | ✅ Rule-based | ✅ Enhanced rule-based + SVG placeholders |
| Agent integration | Manual | GatewayRouter auto-selection |
| API endpoints | None | 7 new endpoints |
| Tests | 1064 | 1094+ |
