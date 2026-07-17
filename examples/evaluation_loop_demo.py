#!/usr/bin/env python3
"""
A3 Demo — Evaluation Loop

Shows: Quiz generation → Student answers → Scoring → Weakness detection → Recommendations

Run: python examples/evaluation_loop_demo.py
"""
from __future__ import annotations
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 60)
    print("  A3 Demo — Evaluation Loop")
    print("=" * 60)
    print()

    from src.agents.evaluation_agent import (
        EvaluationAgent, QuizQuestion, StudentAnswer,
    )

    agent = EvaluationAgent()
    topic = "Python OOP"
    level = "beginner"

    # ═══════════════════════════════════════════════════════
    # Step 1: Generate quiz
    # ═══════════════════════════════════════════════════════
    print("─" * 40)
    print("✏️  Generating quiz...")
    print()

    quiz = agent.generate_quiz(topic, level, num_questions=5)

    print(f"📋 Quiz: {topic} ({level})")
    print(f"   Questions: {len(quiz)}")
    print()

    for q in quiz:
        print(f"   Q{q.id}: {q.question}")
        print(f"      Difficulty: {q.difficulty}")
        print()

    # ═══════════════════════════════════════════════════════
    # Step 2: Simulate student answers
    # ═══════════════════════════════════════════════════════
    print("─" * 40)
    print("👤 Student answers...")
    print()

    # Simulate: correct on 1,3,5; wrong on 2,4
    answers = []
    for i, q in enumerate(quiz):
        correct = q.correct_index
        # Get a wrong answer
        wrong = (correct + 1) % max(len(q.options), 2)
        chosen = correct if i % 2 == 0 else wrong

        answers.append(StudentAnswer(
            question_id=q.id,
            selected_index=chosen,
        ))
        mark = "✅" if chosen == correct else "❌"
        print(f"   Q{q.id}: chose index {chosen} (correct: {correct}) {mark}")
    print()

    # ═══════════════════════════════════════════════════════
    # Step 3: Score quiz
    # ═══════════════════════════════════════════════════════
    print("─" * 40)
    print("📊 Scoring...")
    print()

    result = agent.score_quiz(quiz, answers, "demo_quiz_001")
    d = result.to_dict()

    print(f"   Score: {d['score_percent']}%")
    print(f"   Correct: {d['correct_count']}/{d['total_questions']}")
    print(f"   Points: {d['earned_points']}/{d['total_points']}")
    print()

    # ═══════════════════════════════════════════════════════
    # Step 4: Weakness detection
    # ═══════════════════════════════════════════════════════
    print("─" * 40)
    print("🔍 Weakness Detection")
    print()

    if d['weak_areas']:
        print("   ⚠️  Weak areas:")
        for area in d['weak_areas']:
            print(f"      • {area}")
    else:
        print("   🎉 No weak areas detected!")
    print()

    if d['strong_areas']:
        print("   💪 Strong areas:")
        for area in d['strong_areas']:
            print(f"      • {area}")
    print()

    # ═══════════════════════════════════════════════════════
    # Step 5: Recommendations
    # ═══════════════════════════════════════════════════════
    print("─" * 40)
    print("📝 Improvement Suggestions")
    print()

    for i, rec in enumerate(d['recommendations'], 1):
        print(f"   {i}. {rec}")
    print()

    # ═══════════════════════════════════════════════════════
    # Step 6: Score band analysis
    # ═══════════════════════════════════════════════════════
    print("─" * 40)
    print("📈 Score Band Analysis")
    print()

    score = d['score_percent']
    if score >= 90:
        band = "🏆 Excellent"
        action = "Ready for advanced topics"
    elif score >= 75:
        band = "✅ Good"
        action = "Minor review recommended"
    elif score >= 60:
        band = "📖 Needs Review"
        action = "Regenerate focus materials"
    elif score >= 40:
        band = "🔄 Let's Retry"
        action = "Switch teaching style and retake"
    else:
        band = "🆘 Start Over"
        action = "Rebuild from fundamentals"

    print(f"   Band: {band}")
    print(f"   Action: {action}")
    print()

    print("=" * 60)
    print("  ✅ Demo Complete — Evaluation Loop")
    print(f"  Result: {score}% — {band}")
    print("=" * 60)


if __name__ == "__main__":
    main()
