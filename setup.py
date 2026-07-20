"""
A3 Multi-Agent System — Application

Install: pip install -e .
Depends on: veritas-core (runtime framework)
"""
from setuptools import setup, find_packages

setup(
    name="a3-multi-agent-system",
    version="1.0.0",
    description="A3 Multi-Agent Personalized Learning System",
    packages=find_packages(where=".", include=["src", "src.*"]),
    package_dir={"": "."},
    python_requires=">=3.10",
    install_requires=[
        "veritas-core>=7.0.0",
    ],
)
