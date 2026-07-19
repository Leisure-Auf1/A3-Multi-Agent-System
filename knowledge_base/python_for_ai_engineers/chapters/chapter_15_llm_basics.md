# Chapter 15: Large Language Models Basics

> **Learning Objective**: Understand how LLMs work and how to use them.

---

## 15.1 What are LLMs?

Large Language Models are neural networks (typically Transformers) trained on massive text corpora to predict the next token. They exhibit emergent capabilities:
- Text generation and completion
- Translation and summarization
- Code generation
- Question answering
- Reasoning (chain-of-thought)

---

## 15.2 The Transformer Architecture

Key components:
- **Self-Attention**: Each token attends to all other tokens
- **Multi-Head Attention**: Multiple attention patterns in parallel
- **Position Encoding**: Injects sequence order information
- **Feed-Forward Networks**: Per-token processing

Key innovation: All tokens processed in parallel (unlike RNNs which process sequentially).

---

## 15.3 Training Paradigms

```
Pre-training → Supervised Fine-Tuning (SFT) → RLHF/DPO
```

- **Pre-training**: Next-token prediction on massive corpora
- **SFT**: Fine-tune on instruction-response pairs
- **RLHF**: Reinforcement Learning from Human Feedback — align outputs with human preferences
- **DPO**: Direct Preference Optimization — simpler alternative to RLHF

---

## 15.4 Using LLM APIs

```python
from openai import OpenAI

client = OpenAI(api_key="sk-...")

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain neural networks in simple terms."}
    ]
)

print(response.choices[0].message.content)
```

---

## 15.5 Key Concepts

- **Token**: Unit of text (word, subword, character)
- **Context window**: Maximum input length (4K-200K+ tokens)
- **Temperature**: Controls randomness (0=deterministic, 1=creative)
- **Hallucination**: Model generates plausible but incorrect information

---

## Practice Exercises

1. Set up an LLM API client and send a simple completion request.

2. Experiment with different temperature values (0, 0.5, 1.0).

3. Use system prompts to control the model's behavior and tone.

4. Compare responses from two different models on the same prompt.

---

## Key Takeaways

- LLMs are Transformer-based models trained on massive text corpora
- Self-attention enables parallel processing of all tokens
- Training: pre-train → SFT → alignment (RLHF/DPO)
- API access via chat completions with messages array
