# Phase 12 — Multimodal Resource Strategy

> Analysis: extending ResourceGenerationAgent to cover competition requirements
> Date: 2026-07-13

---

## 1. Current Capability Map

| # | Resource Type | Generator | Output Format | Dashboard Card |
|:--|:--------------|:----------|:--------------|:---------------|
| 1 | 📄 Course explanation | `generate_course_notes()` | Markdown sections | ✅ Document card |
| 2 | 🧠 Knowledge graph / mind map | `generate_mind_map()` | Mermaid code | ✅ Mindmap card |
| 3 | ✏️ Exercises | `generate_exercises()` | Questions + rubrics | ✅ Exercise card |
| 4 | 📖 Extended reading | (not yet) | — | — |
| 5 | 💻 Code practice | `generate_code_lab()` | Starter code + hints | ✅ Code card |
| 6 | 🎬 Video teaching script | `generate_video_script()` | Scene narration | ✅ Video card |
| 7 | 🎨 Animation storyboard | (not yet) | — | — |

**Gap:** 2 of 7 types not yet generated (extended reading, animation storyboard).

---

## 2. Strategy: Lightweight Extension

### Principle: No New AI Model

The existing `ResourceGenerationAgent` already generates 5 types. Two more can be added as lightweight generators without introducing a new model or heavy pipeline.

### Proposed: `generate_extended_reading()`

**Input:** Topic + concepts + knowledge base chapter references

**Output:**
```python
{
    "type": "extended_reading",
    "title": "Further Reading: Multi-Agent Architecture",
    "references": [
        {
            "title": "Generative Agents: Interactive Simulacra",
            "authors": "Park et al., 2023",
            "source": "arXiv:2304.03442",
            "relevance": "Foundation paper on agent simulation",
            "difficulty": "advanced"
        },
        ...
    ],
    "discussion_prompts": [
        "How does event-driven communication differ from message passing?",
        ...
    ],
    "estimated_read_minutes": 30
}
```

**Implementation approach:**
- Read `resources.json` → `external_references` array
- Filter by chapter, difficulty, profile
- Generate discussion prompts from chapter learning objectives
- ~50 lines of new code

### Proposed: `generate_animation_prompt()`

**Input:** Concept + visual style preference

**Output:**
```python
{
    "type": "animation_prompt",
    "title": "How Self-Attention Works — Animation Storyboard",
    "frames": [
        {
            "frame": 1,
            "duration": "3s",
            "visual": "Input sequence: [The, cat, sat, on, the, mat]",
            "narration": "We start with a sequence of tokens...",
            "highlight": "attention_weights[0]"
        },
        ...
    ],
    "total_duration_seconds": 30,
    "style": "visual_dominant"  # from student profile
}
```

**Implementation approach:**
- Template-based frame generation from concept description
- Student's cognitive_style affects visual design
- ~60 lines of new code
- Does NOT render animation — only generates the prompt/storyboard

---

## 3. Proposed Lightweight Agent

### MultimodalResourceAgent (proposed, NOT to implement yet)

```python
class MultimodalResourceAgent:
    """
    Lightweight wrapper that extends ResourceGenerationAgent.
    Adds 2 resource types without new AI models.
    """

    RESOURCE_TYPES = {
        **ResourceGenerationAgent.RESOURCE_TYPES,
        "extended_reading": {"icon": "📖", "label": "Extended Reading"},
        "animation_prompt": {"icon": "🎨", "label": "Animation Storyboard"},
    }

    def __init__(self, kb_loader=None):
        self.base = ResourceGenerationAgent()
        self.kb = kb_loader

    def generate_all(self, topic, concepts):
        """Generate all 7 types."""
        resources = self.base.generate_all(topic, concepts)
        resources["extended_reading"] = self.generate_extended_reading(concepts)
        resources["animation_prompt"] = self.generate_animation_prompt(topic, concepts)
        return resources
```

**Design decisions:**
1. **Composition over inheritance** — wraps ResourceGenerationAgent, doesn't modify it
2. **No new LLM calls** — all generation is template-based
3. **KB integration** — reads `resources.json` for reference data
4. **Profile-aware** — visual style from student profile
5. **Zero risk** — if not needed, the 5-type agent still works independently

---

## 4. Input/Output Contract

### Unified Resource Format

Every resource follows this contract:

```python
@dataclass
class MultimodalResource:
    type: str           # document | mindmap | exercise | code | video | extended_reading | animation_prompt
    title: str
    format: str         # markdown | mermaid | json
    data: Dict[str, Any]  # Type-specific payload
    metadata: Dict[str, Any] = field(default_factory=lambda: {
        "generated_by": "ResourceGenerationAgent",
        "timestamp": "",
        "confidence": 1.0,
    })

    def to_markdown(self) -> str: ...
    def to_dict(self) -> Dict[str, Any]: ...
    def to_card(self) -> Dict[str, str]: ...  # Dashboard card data
```

### Dashboard Card Mapping

```
MultimodalResource.to_card()
        │
        ▼
render_multimodal_cards()  (web/v1/components.py)
        │
        ▼
Colored card with: icon + title + preview expander
```

---

## 5. Competition Impact Assessment

| Resource Type | Competition Value | Implementation Cost |
|:--------------|:-----------------:|:-------------------:|
| Course notes | ★★★★★ Essential | Already done |
| Mind map | ★★★★★ Essential | Already done |
| Exercises | ★★★★☆ Important | Already done |
| Code lab | ★★★★☆ Important | Already done |
| Video script | ★★★☆☆ Nice | Already done |
| **Extended reading** | **★★★☆☆ Nice** | **~50 lines** |
| **Animation storyboard** | **★★☆☆☆ Bonus** | **~60 lines** |

### Recommendation

- **Implement extended reading NOW** — low cost, shows knowledge breadth
- **Propose animation storyboard** — implement only if time permits
- **Do NOT introduce new AI models** — reuse existing infrastructure

---

## 6. Non-Multimodal Items (Out of Scope)

These are explicitly NOT part of this strategy:

- ❌ Actual video rendering (requires video generation model)
- ❌ Audio narration generation (requires TTS model)
- ❌ Interactive 3D visualizations (requires WebGL/game engine)
- ❌ Real-time animation rendering (requires rendering engine)

The A3 system generates **descriptions and prompts** for multimodal content. Actual rendering is left to external tools (video editors, animation software, TTS engines). This is the correct boundary for an AI agent system.
