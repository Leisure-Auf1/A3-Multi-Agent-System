"""
Phase 6.1 — Veritas CLI

Command-line interface for the Veritas Agent Runtime.
All commands go through RuntimeClient — zero direct RuntimeEngine access.

Usage:
    veritas run --agent planner --task "create learning plan"
    veritas status
    veritas trace SESSION_ID
    veritas plugins

Architecture:
    User → CLI → RuntimeClient → RuntimeAdapter → RuntimeEngine
                                              (hidden)
"""

from __future__ import annotations
import sys
import argparse
from typing import List, Optional

from .commands import run, status, trace, plugins


def create_parser() -> argparse.ArgumentParser:
    """Build the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="veritas",
        description="Veritas Agent Runtime CLI",
        epilog="For more: https://github.com/Leisure-Auf1/A3-Multi-Agent-System",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="veritas 6.1.0",
    )

    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        help="Available commands",
    )

    # Register all subcommands
    run.register_parser(subparsers)
    status.register_parser(subparsers)
    trace.register_parser(subparsers)
    plugins.register_parser(subparsers)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main CLI entry point.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted")
        return 130
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
