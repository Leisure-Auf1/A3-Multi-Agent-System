"""
veritas plugins — List installed RuntimePlugins.

Usage:
    veritas plugins
    veritas plugins --json
"""

from __future__ import annotations
import argparse

from ...sdk import RuntimeClient
from ..formatter import Formatter, OutputFormat


def register_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "plugins",
        help="List installed RuntimePlugins",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    parser.set_defaults(func=handle_plugins)


def handle_plugins(args: argparse.Namespace) -> int:
    """List all installed plugins."""
    fmt = Formatter(OutputFormat.JSON if args.json else OutputFormat.TABLE)
    client = RuntimeClient()

    # Plugins come from config for now
    # In future: client.plugins() SDK method
    plugins = [
        {"name": p.name, "version": "1.0", "state": "started" if p.enabled else "disabled", "priority": 0}
        for p in client.config.plugins
    ]
    print(fmt.format_plugins(plugins))
    return 0
