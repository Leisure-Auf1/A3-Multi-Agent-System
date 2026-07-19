# Chapter 16: Prompt Engineering

> **Learning Objective**: Craft effective prompts to control LLM behavior.

---

## 16.1 Prompt Structure

A good prompt has:
- **Role/Persona**: "You are an expert Python tutor."
- **Context**: Background information the model needs
- **Task**: Clear, specific instruction
- **Format**: Desired output format (JSON, markdown, etc.)
- **Constraints**: Length limits, style guidance, don'ts

---

## 16.2 Core Techniques

### Zero-Shot
Just ask directly:
```
Translate to French: "Hello, how are you?"
```

### Few-Shot
Provide examples:
```
English: Hello → French: Bonjour
English: Goodbye → French: Au revoir
English: Thank you → French:
```

### Chain-of-Thought (CoT)
Ask the model to reason step by step:
```
Q: If a shirt costs $25 after a 20% discount, what was the original price?
Let's think step by step:
```

---

## 16.3 Advanced Techniques

### Structured Output
```
Return a JSON object with fields: name (string), age (number), skills (array).
User: I'm Alice, 28 years old, know Python and JavaScript.
```

### Self-Consistency
Run the same prompt multiple times and take the majority answer:
```
Solve this math problem. Think step by step. [Problem]
--- (run 3-5 times, pick most common answer)
```

### ReAct (Reasoning + Acting)
Interleave reasoning with tool calls:
```
Thought: I need to look up the weather.
Action: search_weather("New York")
Observation: 72F, sunny
Thought: Now I can answer the user's question.
```

---

## 16.4 Common Pitfalls

- **Too vague**: "Write something about AI" → gets generic output
- **Conflicting instructions**: "Be concise. Include all details."
- **Prompt injection**: User input overrides system instructions
- **Hallucination**: Model invents facts; use RAG to ground responses

---

## Practice Exercises

1. Write a zero-shot prompt for a Python code reviewer. Test it.

2. Create a few-shot prompt for sentiment analysis with 3 examples.

3. Use chain-of-thought prompting to solve a multi-step math problem.

4. Design a prompt that outputs a structured JSON response.

---

## Key Takeaways

- Good prompts have role, context, task, format, constraints
- Few-shot examples dramatically improve output quality
- Chain-of-thought enables complex reasoning
- Structured output prompts guide the format
