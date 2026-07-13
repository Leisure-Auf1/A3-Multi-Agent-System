# Phase 13 — Extended Reading Resource Extension Plan

> Adding a 6th resource type to ResourceGenerationAgent
> Date: 2026-07-13 | A3 v2.8 → v2.9

---

## 1. Current State

`ResourceGenerationAgent` generates 5 types:

| # | Type | Method | Already Exists |
|:--|:-----|:-------|:-------------:|
| 1 | 📄 Course Notes | `generate_course_notes()` | ✅ |
| 2 | 🧠 Mind Map | `generate_mind_map()` | ✅ |
| 3 | ✏️ Exercises | `generate_exercises()` | ✅ |
| 4 | 💻 Code Lab | `generate_code_lab()` | ✅ |
| 5 | 🎬 Video Script | `generate_video_script()` | ✅ |
| **6** | **📖 Extended Reading** | `generate_extended_reading()` | **❌ (proposed)** |

---

## 2. Requirement

**Competition value:** Shows the system connects learning to the broader academic world. Not just generating content — curating references.

**Judge question:** "Where does the system get its knowledge from?"
**Answer:** "From our curated knowledge base AND curated external references. Here's how."

---

## 3. Data Source

The `resources.json` in the knowledge base already contains an `external_references` array:

```json
{
  "external_references": [
    {
      "title": "Attention Is All You Need",
      "url": "https://arxiv.org/abs/1706.03762",
      "type": "paper",
      "chapter": 2
    },
    {
      "title": "RAG: A Survey",
      "url": "https://arxiv.org/abs/2312.10997",
      "type": "paper",
      "chapter": 4
    },
    ...
  ]
}
```

**No new data needed.** The references already exist.

---

## 4. Proposed Output

```python
{
    "type": "extended_reading",
    "title": "Extended Reading: Multi-Agent Architecture",
    "summary": "Curated references for deeper understanding of multi-agent system design.",
    "references": [
        {
            "title": "Generative Agents: Interactive Simulacra of Human Behavior",
            "authors": "Park et al., 2023",
            "source": "arXiv:2304.03442",
            "type": "paper",
            "difficulty": "advanced",
            "relevance": "Foundation paper on agent simulation and emergent social behavior.",
            "estimated_read_minutes": 45
        },
        {
            "title": "CAMEL: Communicative Agents for 'Mind' Exploration",
            "authors": "Li et al., 2023",
            "source": "arXiv:2303.17760",
            "type": "paper",
            "difficulty": "intermediate",
            "relevance": "Role-playing framework for autonomous agent collaboration.",
            "estimated_read_minutes": 30
        }
    ],
    "discussion_prompts": [
        "How does the EventBus pattern compare to CAMEL's role-playing communication?",
        "What design trade-offs exist between pipeline and blackboard agent patterns?"
    ],
    "estimated_total_minutes": 75,
    "difficulty": "intermediate"
}
```

---

## 5. Implementation

### 5.1 New Method

```python
# In src/agents/resource_generation_agent.py

def generate_extended_reading(
    self,
    title: str,
    topic: str,
    chapter_ids: List[str] = None,
    difficulty: str = "intermediate",
    kb_loader: Any = None,
) -> Dict[str, Any]:
    """
    Generate extended reading list from knowledge base references.

    Args:
        title: Reading list title.
        topic: The topic area (used for discussion prompts).
        chapter_ids: Optional list of chapter IDs to filter references.
        difficulty: Target difficulty (beginner/intermediate/advanced).
        kb_loader: CourseKnowledgeBase instance for reference data.

    Returns:
        Dict with references, discussion prompts, and metadata.
    """
    references = []
    discussion_prompts = []

    # 1. Load references from KB
    if kb_loader:
        resources = kb_loader.get_resources()
        all_refs = (
            resources.get("resources", {})
            .get("external_references", [])
        )
    else:
        all_refs = self._get_default_references()

    # 2. Filter by chapter
    if chapter_ids:
        all_refs = [r for r in all_refs if r.get("chapter") in chapter_ids]

    # 3. Enrich with metadata
    for ref in all_refs[:5]:  # Max 5 references
        references.append({
            "title": ref.get("title", ""),
            "source": ref.get("url", ref.get("source", "")),
            "type": ref.get("type", "paper"),
            "difficulty": ref.get("difficulty", "intermediate"),
            "relevance": self._describe_relevance(ref, topic),
            "estimated_read_minutes": ref.get("estimated_minutes", 30),
        })

    # 4. Generate discussion prompts
    discussion_prompts = self._generate_discussion_prompts(topic, len(references))

    return {
        "type": "extended_reading",
        "title": title,
        "summary": f"Curated references for deeper understanding of {topic}.",
        "references": references,
        "discussion_prompts": discussion_prompts,
        "estimated_total_minutes": sum(r["estimated_read_minutes"] for r in references),
        "difficulty": difficulty,
        "format": "json",
    }
```

