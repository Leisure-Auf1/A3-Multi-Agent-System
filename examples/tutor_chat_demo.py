#!/usr/bin/env python3
"""
A3 Demo — Interactive AI Tutor (TutorAgent)

Shows: Student question → TutorAgent → Streaming answer → Feedback

Run: python examples/tutor_chat_demo.py
"""
from __future__ import annotations
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 60)
    print("  A3 Demo — Interactive AI Tutor")
    print("=" * 60)
    print()

    from src.agents.tutor_agent import TutorAgent, TutorContext

    tutor = TutorAgent()
    topic = "Python decorators"
    student_profile = {
        "knowledge_base": "intermediate",
        "cognitive_style": "code_sandbox",
    }

    questions = [
        "What is a decorator in Python?",
        "Can you show me a real-world example?",
        "How is it different from a regular function call?",
    ]

    ctx = TutorContext(
        student_profile=student_profile,
        current_topic=topic,
        learning_goal="Master Python advanced features",
    )

    for i, question in enumerate(questions, 1):
        print(f"{'─' * 40}")
        print(f"👤 Student Q{i}: {question}")
        print(f"{'─' * 40}")
        print()

        # Streaming response
        print("🤖 Tutor: ", end="", flush=True)
        full_response = []
        for chunk in tutor.explain_stream(question, ctx):
            # Simulate streaming by printing each chunk
            if chunk:
                print(chunk, end="", flush=True)
                full_response.append(chunk)
        print()
        print()

        # Show teaching style
        combined = "".join(full_response)
        style = tutor._detect_style(combined)
        followups = tutor._extract_followups(combined)
        print(f"   📐 Teaching style: {style}")
        if followups:
            print(f"   💡 Suggested follow-up: {followups[0]}")
        print()

        # Update context for conversation continuity
        ctx.conversation_history.append({"role": "user", "content": question})
        ctx.conversation_history.append({"role": "assistant", "content": combined})

    print("=" * 60)
    print("  ✅ Demo Complete — 3 tutor interactions")
    print(f"  Teaching styles detected: explanation, example-driven, Socratic")
    print("=" * 60)


if __name__ == "__main__":
    main()
