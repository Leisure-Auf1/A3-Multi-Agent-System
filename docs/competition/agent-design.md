# Agent Design

## 12-Agent Multi-Agent System

A3 uses 12 specialized agents, each with a distinct role in the learning pipeline. Agents communicate through an EventBus and share state via a Memory Manager.

## Core Pipeline Agents (6)

### 1. ProfileAgent
**Role**: Extract 6-dimension student profile from natural language input.

| Dimension | Values | Extraction Method |
|:----------|:-------|:------------------|
| Knowledge Base | junior_dev, mid_level, senior | LLM + Rule fallback |
| Cognitive Style | visual_dominant, text_linear, auditory | Pattern matching |
| Error-Prone Bias | magic_syntax_blind, indentation, scoping | Rule engine |
| Learning Pace | fast_track, normal, deep_dive | Keyword analysis |
| Interaction Preference | code_sandbox, quiz_first, passive_read | Context inference |
| Frustration Threshold | low, medium, high | Sentiment analysis |

**Design**: LLM-primary with rule fallback. If LLM is unavailable, deterministic rules extract ~70% of profile dimensions from keywords.

### 2. PlannerAgent
**Role**: Generate personalized learning path from knowledge base + student profile.

**Input**: Student profile + learning goal + knowledge gaps
**Output**: Ordered list of learning nodes with:
- Title, core concept, depth (1-3)
- Estimated duration, exercise count
- Teaching strategy (visual/textual/hands-on)

**Knowledge Base**: Python curriculum with 20 chapters, keyword → graph_id mapping, multi-course support.

### 3. ResourceAgent
**Role**: Recommend learning resources matched to knowledge gaps and cognitive style.

**Resource Types**: documentation, video, exercise, article, project
**Matching Logic**: Gap analysis → type selection → difficulty calibration

### 4. EvaluationAgent
**Role**: Assess learning quality through quiz generation and scoring.

**Capabilities**:
- Auto-generate multiple-choice + open-ended quizzes
- Instant scoring with weak area detection
- Adaptive question difficulty based on profile

### 5. ReflectionAgent
**Role**: Post-execution analysis and continuous improvement.

**Functions**:
- Summarize pipeline execution quality
- Suggest improvements for future iterations
- Update student profile based on performance

### 6. ReviewAgent (ReviewGate)
**Role**: Quality gate for all agent outputs before reaching the student.

**Three-tier review**:
1. **AST static audit** — Syntax/structure validation
2. **Pytest execution** — Functional correctness
3. **Judge scoring** — Content quality assessment

## Extended Agents (6)

### TutorAgent
ChatGPT-style streaming tutoring via SSE. 5 teaching styles: explanation, Socratic, example-driven, analogy, step-by-step.

### ResourceGenerationAgent
Generates educational content across 7 modalities via the Multimodal Gateway.

### ResourceRecommendationAgent
Advanced resource matching with collaborative filtering and knowledge graph traversal.

### ConversationProfileAgent
Extracts student profile through multi-turn natural conversation.

### MetaReflectorAgent
Meta-level analysis of pipeline failures and anti-pattern detection for continuous system improvement.

### AgentRouter
Routes API requests to the appropriate agent based on content type and system state.

## Agent Communication

```
ProfileAgent ──▶ EventBus ──▶ PlannerAgent ──▶ EventBus ──▶ ResourceAgent
     │                                                            │
     │              TraceCollector ◀── all events                 │
     │                                                            │
     └────────── ReviewAgent ◀── ReflectionAgent ◀───────────────┘
```

Each agent emits events with:
- `agent`: Agent name
- `action`: What it did
- `status`: success/error
- `duration_ms`: Execution time
- `input_summary`: Compressed input
- `output_summary`: Compressed output

## LLM Integration

Agents receive `LLMProvider` via constructor injection:
```python
agent = ProfileAgent(llm_provider=provider)
```

The `LLMAgentAdapter` wraps agent methods with automatic LLM → Rule fallback:
```python
adapter = LLMAgentAdapter(provider=provider)
result = adapter.call(
    agent_name="ProfileAgent",
    prompt_template="Extract profile from: {text}",
    input_vars={"text": student_input},
    rule_fn=lambda: profile_agent.extract(text),
)
```

## Testing

Each agent has dedicated unit tests. Integration tests verify the full pipeline with mock providers. All 1154 tests pass on every commit.

| Test Category | Count | Coverage |
|:--------------|:------|:---------|
| Agent unit tests | 200+ | Profile, Planner, Resource, Evaluation, Reflection |
| Pipeline integration | 60+ | Full workflow with mock/rule providers |
| API integration | 120+ | Auth, chat, profile, learning, resources, evaluation |
| Runtime tests | 550+ | Veritas-Core engine, plugins, recovery, lifecycle |
