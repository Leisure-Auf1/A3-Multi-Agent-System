"""
Phase 9.5 — Code Provider

Generates Python code experiments/labs.
"""
from .base import BaseProvider, ProviderResult


CODE_TEMPLATES = {
    "beginner": '''
# {title}
# Topic: {topic}
# Level: {level}

def main():
    """Basic demonstration of {topic}."""
    print("Welcome to the {topic} code lab!")
    print("=" * 40)

    # TODO: Add your code here
    # Experiment with the concepts:
    {concept_placeholders}

    print("\\nCode lab complete! 🎉")

if __name__ == "__main__":
    main()
''',
    "intermediate": '''
"""{title} — Code Lab""\"

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Experiment:
    """Container for {topic} experiments."""
    name: str
    result: str = ""

    def run(self) -> str:
        return f"Experiment '{{self.name}}' completed."


def run_experiments() -> List[Experiment]:
    """Run all {topic} experiments."""
    experiments = []

    {concept_placeholders}

    return experiments


if __name__ == "__main__":
    results = run_experiments()
    for r in results:
        print(f"✓ {{r.name}}: {{r.run()}}")
    print(f"\\nAll {{len(results)}} experiments complete! 🎉")
''',
    "advanced": '''
"""{title} — Advanced Code Lab""\"

import time
from typing import Callable, Any
from functools import wraps


def benchmark(func: Callable) -> Callable:
    """Decorator to measure execution time."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"  ⏱️  {{func.__name__}}: {{elapsed:.4f}}s")
        return result
    return wrapper


@benchmark
def explore_concept_1():
    """Explore the first concept of {topic}."""
    {concept_placeholders}

    return "Concept 1 explored successfully"


@benchmark
def explore_concept_2():
    """Explore the second concept of {topic}."""
    pass  # TODO: Implement

    return "Concept 2 explored successfully"


if __name__ == "__main__":
    print("=" * 50)
    print(f"  {{'{title}'}} — Advanced Code Lab")
    print("=" * 50)
    print()

    results = [explore_concept_1(), explore_concept_2()]

    print()
    print("All advanced experiments complete! 🎉")
''',
}


class CodeProvider(BaseProvider):
    name = "code"
    cost_per_token = 0.0

    def _api_available(self) -> bool:
        return False  # Code is always locally generated

    def _generate_via_api(self, topic, title, concepts, profile, goal, level):
        return self._generate_via_rules(topic, title, concepts, profile, goal, level)

    def _generate_via_rules(self, topic, title, concepts, profile, goal, level):
        title = title or f"{topic} Code Lab"
        placeholders = self._build_placeholders(concepts, level)
        template = CODE_TEMPLATES.get(level, CODE_TEMPLATES["beginner"])
        code = template.format(
            title=title, topic=topic, level=level,
            concept_placeholders=placeholders,
        )
        return ProviderResult(
            content=code,
            content_format="python",
            provider_name="rule",
            fallback_level=1,
        )

    def _build_placeholders(self, concepts: list, level: str) -> str:
        if not concepts:
            return '    print("Add your code here")'

        lines = []
        for i, c in enumerate(concepts[:4], 1):
            name = c.lower().replace(" ", "_").replace("-", "_")
            lines.append(f"    # Experiment {i}: {c}")
            lines.append(f"    print(f\"Running experiment: {c}\")")
            if level == "beginner":
                lines.append(f'    result_{i} = "Result for {c}"')
                lines.append(f"    print(f\"  → {{result_{i}}}\")")
            elif level == "intermediate":
                lines.append(f"    exp_{i} = Experiment(name=\"{c}\")")
                lines.append(f"    exp_{i}.result = exp_{i}.run()")
                lines.append(f"    experiments.append(exp_{i})")
            else:
                lines.append(f"    # Advanced analysis of {c}")
                lines.append(f"    data = [x for x in range(10)]")
                lines.append(f"    result = sum(data)")
                lines.append(f"    print(f\"  Analysis complete: {{result}}\")")
            lines.append("")
        return "\n".join(lines)

    def _generate_mock(self, topic: str, title: str) -> ProviderResult:
        return ProviderResult(
            content=f'# {title or topic}\nprint("Mock code lab for {topic}")\n',
            content_format="python",
            provider_name="mock",
            fallback_level=2,
        )
