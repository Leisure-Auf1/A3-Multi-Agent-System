"""
Veritas Agent Runtime — setup

Minimal setup for the CLI entry point.
Allows: pip install -e .  →  veritas command available.
"""
from setuptools import setup, find_packages

setup(
    name="veritas-core",
    version="6.1.0",
    description="Agent Runtime Framework CLI",
    packages=find_packages(where=".", include=["src", "src.*"]),
    package_dir={"": "."},
    entry_points={
        "console_scripts": [
            "veritas = src.cli.main:main",
        ],
    },
    python_requires=">=3.10",
)
