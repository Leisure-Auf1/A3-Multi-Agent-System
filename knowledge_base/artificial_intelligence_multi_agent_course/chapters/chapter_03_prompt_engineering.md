# Chapter 3: Prompt Engineering

> **Learning Objective**: Master the art and science of crafting effective prompts for Large Language Models.

---

## 3.1 What is Prompt Engineering?

Prompt Engineering is the practice of designing and optimizing input text (prompts) to elicit desired outputs from language models. It bridges the gap between human intent and model behavior.

### Why It Matters

- **No Fine-tuning Required**: Achieve specialized behavior without training
- **Cost Effective**: Prompt optimization vs. model training ($0 vs. $100K+)
- **Rapid Iteration**: Test and refine prompts in minutes
- **Model Agnostic**: Good prompts work across different LLMs

---

## 3.2 Fundamental Techniques

### Zero-Shot Prompting
Ask the model directly without examples.

```
✗ Bad: "Tell me about databases."
✓ Good: "Explain SQL databases to a beginner. Include: (1) what they are,
         (2) why they differ from spreadsheets, (3) a simple SELECT example.
         Use analogies appropriate for a non-technical audience."
```

### Few-Shot Prompting
Provide 2-5 examples to establish the pattern.

```
Classify sentiment as Positive, Negative, or Neutral:

Text: "The product arrived broken." → Negative
Text: "Fast shipping, works great!" → Positive
Text: "It's a blue shirt." → Neutral
Text: "Waste of money, don't buy." → [Model completes: Negative]
```

### Chain-of-Thought (CoT)
Prompt the model to show its reasoning steps.

```
Problem: Roger has 5 tennis balls. He buys 2 more cans, each with 3 balls.
How many balls does he have now?

Let's think step by step:
1. Roger starts with 5 balls
2. He buys 2 cans × 3 balls each = 6 new balls
3. Total = 5 + 6 = 11 balls
Answer: 11

Problem: A store has 120 apples in 8 boxes. If 3 boxes are sold,
how many apples remain? Let's think step by step:
```

---

## 3.3 Advanced Techniques

### Role Prompting
Assign the model a persona to guide its behavior.

```
You are a senior Python developer conducting a code review.
Focus on: security vulnerabilities, performance bottlenecks,
and PEP 8 compliance. Be specific and suggest concrete fixes.
```

### Structured Output Prompting
Request specific output formats.

```
Generate a JSON object with the following schema:
{
  "topic": "string",
  "difficulty": "beginner|intermediate|advanced",
  "key_points": ["string"],
  "code_example": "string",
  "common_mistakes": ["string"]
}

Topic: Python list comprehensions
```

### Self-Consistency
Run the same prompt multiple times and take the majority answer.

```
# Run 5 times with temperature=0.7
Q: If a train travels at 60 mph for 2.5 hours, how far does it go?
→ Run 1: 150 miles ✓
→ Run 2: 150 miles ✓
→ Run 3: 140 miles ✗
→ Run 4: 150 miles ✓
→ Run 5: 150 miles ✓

Majority: 150 miles ✓
```

### Tree-of-Thought (ToT)
Explore multiple reasoning paths simultaneously.

```
Problem: Find the shortest path from A to F.

Step 1: From A, possible next: B, C, D
  Path A→B: cost 5, remaining estimate 10 → total 15
  Path A→C: cost 3, remaining estimate 8  → total 11 ← best
  Path A→D: cost 7, remaining estimate 12 → total 19

Step 2: From C, evaluate possibilities...
```

---

## 3.4 Prompt Design Principles

### The CRISP Framework

| Element | Purpose | Example |
|:--------|:--------|:--------|
| **C**ontext | Set the scene | "You are a math tutor..." |
| **R**ole | Define persona | "...helping a 10th grader..." |
| **I**nstruction | Specify the task | "...solve quadratic equations..." |
| **S**tyle | Output format | "...step-by-step with explanations..." |
| **P**arameters | Constraints | "...max 200 words, no formulas." |

### Common Pitfalls

| Pitfall | Example | Fix |
|:--------|:--------|:----|
| **Vague instructions** | "Write about AI" | "Explain transformer attention in 3 paragraphs with a code example" |
| **Over-constraining** | 10+ specific requirements | Prioritize top 3 requirements |
| **Missing context** | "Fix this code" (paste code only) | Add: language, expected behavior, error message |
| **Leading questions** | "Why is X better than Y?" | "Compare X and Y on: speed, cost, accuracy" |

---

## 3.5 System Prompts

System prompts set the model's behavior at the conversation level (not per-message).

### Effective System Prompt Pattern

```
You are [ROLE]. Your task is [TASK].

Rules:
1. [Constraint 1]
2. [Constraint 2]
3. [Constraint 3]

Format: [Output format specification]

Example interaction:
User: [Sample question]
Assistant: [Sample answer demonstrating desired behavior]
```

### A3 Example: ContentAgent System Prompt

```
You are an AI teaching assistant specializing in [TOPIC].

Rules:
1. Every concept must have a concrete code example
2. Use visual comparisons: ❌ wrong vs ✅ right
3. No paragraph longer than 200 words without a code block
4. Include a Mermaid diagram for complex relationships

Student Profile:
- Visual learner: use ASCII art for structures
- Fast pace: skip basic definitions, focus on insights
- Code-first: show the code, then explain it
```

---

## Chapter 3 Exercises

1. Write 3 versions of a prompt for "explain recursion" — zero-shot, few-shot, and CoT
2. Design a few-shot prompt that extracts {name, date, location} from event descriptions
3. Create a system prompt for a code review assistant
4. Debug: given a poorly-performing prompt, identify issues and rewrite

---

## Key Terms

- **Prompt Engineering** · **Zero-Shot** · **Few-Shot**
- **Chain-of-Thought (CoT)** · **Self-Consistency** · **Tree-of-Thought (ToT)**
- **System Prompt** · **Role Prompting** · **Structured Output**
- **CRISP Framework** · **Prompt Injection** · **Token Limit**

---

## Further Reading

- Wei et al., "Chain-of-Thought Prompting Elicits Reasoning in LLMs" (2022)
- Wang et al., "Self-Consistency Improves Chain-of-Thought Reasoning" (2023)
- Yao et al., "Tree of Thoughts: Deliberate Problem Solving with LLMs" (2023)
- OpenAI, "Prompt Engineering Guide" (2024)
