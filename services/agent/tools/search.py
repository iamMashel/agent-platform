from __future__ import annotations

import structlog
from ddgs import DDGS
from langchain_core.tools import tool

log = structlog.get_logger(__name__)

_MAX_RESULTS = 3
_TIMEOUT = 10


@tool
def search_tool(query: str) -> str:
    """Search the web using DuckDuckGo and return a summary of the top results.

    Args:
        query: The search query string.

    Returns:
        A formatted string with the top search results.
    """
    log.debug("search.duckduckgo", query=query)
    try:
        with DDGS(timeout=_TIMEOUT) as ddgs:
            results = list(ddgs.text(query, max_results=_MAX_RESULTS))

        if not results:
            return f"No results found for: {query}"

        parts: list[str] = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            body = r.get("body", "")
            href = r.get("href", "")
            parts.append(f"[{i}] {title}\n{body}\nSource: {href}")

        return "\n\n".join(parts)

    except Exception as exc:
        log.warning("search.duckduckgo.error", error=str(exc))
        return f"Search failed: {exc}. Please try rephrasing your query."
