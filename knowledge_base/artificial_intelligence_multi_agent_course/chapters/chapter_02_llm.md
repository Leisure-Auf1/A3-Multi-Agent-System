# Chapter 2: Large Language Models

> **Learning Objective**: Understand the architecture, training, and capabilities of Large Language Models (LLMs).

---

## 2.1 What are Large Language Models?

Large Language Models are neural networks trained on massive text corpora to predict the next token in a sequence. Through this simple objective, they learn:

- **Syntax**: Grammatical structures and language rules
- **Semantics**: Word meanings and relationships
- **World Knowledge**: Facts, concepts, and common sense
- **Reasoning Patterns**: Logical deduction, analogies, problem-solving

### Scale Matters

| Model Size | Parameters | Training Data | Emergent Abilities |
|:-----------|:-----------|:--------------|:-------------------|
| Small (<1B) | Millions | GBs | Basic completion |
| Medium (1-10B) | Billions | 100s GBs | Translation, summarization |
| Large (10-100B) | Tens of billions | TBs | Reasoning, code generation |
| Massive (>100B) | Hundreds of billions | 10s TBs | Multi-step reasoning, tool use |

---

## 2.2 LLM Architecture

### The Transformer Decoder

Most modern LLMs (GPT, Llama, Claude) use a decoder-only Transformer:

```
Input: "The cat sat on the"

1. Tokenization: ["The", "cat", "sat", "on", "the"]
2. Embedding: Each token → dense vector (e.g., 4096 dimensions)
3. Positional Encoding: Add position information
4. Self-Attention: Each token attends to all previous tokens
5. Feed-Forward: Non-linear transformation per token
6. Output: Probability distribution over vocabulary for next token
```

### Key Components

| Component | Function | Formula (Simplified) |
|:----------|:---------|:---------------------|
| **Multi-Head Attention** | Parallel attention heads capture different relationships | `Attention(Q,K,V) = softmax(QK^T/√d)V` |
| **Layer Normalization** | Stabilize training by normalizing activations | `LayerNorm(x) = γ(x-μ)/σ + β` |
| **Residual Connections** | Enable deep networks by adding input to output | `Output = Layer(x) + x` |
| **Feed-Forward Network** | Per-position non-linear transformation | `FFN(x) = W₂·ReLU(W₁·x)` |

---

## 2.3 Training Paradigms

### Pre-training
- **Objective**: Next Token Prediction (causal language modeling)
- **Data**: Web crawls (Common Crawl), books, code repositories, Wikipedia
- **Hardware**: Thousands of GPUs/TPUs, weeks to months
- **Cost**: $1M-$100M+ for frontier models

### Fine-tuning
- **Supervised Fine-Tuning (SFT)**: Train on human-written prompt-response pairs
- **RLHF (Reinforcement Learning from Human Feedback)**:
  1. Collect human preference data (Response A > Response B)
  2. Train a Reward Model to predict human preferences
  3. Fine-tune LLM with PPO to maximize reward

### Instruction Tuning
- Train model to follow natural language instructions
- Key technique behind ChatGPT-like conversational ability
- Requires diverse instruction dataset (e.g., FLAN, Super-NaturalInstructions)

---

## 2.4 LLM Capabilities and Limitations

### Capabilities

| Capability | Description | Example |
|:-----------|:------------|:--------|
| Text Generation | Creative writing, summarization | Essays, stories, reports |
| Code Generation | Programming in multiple languages | Python, JavaScript, SQL |
| Translation | Cross-lingual understanding | EN↔ZH, multilingual support |
| Reasoning | Multi-step logical deduction | Math problems, puzzles |
| Analysis | Data interpretation, sentiment | Report analysis, trend detection |

### Limitations

| Limitation | Cause | Mitigation |
|:-----------|:------|:-----------|
| **Hallucination** | Statistical prediction, not knowledge | RAG, source grounding |
| **Context Window** | Fixed maximum token length | Chunking, external memory |
| **Knowledge Cutoff** | Training data timestamp | RAG with current data |
| **Reasoning Errors** | Pattern matching not logic | Chain-of-thought, verification |
| **Bias** | Training data reflects societal biases | Alignment, content filtering |

---

## 2.5 Major LLM Families

### OpenAI GPT Series
- **GPT-3** (2020): 175B parameters, first demonstration of in-context learning at scale
- **GPT-4** (2023): Multi-modal, improved reasoning, longer context (128K tokens)
- **o1** (2024): Reasoning-focused, chain-of-thought internally

### Anthropic Claude
- **Claude 3.5 Sonnet** (2024): Strong coding, 200K context, constitutional AI alignment
- Focus on safety and helpfulness through constitutional training

### Open-Source Models
- **Llama 3** (Meta): 8B/70B/405B, open weights, strong multilingual
- **Qwen 2.5** (Alibaba): Strong Chinese performance, 0.5B-72B
- **DeepSeek-V3** (DeepSeek): Mixture-of-Experts, efficient inference

### Chinese LLMs
- **讯飞星火 Spark**: Education-focused, strong Chinese, multi-modal
- **文心一言 ERNIE**: Baidu's foundation model, knowledge-enhanced
- **通义千问 Qwen**: Alibaba, open-source, strong benchmarks

---

## Chapter 2 Exercises

1. Calculate the number of attention operations for a sequence of length 2048 with hidden dimension 4096
2. Explain why RLHF improves instruction following compared to SFT alone
3. Research: Compare the context window sizes of 3 major LLMs and explain the trade-offs
4. Implement a minimal attention mechanism in Python (30 lines)

---

## Key Terms

- **LLM (Large Language Model)** · **Transformer** · **Self-Attention**
- **Tokenization** · **Embedding** · **Pre-training**
- **Fine-tuning** · **RLHF** · **Instruction Tuning**
- **Hallucination** · **Context Window** · **Emergent Ability**

---

## Code Lab: Minimal Attention

```python
import numpy as np

def scaled_dot_product_attention(Q, K, V, mask=None):
    """Compute attention: softmax(QK^T / sqrt(d_k)) * V"""
    d_k = Q.shape[-1]
    scores = np.dot(Q, K.T) / np.sqrt(d_k)
    if mask is not None:
        scores = scores + mask
    attention_weights = np.exp(scores) / np.sum(np.exp(scores), axis=-1, keepdims=True)
    return np.dot(attention_weights, V), attention_weights

# Example: 4 tokens, 3-dim embeddings
Q = K = V = np.random.randn(4, 3)
output, weights = scaled_dot_product_attention(Q, K, V)
print(f"Attention output shape: {output.shape}")
print(f"Attention weights:\n{weights}")
```

---

## Further Reading

- Vaswani et al., "Attention Is All You Need" (2017)
- Brown et al., "Language Models are Few-Shot Learners" (GPT-3, 2020)
- Ouyang et al., "Training language models to follow instructions" (InstructGPT, 2022)
- Touvron et al., "Llama 2: Open Foundation and Fine-Tuned Chat Models" (2023)
