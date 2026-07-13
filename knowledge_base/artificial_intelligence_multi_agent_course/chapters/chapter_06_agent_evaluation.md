# Chapter 6: Agent Evaluation

> **Learning Objective**: Build systematic evaluation frameworks for AI agents using quantitative metrics, qualitative assessment, and continuous improvement loops.

---

## 6.1 Why Evaluate Agents?

Without evaluation, you're flying blind:

- **No Quality Control**: How do you know if agents are improving?
- **No Regression Detection**: Did a change break something?
- **No Comparative Baseline**: Is multi-agent better than single-agent?
- **No Stakeholder Trust**: Can users/judges trust the system?

> "If you can't measure it, you can't improve it." — Peter Drucker

---

## 6.2 Evaluation Dimensions

### The 4-Dimension Framework

A3 evaluates agents across four dimensions with weighted scoring:

| Dimension | Weight | What It Measures | Example |
|:----------|:-------|:-----------------|:--------|
| **Correctness** | 0.35 | Is the output factually correct? | Profile: correct dimension values |
| **Personalization** | 0.30 | Is output tailored to the student? | Plan: different paths for different profiles |
| **Explainability** | 0.20 | Can decisions be understood? | Recommendation: reason for each resource |
| **Efficiency** | 0.15 | Time and resource usage | Response time, memory consumption |

### Scoring Formula

```
Overall Score = 0.35 × Correctness
              + 0.30 × Personalization
              + 0.20 × Explainability
              + 0.15 × Efficiency
```

---

## 6.3 Evaluation Methods

### Rule-Based Evaluation (RuleJudge)

Deterministic, reproducible, no LLM dependency.

```python
class RuleJudge:
    def evaluate_profile_extraction(self, profile, student_text):
        score = 0.0
        # Check: are all 6 dimensions present?
        if all(dim in profile for dim in PROFILE_DIMENSIONS):
            score += 0.5
        # Check: are dimension values valid?
        if all(is_valid_value(v) for v in profile.values()):
            score += 0.3
        # Check: is extraction source-justified?
        if profile.get("source") in ("rule", "llm", "rule+memory"):
            score += 0.2
        return score
```

**Pros**: Fast, consistent, no API cost
**Cons**: Can't evaluate semantic quality, limited to structured checks

### LLM-Based Evaluation (LLMJudge)

Uses another LLM to assess output quality.

```python
class LLMJudge:
    def evaluate(self, agent_output: str, context: str) -> JudgeResult:
        prompt = f"""
        Rate this agent output on 4 dimensions (0.0-1.0):
        
        Context: {context}
        Output: {agent_output}
        
        Dimensions:
        1. Correctness: is it factually accurate?
        2. Personalization: is it tailored?
        3. Explainability: are decisions clear?
        4. Efficiency: is it concise?
        
        Return JSON: {{"correctness": X, "personalization": X, ...}}
        """
        return self.llm.generate(prompt)
```

**Pros**: Evaluates semantic quality, catches subtle issues
**Cons**: Expensive, non-deterministic, potential bias

### Human Evaluation

The gold standard — but slow and expensive. Use for:
- Calibrating automated metrics
- Evaluating subjective qualities (tone, engagement)
- Final QA before release

---

## 6.4 The Improvement Loop

### Continuous Improvement Cycle

```
┌──────────────────────────────────────────────┐
│                                              │
│   Agent Run → Evaluate → Low Score?          │
│       ▲                      │               │
│       │                      ▼               │
│       │              MetaReflector            │
│       │              (Root Cause)             │
│       │                      │               │
│       │                      ▼               │
│       └──── Strategy Update ← Experience     │
│                                              │
└──────────────────────────────────────────────┘
```

### A3 ImprovementLoop

```python
class ImprovementLoop:
    def run_cycle(self, agent_results, node_id, student_id):
        for agent_name, result in agent_results.items():
            if result.overall_score < 0.5:  # Below threshold
                # 1. Diagnose root cause
                reflection = self.reflector.reflect(
                    node_id=node_id,
                    failure_context={"problem": result.reason},
                    concept=node_id,
                    attempts=1
                )
                # 2. Store lesson for future
                self.experience_memory.store(reflection.to_experience_entry())
                # 3. Generate improvement suggestion
                suggestion = self._generate_suggestion(agent_name, result, reflection)
                self.suggestions.append(suggestion)
```

---

## 6.5 Benchmark Datasets

### A3 Benchmark

20 simulated students across 4 categories:

| Category | Count | Profile Characteristics |
|:---------|:------|:-----------------------|
| **Beginner** | 8 | junior_dev, visual_dominant, slow pace |
| **Intermediate** | 6 | mid_level, code_sandbox, normal pace |
| **Advanced** | 4 | senior, fast_track, deep_dive |
| **Edge Cases** | 2 | Ambiguous input, contradictory preferences |

### Running Evaluation

