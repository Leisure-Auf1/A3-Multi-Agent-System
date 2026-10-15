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
        "veritas-core @ git+https://github.com/Leisure-Auf1/Veritas-Core.git@29a42debc46fdbbd5fb84c4213035971986344af",
        "streamlit>=1.28.0",
        "fastapi>=0.115.0",
        "uvicorn>=0.30.0",
        "keyring>=25.0.0",
        "networkx>=3.2",
        "python-pptx>=1.0",
    ],
)
