"""
PR #4 — Web Search Tool

DuckDuckGo HTML search via urllib (zero external dependencies).
Returns truncated summaries of search results.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
import re
import ssl
from html.parser import HTMLParser
from typing import List, Dict, Optional

from src.tools.base import BaseTool, ToolResult


class _DuckDuckGoParser(HTMLParser):
    """Minimal parser extracting result titles, snippets, and links from DDG HTML."""

    def __init__(self):
        super().__init__()
        self.results: List[Dict[str, str]] = []
        self._current: Dict[str, str] = {}
        self._in_result = False
        self._in_snippet = False
        self._in_link = False
        self._link_href = ""
        self._title_count = 0

    def handle_starttag(self, tag: str, attrs: list):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")

        if tag == "a" and "result__a" in cls:
            self._in_link = True
            self._link_href = attrs_dict.get("href", "")
            self._current = {"title": "", "snippet": "", "url": self._link_href}

        if tag == "a" and "result__snippet" in cls:
            self._in_snippet = True

    def handle_endtag(self, tag: str):
        if tag == "a" and self._in_link:
            self._in_link = False
            self._title_count += 1
        if tag == "a" and self._in_snippet:
            self._in_snippet = False

    def handle_data(self, data: str):
        text = data.strip()
        if not text:
            return
        if self._in_link and not self._current.get("title"):
            self._current["title"] = text
        if self._in_snippet:
            current = self._current.get("snippet", "")
            self._current["snippet"] = current + " " + text

    def close_result(self):
        if self._current.get("title") and self._current.get("url"):
            snippet = self._current.get("snippet", "").strip()
            self.results.append({
                "title": self._current["title"],
                "url": self._current.get("url", ""),
                "snippet": snippet[:300],
            })
        self._current = {}


class WebSearchTool(BaseTool):
    """Search the web using DuckDuckGo HTML (no API key required).

    Returns top 5 results with title, URL, and snippet.
    """

    name = "web_search"
    description = (
        "Search the web for current information. "
        "Use this when the student asks about recent events, "
        "latest developments, or facts beyond your training data."
    )
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to look up on the web",
            },
        },
        "required": ["query"],
    }

    MAX_RESULTS = 5
    TIMEOUT = 10

    def execute(self, query: str = "", **kwargs) -> ToolResult:
        """Execute a web search query via DuckDuckGo."""
        if not query or not query.strip():
            return ToolResult(
                success=False,
                tool_name=self.name,
                error="Empty search query",
            )

        try:
            results = self._search(query.strip())
            if not results:
                return ToolResult(
                    success=True,
                    tool_name=self.name,
                    content="No results found.",
                    metadata={"query": query},
                )

            content = self._format_results(results)
            return ToolResult(
                success=True,
                tool_name=self.name,
                content=content,
                metadata={"query": query, "count": len(results)},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=self.name,
                error=f"Search failed: {e}",
            )

    def _search(self, query: str) -> List[Dict[str, str]]:
        """Fetch and parse DuckDuckGo HTML results."""
        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"

        ctx = ssl.create_default_context()
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "A3-Learning-Assistant/1.0"},
        )

        try:
            with urllib.request.urlopen(req, context=ctx,
                                        timeout=self.TIMEOUT) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception:
            # Fallback: text-only endpoint
            url_lite = (f"https://lite.duckduckgo.com/lite/?q={encoded}")
            req_lite = urllib.request.Request(
                url_lite,
                headers={"User-Agent": "A3-Learning-Assistant/1.0"},
            )
            with urllib.request.urlopen(req_lite, context=ctx,
                                        timeout=self.TIMEOUT) as resp:
                html = resp.read().decode("utf-8", errors="replace")

        return self._parse_results(html)

    def _parse_results(self, html: str) -> List[Dict[str, str]]:
        """Parse HTML to extract search results."""
        # Try regex-based extraction first (more reliable)
        results = []

        # Pattern: link with class containing "result" followed by snippet
        link_pattern = re.compile(
            r'<a[^>]*class="[^"]*result[^"]*"[^>]*href="([^"]*)"[^>]*>'
            r'(.+?)</a>',
            re.DOTALL | re.IGNORECASE,
        )
        snippet_pattern = re.compile(
            r'<a[^>]*class="[^"]*snippet[^"]*"[^>]*>(.+?)</a>',
            re.DOTALL | re.IGNORECASE,
        )

        links = link_pattern.findall(html)
        snippets = snippet_pattern.findall(html)

        for i, (href, title) in enumerate(links[:self.MAX_RESULTS]):
            title_clean = re.sub(r"<[^>]+>", "", title).strip()
            snippet_clean = ""
            if i < len(snippets):
                snippet_clean = re.sub(r"<[^>]+>", "", snippets[i]).strip()

            results.append({
                "title": title_clean or "Untitled",
                "url": href,
                "snippet": snippet_clean[:300],
            })

        # Fallback: try DuckDuckGoParser if regex found nothing
        if not results:
            parser = _DuckDuckGoParser()
            parser.feed(html)
            parser.close_result()
            results = parser.results[:self.MAX_RESULTS]

        return results

    def _format_results(self, results: List[Dict[str, str]]) -> str:
        """Format search results for LLM context."""
        lines = [f"Web search results for the query:\n"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "Untitled")
            snippet = r.get("snippet", "")
            url = r.get("url", "")
            lines.append(f"{i}. **{title}**")
            if snippet:
                lines.append(f"   {snippet}")
            lines.append(f"   {url}")
            lines.append("")
        return "\n".join(lines)
