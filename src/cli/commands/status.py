"""
veritas status — Display Runtime status and health.

Usage:
    veritas status
    veritas status --json
"""

from __future__ import annotations
import argparse

from ...sdk import RuntimeClient
from ..formatter import Formatter, OutputFormat


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "status",
        help="Display Runtime status and health",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    parser.set_defaults(func=handle_status)


def handle_status(args: argparse.Namespace) -> int:
    """Display the current Veritas Runtime status."""
    fmt = Formatter(OutputFormat.JSON if args.json else OutputFormat.TABLE)
    client = RuntimeClient()

    data = client.status()
    print(fmt.format_status(data))
    return 0
