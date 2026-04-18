"""
Rokan Search — Web search via DuckDuckGo. No API key needed.
Injects search results into the LLM context so Rokan can answer
real-time questions with live data.
"""

from __future__ import annotations


def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web and return a formatted context string
    ready to be injected into the LLM messages.
    Returns plain text summary of results.
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "[SEARCH] duckduckgo-search not installed."

    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title  = r.get("title", "")
                body   = r.get("body", "")
                href   = r.get("href", "")
                results.append(f"• {title}\n  {body}\n  Source: {href}")

        if not results:
            return f"[SEARCH] No results found for: {query}"

        header = f"[WEB SEARCH RESULTS for: {query}]\n"
        return header + "\n\n".join(results)

    except Exception as exc:
        return f"[SEARCH ERROR] {type(exc).__name__}: {exc}"


def news_search(query: str, max_results: int = 5) -> str:
    """Search latest news items."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "[SEARCH] duckduckgo-search not installed."

    try:
        results = []
        with DDGS() as ddgs:
            for r in ddgs.news(query, max_results=max_results):
                title  = r.get("title", "")
                body   = r.get("body", "")
                source = r.get("source", "")
                date   = r.get("date", "")
                results.append(f"• [{date}] {title} — {source}\n  {body}")

        if not results:
            return f"[NEWS] No news found for: {query}"

        header = f"[LIVE NEWS for: {query}]\n"
        return header + "\n\n".join(results)

    except Exception as exc:
        return f"[NEWS ERROR] {type(exc).__name__}: {exc}"
