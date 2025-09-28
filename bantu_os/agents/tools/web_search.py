"""
Web search tool with SerpAPI (preferred if key available) or DuckDuckGo fallback.

- If SERPAPI_API_KEY env var (or api_key arg) is provided, uses SerpAPI
  (Google engine) and returns top organic results.
- Otherwise uses DuckDuckGo Instant Answer API (limited but dependency-free).

This tool is synchronous and uses only Python's standard library for HTTP.
"""
from __future__ import annotations

import json
import os
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode
from urllib.request import urlopen, Request


def _http_get_json(url: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    req = Request(url, headers=headers or {"User-Agent": "bantu-os/0.1"})
    with urlopen(req, timeout=20) as resp:  # nosec - simple GET for public APIs
        data = resp.read()
    return json.loads(data.decode("utf-8", errors="replace"))


def _format_results(items: List[Dict[str, str]], limit: int) -> str:
    lines = []
    for i, it in enumerate(items[:limit], start=1):
        title = it.get("title") or it.get("text") or "(no title)"
        link = it.get("link") or it.get("url") or ""
        snippet = it.get("snippet") or it.get("description") or ""
        if link:
            lines.append(f"{i}. {title}\n   {link}\n   {snippet}")
        else:
            lines.append(f"{i}. {title}\n   {snippet}")
    return "\n".join(lines) if lines else "No results."


def web_search(query: str, *, api_key: Optional[str] = None, limit: int = 5) -> str:
    """Search the web and return a concise list of results as text.

    Prefers SerpAPI if an API key is available, else falls back to
    DuckDuckGo Instant Answer (limited coverage).
    """
    key = api_key or os.getenv("SERPAPI_API_KEY")
    if key:
        # SerpAPI (Google engine)
        params = {
            "engine": "google",
            "q": query,
            "num": max(1, min(limit, 10)),
            "api_key": key,
        }
        url = f"https://serpapi.com/search.json?{urlencode(params)}"
        data = _http_get_json(url)
        items: List[Dict[str, str]] = []
        for r in data.get("organic_results", [])[:limit]:
            items.append({
                "title": r.get("title", ""),
                "link": r.get("link", ""),
                "snippet": r.get("snippet", ""),
            })
        return _format_results(items, limit)

    # DuckDuckGo Instant Answer API fallback
    ddg_params = {
        "q": query,
        "format": "json",
        "no_html": "1",
        "no_redirect": "1",
    }
    ddg_url = f"https://api.duckduckgo.com/?{urlencode(ddg_params)}"
    data = _http_get_json(ddg_url)

    items = []
    abstract = data.get("AbstractText") or data.get("Abstract") or ""
    abstract_url = data.get("AbstractURL") or data.get("AbstractSourceUrl") or ""
    if abstract:
        items.append({"title": "Summary", "snippet": abstract, "link": abstract_url})

    def _collect_topics(topics: List[Dict[str, Any]]) -> None:
        for t in topics:
            if "Topics" in t:
                _collect_topics(t["Topics"])  # nested groups
            else:
                text = t.get("Text") or ""
                url = t.get("FirstURL") or ""
                if text or url:
                    items.append({"title": text, "link": url, "snippet": ""})

    related = data.get("RelatedTopics") or []
    _collect_topics(related)

    return _format_results(items, limit)
