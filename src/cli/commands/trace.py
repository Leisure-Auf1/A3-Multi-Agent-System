"""
veritas trace — Query DecisionTrace and explainability.

Usage:
    veritas trace SESSION_ID
    veritas trace SESSION_ID --json
"""

from __future__ import annotations
import argparse

from ...sdk import RuntimeClient
from ...sdk.exceptions import VeritasError
from ..formatter import Formatter, OutputFormat


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "trace",
        help="Query decision explainability for a session",
    )
    parser.add_argument(
        "session_id",
        help="Session ID to query traces for",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    parser.set_defaults(func=handle_trace)


def handle_trace(args: argparse.Namespace) -> int:
    """Query explainability data for a session."""
    fmt = Formatter(OutputFormat.JSON if args.json else OutputFormat.TABLE)
    client = RuntimeClient()

    try:
        data = client.explain(args.session_id)
        print(fmt.format_explain(data))
        return 0
    except VeritasError as e:
        print(f"❌ {e.detail}")
        return 1
