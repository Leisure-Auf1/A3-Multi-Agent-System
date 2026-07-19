# Chapter 20: Capstone Project — AI Learning Assistant

> **Learning Objective**: Apply all Python + AI skills to build a complete application.

---

## 20.1 Project Overview

Build a simple **AI-Powered Learning Assistant** that:
1. Takes a learning goal from the user
2. Analyzes the user's current knowledge level
3. Generates a personalized learning plan
4. Produces study materials
5. Quizzes the user
6. Tracks progress

---

## 20.2 Architecture

```
Streamlit UI (frontend)
    ↕ HTTP
FastAPI Backend
    ↕
Agent Pipeline: Profile → Plan → Resources → Quiz → Report
    ↕
SQLite Database (users, profiles, learning records)
```

---

## 20.3 Step-by-Step Implementation

### Step 1: User Input
```python
goal = input("What do you want to learn? ")
```

### Step 2: Profile Analysis
```python
from src.agents.profile_agent import ProfileAgent
agent = ProfileAgent()
result = agent.extract(goal)
profile = result.profile
```

### Step 3: Learning Plan
```python
from src.agents.planner_agent import PlannerAgent
planner = PlannerAgent()
plan = planner.plan(profile=profile.to_dict(), goal_text=goal)
```

### Step 4: Resource Recommendation
```python
from src.agents.resource_agent import ResourceAgent
resource_agent = ResourceAgent()
resources = resource_agent.recommend(
    profile=profile.to_dict(), goal=goal
)
```

### Step 5: Quiz Generation
```python
from src.agents.evaluation_agent import EvaluationAgent
eval_agent = EvaluationAgent()
quiz = eval_agent.generate_quiz(topic=goal, student_level="beginner")
```

### Step 6: Progress Tracking
```python
from src.data.learning_records import record_agent_action
record_agent_action(
    user_id="student_1", agent="tutor",
    action="learning_session", score=85.0
)
```

---

## 20.4 Extension Ideas

- Add LLM-powered TutorAgent for interactive Q&A
- Implement RAG for domain-specific knowledge
- Deploy as Docker container with Streamlit + FastAPI
- Package as Windows desktop app with Electron

---

## 20.5 Deliverables

1. Working application code (Python)
2. README with setup instructions
3. Demo video or screenshots
4. 5-minute presentation of your system

---

## Key Takeaways

- You now have the skills to build an AI learning system from scratch
- The A3-Multi-Agent-System codebase is your reference implementation
- Start simple: one agent at a time, test thoroughly, then add complexity
- The best way to learn AI engineering is to build AI systems
