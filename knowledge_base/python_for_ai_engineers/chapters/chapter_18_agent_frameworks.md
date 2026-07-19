# Chapter 18: Agent Frameworks

> **Learning Objective**: Build AI agents that can reason, use tools, and complete tasks.

---

## 18.1 What is an AI Agent?

An AI agent is a system that:
- Perceives its environment (reads input, observes state)
- Reasons about what to do (plans, decides)
- Acts using tools (calls APIs, runs code, searches)
- Learns from results (adapts, improves)

```
User Goal → Agent thinks → Selects tool → Executes → Observes result → (loop)
```

---

## 18.2 LangChain Agents

```python
from langchain.agents import initialize_agent, Tool
from langchain.llms import OpenAI

tools = [
    Tool(name="Search", func=search_function,
         description="Search the web for information"),
    Tool(name="Calculator", func=calculator,
         description="Perform mathematical calculations"),
]

agent = initialize_agent(
    tools, llm, agent="zero-shot-react-description", verbose=True
)

agent.run("What is the population of Tokyo divided by 1000?")
```

---

## 18.3 CrewAI

Multi-agent collaboration framework:

```python
from crewai import Agent, Task, Crew

researcher = Agent(
    role="Researcher",
    goal="Find relevant information",
    backstory="Expert at finding and synthesizing information"
)

writer = Agent(
    role="Writer",
    goal="Create clear, engaging content",
    backstory="Skilled technical writer"
)

research_task = Task(description="Research topic X", agent=researcher)
writing_task = Task(description="Write report on topic X", agent=writer)

crew = Crew(agents=[researcher, writer], tasks=[research_task, writing_task])
result = crew.kickoff()
```

---

## 18.4 Agent Design Patterns

- **ReAct**: Reason (think) → Act (use tool) → Observe (get result) → repeat
- **Plan-and-Execute**: Plan all steps first, then execute
- **Multi-Agent**: Specialized agents collaborate on sub-tasks
- **Reflection**: Agent critiques its own output and improves

---

## 18.5 A3's Agent Architecture

A3 implements a custom 9-agent pipeline:
```
ProfileAgent → PlannerAgent → ResourceAgent → TutorAgent → EvaluationAgent → ReflectionAgent
```

Each agent is a focused module with clear inputs and outputs, orchestrated by A3Workflow.

---

## Practice Exercises

1. Build a simple agent with one tool (calculator). Have it solve math problems.

2. Create a two-agent CrewAI team: researcher + summarizer.

3. Implement a ReAct loop manually: think → act → observe → repeat.

4. Study A3's agent pipeline and trace a complete run.

---

## Key Takeaways

- Agents perceive, reason, act, and learn
- LangChain provides agent initialization with tools
- CrewAI enables multi-agent collaboration
- ReAct is the fundamental pattern for tool-using agents
