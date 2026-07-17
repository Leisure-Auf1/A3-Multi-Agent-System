"""
Phase 6.1 — Veritas CLI Package

Command-line interface for the Veritas Agent Runtime.
All CLI commands use RuntimeClient exclusively.
"""

from .main import main, create_parser

__all__ = ["main", "create_parser"]
