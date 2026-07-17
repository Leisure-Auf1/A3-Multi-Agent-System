#!/usr/bin/env python3
"""
A3 Demo — Multimodal Generation Gateway

Generate 7 types of learning materials for a topic via the MultimodalGateway.

Shows: Gateway routing → Provider selection → Validation → Artifact output

Run: python examples/multimodal_generation_demo.py
"""
from __future__ import annotations
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    print("=" * 60)
    print("  A3 Demo — Multimodal Generation Gateway")
    print("=" * 60)
    print()

    topic = "Python Object-Oriented Programming"
    concepts = ["classes", "inheritance", "polymorphism", "encapsulation"]

    print(f"🎯 Topic: {topic}")
    print(f"📝 Concepts: {', '.join(concepts)}")
    print()

    # ═══════════════════════════════════════════════════════
    # Gateway generation — all 7 types
    # ═══════════════════════════════════════════════════════
    from src.multimodal.gateway import MultimodalGateway, GenerateRequest
    from src.multimodal.artifact import ResourceType

    gateway = MultimodalGateway(user_tier="pro")
    resource_types = [
        (ResourceType.DOCUMENT, "📄 Course Notes"),
        (ResourceType.MINDMAP, "🧠 Mind Map"),
        (ResourceType.EXERCISE, "✏️ Exercises"),
        (ResourceType.CODE_LAB, "💻 Code Lab"),
        (ResourceType.SLIDES, "📊 PPT Slides"),
        (ResourceType.ILLUSTRATION, "🖼️ Illustration"),
        (ResourceType.VIDEO_SCRIPT, "🎬 Video Script"),
    ]

    results = []
    for rt, label in resource_types:
        print(f"  {label} ... ", end="", flush=True)
        artifact = gateway.generate(GenerateRequest(
            resource_type=rt,
            topic=topic,
            title=f"{topic} — {label[2:]}",
            concepts=concepts,
        ))
        status_icon = "✅" if artifact.status.value == "active" else "❌"
        print(f"{status_icon} [{artifact.provider}] ({len(artifact.content)} chars)")
        results.append((rt, label, artifact))

    print()
    print("─" * 40)
    print("📊 Generation Summary")
    print("─" * 40)

    active = [a for _, _, a in results if a.status.value == "active"]
    failed = [a for _, _, a in results if a.status.value == "failed"]
    print(f"   Active: {len(active)}/{len(results)}")
    print(f"   Failed: {len(failed)}/{len(results)}")
    print()

    # Show providers used
    print("   Provider Breakdown:")
    providers = set(a.provider for _, _, a in results)
    for p in sorted(providers):
        count = sum(1 for _, _, a in results if a.provider == p)
        print(f"     {p}: {count} artifacts")
    print()

    # Show sample content
    print("─" * 40)
    print("📄 Sample: Course Notes (first 300 chars)")
    print("─" * 40)
    for rt, label, a in results:
        if rt == ResourceType.DOCUMENT and a.content:
            print(a.content[:300] + "...")
            break
    print()

    # Show validation status
    print("─" * 40)
    print("🔍 Validation Results")
    print("─" * 40)
    for rt, label, a in results:
        errs = a.validation_errors
        status = "✅ clean" if not errs else f"⚠️  {len(errs)} issues"
        print(f"   {label}: {status}")
    print()

    print("=" * 60)
    print("  ✅ Demo Complete — 7 resource types generated")
    print("=" * 60)


if __name__ == "__main__":
    main()
