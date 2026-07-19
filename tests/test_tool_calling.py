"""
PR #4 — Tool Calling Tests

Tool registry, web search, tutor agent with tools, cross-user isolation.
"""
from __future__ import annotations

import sys, os, uuid, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient


# ══════════════════════════════════════════════════
# Tool Registry Tests
# ══════════════════════════════════════════════════

class TestToolRegistry:
    def test_register_and_get_tool(self):
        from src.tools import ToolRegistry, WebSearchTool
        reg = ToolRegistry()
        reg.register(WebSearchTool())
        assert len(reg) == 1
        assert "web_search" in reg
        tool = reg.get("web_search")
        assert tool is not None
        assert tool.name == "web_search"

    def test_register_multiple_tools(self):
        from src.tools import ToolRegistry, WebSearchTool, ToolResult

        class EchoTool(WebSearchTool):
            name = "echo"
            description = "Echoes input"
            parameters = {"type": "object", "properties": {
                "text": {"type": "string"}}, "required": ["text"]}

            def execute(self, query="", **kwargs):
                return ToolResult(success=True, content=str(kwargs.get("text", query)),
                                  tool_name="echo")

        reg = ToolRegistry()
        reg.register(WebSearchTool())
        reg.register(EchoTool())
        assert len(reg) == 2
        names = reg.names()
        assert "echo" in names
        assert "web_search" in names

    def test_execute_unknown_tool(self):
        from src.tools import ToolRegistry
        reg = ToolRegistry()
        result = reg.execute("nonexistent", {"q": "test"})
        assert not result.success
        assert "not found" in result.error.lower()

    def test_execute_registered_tool(self):
        from src.tools import ToolRegistry, WebSearchTool

        class MockSearch(WebSearchTool):
            def execute(self, query="", **kwargs):
                from src.tools.base import ToolResult
                return ToolResult(
                    success=True, tool_name="web_search",
                    content=f"Mock results for: {query}",
                )

        reg = ToolRegistry()
        reg.register(MockSearch())
        result = reg.execute("web_search", {"query": "Python"})
        assert result.success
        assert "Python" in result.content

    def test_to_openai_tools_format(self):
        from src.tools import ToolRegistry, WebSearchTool
        reg = ToolRegistry()
        reg.register(WebSearchTool())
        tools = reg.to_openai_tools()
        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert tools[0]["function"]["name"] == "web_search"


# ══════════════════════════════════════════════════
# Web Search Tool Tests
# ══════════════════════════════════════════════════

class TestWebSearchTool:
    def test_to_openai_tool(self):
        from src.tools import WebSearchTool
        tool = WebSearchTool()
        spec = tool.to_openai_tool()
        assert spec["type"] == "function"
        assert spec["function"]["name"] == "web_search"
        assert "query" in spec["function"]["parameters"]["required"]

    def test_empty_query_returns_error(self):
        from src.tools import WebSearchTool
        tool = WebSearchTool()
        result = tool.execute(query="")
        assert not result.success
        assert "empty" in result.error.lower()

    def test_search_returns_formatted_results(self):
        """Integration test — real DuckDuckGo search."""
        from src.tools import WebSearchTool
        tool = WebSearchTool()
        result = tool.execute(query="Python programming language")
        assert result.success
        # May return results or "No results" — both are valid
        assert result.tool_name == "web_search"


# ══════════════════════════════════════════════════
# TutorAgent with Tools Tests
# ══════════════════════════════════════════════════

class TestTutorAgentWithTools:
    def test_tutor_without_tools_unchanged(self):
        """TutorAgent without tool_registry behaves identically."""
        from src.agents.tutor_agent import TutorAgent
        tutor = TutorAgent(llm_provider=None)
        assert not tutor.has_tools
        resp = tutor.explain("What is Python?")
        assert len(resp.content) > 0
        assert resp.tool_calls_made == 0

    def test_tutor_with_tool_registry_has_tools(self):
        """TutorAgent with tool_registry reports has_tools=True."""
        from src.agents.tutor_agent import TutorAgent
        from src.tools import ToolRegistry, WebSearchTool

        reg = ToolRegistry()
        reg.register(WebSearchTool())
        tutor = TutorAgent(llm_provider=None, tool_registry=reg)
        assert tutor.has_tools

    def test_has_tools_false_when_registry_empty(self):
        """has_tools is False when registry has no tools."""
        from src.agents.tutor_agent import TutorAgent
        from src.tools import ToolRegistry

        reg = ToolRegistry()
        tutor = TutorAgent(llm_provider=None, tool_registry=reg)
        assert not tutor.has_tools

    def test_tool_response_includes_count(self):
        """TutorResponse.tool_calls_made defaults to 0."""
        from src.agents.tutor_agent import TutorAgent, TutorResponse
        resp = TutorResponse(content="test")
        assert resp.tool_calls_made == 0

    def test_tutor_fallback_still_works_with_tools(self):
        """Fallback explain works even with tool_registry."""
        from src.agents.tutor_agent import TutorAgent
        from src.tools import ToolRegistry, WebSearchTool

        reg = ToolRegistry()
        reg.register(WebSearchTool())
        tutor = TutorAgent(llm_provider=None, tool_registry=reg)
        resp = tutor.explain("test")
        assert "rule-based" in resp.content.lower()


# ══════════════════════════════════════════════════
# Integration: Chat API with Tools
# ══════════════════════════════════════════════════

class TestChatAPIWithTools:
    @pytest.fixture
    def client(self):
        from src.api.server import app
        return TestClient(app)

    def _auth(self, client):
        email = f"tool_{uuid.uuid4().hex[:6]}@test.com"
        client.post("/api/v2/auth/register", json={
            "email": email, "password": "testpass", "display_name": "T"})
        resp = client.post("/api/v2/auth/login", json={
            "email": email, "password": "testpass"})
        return {"Authorization": f"Bearer {resp.json()['token']}"}

    def test_chat_message_returns_tool_calls_count(self, client):
        """Chat response includes tool_calls_made in JSON."""
        headers = self._auth(client)
        resp = client.post("/api/v2/chat/message", json={
            "message": "Tell me about Python",
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "tool_calls_made" in data
        assert isinstance(data["tool_calls_made"], int)


# ══════════════════════════════════════════════════
# Cross-User Isolation (PR #2.1 regression)
# ══════════════════════════════════════════════════

class TestToolCrossUserIsolation:
    """Tool results must not leak across users — same gates as PR #2.1."""

    @pytest.fixture
    def client(self):
        from src.api.server import app
        return TestClient(app)

    def _auth(self, client, prefix="A"):
        email = f"tool_{prefix}_{uuid.uuid4().hex[:4]}@test.com"
        client.post("/api/v2/auth/register", json={
            "email": email, "password": "testpass", "display_name": prefix})
        resp = client.post("/api/v2/auth/login", json={
            "email": email, "password": "testpass"})
        return {"Authorization": f"Bearer {resp.json()['token']}"}

    def test_thread_isolation_still_holds(self, client):
        """User A's chat with tools invisible to User B."""
        h_a = self._auth(client, "A")
        h_b = self._auth(client, "B")

        # User A creates thread
        r = client.post("/api/v2/chat/message", json={
            "message": "What is Python?",
        }, headers=h_a)
        tid = r.json()["thread_id"]

        # User B cannot access
        r = client.get(f"/api/v2/chat/threads/{tid}/messages", headers=h_b)
        assert r.status_code in (403, 404)