### 5.2 Helper Methods

```python
def _get_default_references(self) -> List[Dict]:
    """Hardcoded fallback references when KB is unavailable."""
    return [
        {
            "title": "Attention Is All You Need",
            "url": "https://arxiv.org/abs/1706.03762",
            "type": "paper", "chapter": 2,
            "difficulty": "advanced",
        },
        {
            "title": "Chain-of-Thought Prompting Elicits Reasoning",
            "url": "https://arxiv.org/abs/2201.11903",
            "type": "paper", "chapter": 3,
            "difficulty": "intermediate",
        },
    ]

def _describe_relevance(self, ref: Dict, topic: str) -> str:
    """Generate a relevance description for a reference."""
    templates = [
        f"Core reading for understanding {topic}.",
        f"Provides foundational concepts for {topic}.",
        f"Practical application of {topic} concepts.",
    ]
    import hashlib
    idx = int(hashlib.md5(ref.get("title", "").encode()).hexdigest()[:2], 16) % len(templates)
    return templates[idx]

def _generate_discussion_prompts(self, topic: str, num_refs: int) -> List[str]:
    """Generate discussion prompts based on topic."""
    return [
        f"How does the architecture described in the readings compare to A3's design?",
        f"What trade-offs exist between the approaches in the references and real-world systems?",
        f"Which reference is most relevant to your current learning goals? Why?",
    ][:min(num_refs, 3)]
```

### 5.3 Multimodal Card Registration

Add to `RESOURCE_TYPES`:

```python
RESOURCE_TYPES = {
    **existing_types,
    "extended_reading": {"icon": "📖", "label": "Extended Reading"},
}
```

---

## 6. Files Affected

| File | Change | Lines |
|:-----|:-------|:------|
| `src/agents/resource_generation_agent.py` | Add `generate_extended_reading()` + 3 helpers | ~80 |
| `src/agents/resource_generation_agent.py` | Add to `RESOURCE_TYPES` dict | 1 |
| `src/agents/resource_generation_agent.py` | Add to `generate_all()` call | 1 |
| `web/v1/components.py` | Add `extended_reading` to multimodal card renderer | ~10 |

**Total: ~92 lines. One file modified (agent), one file extended (components).**

---

## 7. Test Impact

| Test File | Impact |
|:----------|:-------|
| Existing tests | ✅ No changes — new method doesn't affect existing ones |
| New test needed | ~15 lines verifying `generate_extended_reading()` output structure |

**Test strategy:** Add a simple output validation test. No integration test needed (resource generation is purely rule-based).

---

## 8. Competition Demo Value

| Judge Question | Answer |
|:---------------|:-------|
| "Where does the knowledge come from?" | "Curated knowledge base + curated external references." |
| "Is this just generating from the internet?" | "No. All references are pre-vetted and stored in resources.json." |
| "What about hallucinations in references?" | "References are curated, not LLM-generated. Zero hallucination risk." |

**Visual:** The extended reading card appears alongside the other 5 resource types, showing the system's breadth.
