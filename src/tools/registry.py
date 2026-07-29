"""
PR #4 — Tool Registry

Central registry for tool discovery, lookup, and execution.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from src.tools.base import BaseTool, ToolResult


class ToolRegistry:
    """Register, discover, and execute tools.

    Usage:
        reg = ToolRegistry()
        reg.register(WebSearchTool())
        tool = reg.get("web_search")
        result = tool.execute(query="Python decorators")
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool. Overwrites if name exists."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """Check if a tool exists."""
        return name in self._tools

    def names(self) -> List[str]:
        """List all registered tool names."""
        return list(self._tools.keys())

    def to_openai_tools(self) -> list:
        """Generate OpenAI-compatible tools array for LLM calls."""
        return [t.to_openai_tool() for t in self._tools.values()]

    def execute(self, name: str, arguments: dict) -> ToolResult:
        """Execute a tool by name with given arguments.

        Returns ToolResult with success=False if tool not found or execution fails.
        """
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                success=False,
                tool_name=name,
                error=f"Tool '{name}' not found. Available: {', '.join(self.names())}",
            )
        try:
            return tool.execute(**arguments)
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=name,
                error=f"Tool execution failed: {e}",
            )

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
