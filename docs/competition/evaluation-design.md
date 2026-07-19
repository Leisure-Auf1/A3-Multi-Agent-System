# Evaluation Design

## ReviewGate — 3-Tier Quality Assurance

Every agent output passes through ReviewGate before reaching the student. This ensures correctness, personalization, and safety.

```
┌──────────────────────────────────────────────────────┐
│                  ReviewGate Pipeline                  │
│                                                      │
│  Agent Output                                        │
│       │                                              │
│       ▼                                              │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐   │
│  │ Gate 1   │───▶│ Gate 2   │───▶│ Gate 3       │   │
│  │ AST      │    │ Pytest   │    │ Judge        │   │
│  │ Static   │    │ Execution│    │ Scoring      │   │
│  │ Audit    │    │          │    │              │   │
│  └──────────┘    └──────────┘    └──────────────┘   │
│       │              │               │               │
│       ▼              ▼               ▼               │
│  Syntax check    Functional     Quality score        │
│  Structure       correctness    (4 dimensions)       │
└──────────────────────────────────────────────────────┘
```

### Gate 1: AST Static Audit
- Validates Python syntax
- Checks structural integrity
- Detects anti-patterns (unclosed brackets, missing imports)

### Gate 2: Pytest Execution
- Runs generated test cases against agent output
- Verifies functional correctness
- Catches runtime errors before they reach the student

### Gate 3: Judge Scoring
4-dimensional quality assessment:

| Dimension | Weight | Description |
|:----------|:-------|:------------|
| Correctness | 35% | Factual accuracy of content |
| Personalization | 30% | Match to student profile |
| Explainability | 20% | Clarity of reasoning chain |
| Efficiency | 15% | Resource appropriateness |

**Scoring**: Each dimension scored 0.0–1.0, weighted sum produces final score (0–100).
**Pass Threshold**: ≥ 70/100

## EvaluationAgent

The EvaluationAgent provides student-facing assessment:

### Quiz Generation
```python
POST /api/v2/evaluation/quiz/generate
→ {
    "questions": [
        {"type": "multiple_choice", "question": "...", "options": [...], "answer": 2},
        {"type": "open_ended", "question": "...", "expected_keywords": [...]}
    ]
}
```

### Quiz Scoring
```python
POST /api/v2/evaluation/quiz/score
→ {
    "score": 85,
    "correct": 4, "total": 5,
    "weak_areas": ["variable_scoping"],
    "recommendations": ["Review Chapter 3: Variable Scoping"]
}
```

### Open Assessment
```python
POST /api/v2/evaluation/open/assess
→ {
    "score": 78,
    "feedback": "Good understanding of concepts, needs more practice with...",
    "suggestions": ["Try exercise 3.2", "Review decorator pattern"]
}
```

## Explainability Chain

Every evaluation includes a traceable reasoning chain:

```
Input: Student answer
   │
   ▼
Rule-based keyword extraction ──▶ Matched: "decorator", "closure", "@"
   │
   ▼
LLM semantic analysis ──▶ Score: 0.85 understanding
   │
   ▼
Profile-aware difficulty calibration ──▶ Adjusted for mid_level
   │
   ▼
Output: Score + Feedback + Recommendations
```

## Confidence Metrics

| Metric | Mock Mode | LLM Mode |
|:-------|:----------|:---------|
| Profile confidence | 0.70 (rule) | 0.88 (LLM) |
| Plan quality | 0.75 | 0.85 |
| Resource relevance | 0.80 | 0.90 |
| Quiz accuracy | 0.85 | 0.92 |
| Overall trust score | 0.78 | 0.89 |

Confidence is calculated as the weighted average of dimension scores from ReviewGate, adjusted by the provider's known reliability characteristics. Mock mode has lower confidence because it uses deterministic rules rather than semantic understanding.
