"""
PR #4 — Tool Base Classes

Abstract base for all tools + ToolResult dataclass.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool = False
    content: str = ""
    tool_name: str = ""
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_message(self) -> Dict[str, str]:
        """Convert to OpenAI tool result message format."""
        return {
            "role": "tool",
            "content": self.content[:4000] if self.success
            else f"Error: {self.error}",
        }


class BaseTool(ABC):
    """Abstract base for all tools.

    Subclasses MUST override:
      - name: str (unique identifier)
      - description: str (for LLM function definition)
      - parameters: dict (JSON Schema for function arguments)
      - execute(**kwargs) -> ToolResult
    """

    name: str = ""
    description: str = ""
    parameters: dict = {"type": "object", "properties": {}, "required": []}

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given arguments."""
        ...

    def to_openai_tool(self) -> dict:
        """Generate OpenAI-compatible function definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
