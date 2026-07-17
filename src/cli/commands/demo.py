"""
veritas demo — Run showcase demonstrations.

Usage:
    veritas demo multiagent
    veritas demo lifecycle
    veritas demo plugins
    veritas demo recovery
    veritas demo learning
    veritas demo all
"""

from __future__ import annotations
import argparse
import subprocess
import sys
import os


DEMOS = {
    "multiagent": "examples/showcase/multi_agent_demo.py",
    "lifecycle": "examples/showcase/lifecycle_demo.py",
    "plugins": "examples/showcase/plugin_demo.py",
    "recovery": "examples/showcase/recovery_demo.py",
    "learning": "examples/showcase/learning_pipeline_demo.py",
}


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "demo",
        help="Run Veritas showcase demonstrations",
    )
    parser.add_argument(
        "demo_name",
        nargs="?",
        default="all",
        choices=list(DEMOS.keys()) + ["all"],
        help="Which demo to run (default: all)",
    )
    parser.set_defaults(func=handle_demo)


def handle_demo(args: argparse.Namespace) -> int:
    """Execute showcase demos."""
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )))

    demos_to_run = list(DEMOS.keys()) if args.demo_name == "all" else [args.demo_name]

    for name in demos_to_run:
        path = os.path.join(repo_root, DEMOS[name])
        if not os.path.exists(path):
            print(f"❌ Demo '{name}' not found at {path}", file=sys.stderr)
            return 1

        print(f"\n{'=' * 60}")
        print(f"  Running: {name} demo")
        print(f"{'=' * 60}")

        result = subprocess.run(
            [sys.executable, path],
            cwd=repo_root,
            capture_output=False,
        )
        if result.returncode != 0 and args.demo_name != "all":
            return result.returncode

    return 0
