"""
veritas run — Execute a task through the Veritas Runtime.

Usage:
    veritas run --agent planner --task "create learning plan"
    veritas run -a evaluator -t "analyze output" --timeout 120
"""

from __future__ import annotations
import argparse
from typing import Optional

from ...sdk import RuntimeClient, TaskRequest
from ...sdk.exceptions import VeritasError
from ..formatter import Formatter, OutputFormat


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "run",
        help="Execute a task through the Veritas Runtime",
    )
    parser.add_argument(
        "--agent", "-a",
        required=True,
        help="Agent type (e.g. planner, evaluator, executor)",
    )
    parser.add_argument(
        "--task", "-t",
        required=True,
        help="Task objective / description",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Maximum execution time in seconds (default: 300)",
    )
    parser.add_argument(
        "--context",
        nargs="*",
        default=[],
        help="Context key=value pairs (e.g. level=beginner)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Output in compact summary format",
    )
    parser.set_defaults(func=handle_run)


def handle_run(args: argparse.Namespace) -> int:
    """Execute the 'veritas run' command."""
    # Parse context key=value pairs
    context = {}
    for pair in args.context:
        if "=" in pair:
            k, v = pair.split("=", 1)
            context[k] = v

    # Build TaskRequest
    task = TaskRequest(
        objective=args.task,
        agent=args.agent,
        context=context,
        timeout_seconds=args.timeout,
    )

    # Determine output format
    if args.json:
        fmt = Formatter(OutputFormat.JSON)
    elif args.summary:
        fmt = Formatter(OutputFormat.SUMMARY)
    else:
        fmt = Formatter(OutputFormat.TABLE)

    # Execute via RuntimeClient (no direct RuntimeEngine access)
    client = RuntimeClient()

    try:
        result = client.run(task)
        print(fmt.format_result(result))
        return 0 if result.is_success else 1
    except VeritasError as e:
        print(f"❌ Error: {e.detail}")
        return 1