```bash
python -m src.evaluation.evaluator datasets/students/benchmark.json
```

Output: `EvaluationReport` with:
- Profile extraction accuracy per student
- Plan quality (node relevance, path coherence)
- Recommendation relevance (resource appropriateness)
- Aggregate scores with confidence intervals

---

## 6.6 User Simulation

### How UserSim Works

`UserSimulationAgent` simulates a student with a specific cognitive profile:

1. **Read Content**: Parse generated teaching material
2. **Apply Profile**: Filter through profile's learning style
3. **Detect Issues**: Concept overload, missing prerequisites, confusing explanations
4. **Score Output**: 0-100 quality score
5. **Generate Diary**: First-person learning experience narrative

### UserSim Scoring Dimensions

| Dimension | Weight | Checks |
|:----------|:-------|:-------|
| Concept Load | 25% | ≤4 new concepts per section |
| Prerequisites | 25% | All dependencies explained |
| Style Match | 20% | Teaching style matches profile |
| Code Quality | 15% | Examples runnable, syntax correct |
| Engagement | 15% | Interactive elements, pacing |

---

## 6.7 Multi-Gate Review

### A3 ReviewGate: 3-Layer Defense

```
ContentAgent Output
        │
        ▼
┌──────────────────┐
│ Gate 1: AST      │  Static code analysis
│ • Syntax check   │  • Python AST parsing
│ • Imports valid  │  • Function signatures
│ • Type hints     │  • ≥50% annotated
└────────┬─────────┘
         ▼
┌──────────────────┐
│ Gate 2: Pytest   │  Dynamic validation
│ • Code runs      │  • Exercise solutions work
│ • Expected output│  • Edge cases handled
└────────┬─────────┘
         ▼
┌──────────────────┐
│ Gate 3: Judge    │  Semantic evaluation
│ • Concept depth  │  • Appropriate for level
│ • Style matching │  • Profile alignment
│ • Anti-patterns  │  • 400+ word paragraphs
└────────┬─────────┘
         │
    All gates pass?
    YES → Commit
    NO  → HotFix → Re-evaluate
```

---

## Chapter 6 Exercises

1. Design an evaluation rubric for a code-generation agent. Include 5 dimensions with weights.
2. Implement a minimal rule-based evaluator for a QA bot (check: answer not empty, answer contains keywords, answer < 500 chars)
3. Compare RuleJudge vs LLMJudge: run both on 5 sample outputs and analyze discrepancies
4. Create a benchmark of 10 test cases for a summarization agent

---

## Key Terms

- **Evaluation Framework** · **RuleJudge** · **LLMJudge**
- **4-Dimension Scoring** · **Benchmark Dataset** · **UserSim**
- **Improvement Loop** · **ReviewGate** · **Confidence Score**
- **Quantitative Metrics** · **Qualitative Assessment** · **Regression Testing**

---

## Code Lab: Minimal Evaluator

```python
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class EvaluationResult:
    correctness: float
    personalization: float
    explainability: float
    efficiency: float

    @property
    def overall(self) -> float:
        return (0.35 * self.correctness
              + 0.30 * self.personalization
              + 0.20 * self.explainability
              + 0.15 * self.efficiency)

class SimpleEvaluator:
    def evaluate_profile(self, profile: Dict) -> EvaluationResult:
        dims = ["knowledge_base", "cognitive_style", "error_prone_bias",
                "learning_pace", "interaction_preference", "frustration_threshold"]

        # Correctness: are all 6 dimensions present and valid?
        correctness = sum(1 for d in dims if d in profile and profile[d]) / 6.0

        # Personalization: are values non-default?
        defaults = {"knowledge_base": "junior_dev", "cognitive_style": "visual_dominant"}
        non_default = sum(1 for k, v in profile.items()
                         if k not in defaults or v != defaults[k])
        personalization = min(non_default / len(profile), 1.0)

        # Explainability: does profile include a source field?
        explainability = 1.0 if "source" in profile else 0.3

        # Efficiency: response time (simulated)
        efficiency = 0.8  # Baseline

        return EvaluationResult(correctness, personalization, explainability, efficiency)

# Demo
evaluator = SimpleEvaluator()
result = evaluator.evaluate_profile({
    "knowledge_base": "mid_level",
    "cognitive_style": "visual_dominant",
    "error_prone_bias": "magic_syntax_blind",
    "learning_pace": "fast_track",
    "interaction_preference": "code_sandbox",
    "frustration_threshold": "low",
    "source": "rule"
})
print(f"Overall Score: {result.overall:.2f}")
```

---

## Further Reading

- Ribeiro et al., "Beyond Accuracy: Behavioral Testing of NLP Models with CheckList" (2020)
- Liang et al., "Holistic Evaluation of Language Models" (HELM, 2023)
- Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (2023)
- Chen et al., "Evaluating Large Language Models Trained on Code" (HumanEval, 2021)
