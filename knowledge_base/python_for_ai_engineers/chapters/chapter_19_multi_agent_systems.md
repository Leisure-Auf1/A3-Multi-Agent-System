# Chapter 19: Multi-Agent Systems

> **Learning Objective**: Design systems where multiple AI agents collaborate.

---

## 19.1 Why Multi-Agent?

Single-agent limitations:
- One model, one perspective
- Can't parallelize sub-tasks
- No specialization

Multi-agent benefits:
- **Specialization**: Each agent focuses on its strength
- **Parallelism**: Multiple agents work simultaneously
- **Robustness**: Failure of one agent doesn't crash the system
- **Emergence**: Complex behavior from simple agent interactions

---

## 19.2 Communication Patterns

### Sequential Pipeline
```
Agent A → Agent B → Agent C → Output
```
A3 Workflow: ProfileAgent → PlannerAgent → ResourceAgent → ...

### Debate/Discussion
```
Agent A: "Answer is X because..."
Agent B: "Disagree, answer is Y because..."
Agent A: "Good point, revising to Z..."
```

### Hierarchical
```
Orchestrator → assigns tasks → Worker Agents → report back → Orchestrator
```

---

## 19.3 Agent Roles

Common role patterns:
- **Planner**: Breaks down goals into sub-tasks
- **Executor**: Performs specific actions
- **Critic/Evaluator**: Reviews and scores outputs
- **Coordinator**: Manages agent communication
- **Memory**: Stores and retrieves context

---

## 19.4 A3's Multi-Agent Design

A3's 9-agent system demonstrates:
1. **ProfileAgent**: Understands the student
2. **PlannerAgent**: Creates learning path
3. **ResourceAgent**: Recommends materials
4. **ResourceGenerationAgent**: Creates content
5. **TutorAgent**: Interacts with student
6. **EvaluationAgent**: Assesses understanding
7. **ReflectionAgent**: Analyzes learning outcomes
8. **ConversationProfileAgent**: Updates profile from chat
9. **ResourceRecommendationAgent**: Precision recommendations

---

## 19.5 Challenges

- **Coordination overhead**: More agents = more complexity
- **Consistency**: Agents may produce conflicting outputs
- **Latency**: Sequential pipelines add up
- **Cost**: Each agent may call an LLM

---

## Practice Exercises

1. Design a 3-agent system for code review: Analyzer → Reviewer → Suggester.

2. Implement a simple debate between two agents on a topic.

3. Study A3Workflow and trace how agents communicate via EventBus.

4. Add a new agent to the A3 pipeline (e.g., MotivationAgent).

---

## Key Takeaways

- Multi-agent = specialization + parallelism + robustness
- Patterns: sequential, debate, hierarchical
- Roles: planner, executor, critic, coordinator, memory
- A3's 9-agent pipeline is a battle-tested example
