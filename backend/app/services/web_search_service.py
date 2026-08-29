"""Live web search service using Tavily AI Search with DuckDuckGo fallback.

Primary Provider: Tavily AI Search (optimized specifically for LLM context grounding).
Fallback Provider: DuckDuckGo / ddgs (zero-configuration free search).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import re
from typing import Any
from urllib.parse import urlparse
import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(slots=True)
class WebSearchResult:
    title: str
    url: str
    snippet: str
    domain: str


def _clean_domain(url_str: str) -> str:
    try:
        parsed = urlparse(url_str)
        return parsed.netloc.replace("www.", "")
    except Exception:
        return "web"


def _clean_search_query(query: str) -> str:
    """Strip bracketed system tags, memory headers or directives before searching."""
    cleaned = re.sub(r"\[[^\]]+\]", "", query)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if len(cleaned) >= 3 else query.strip()


def _search_tavily_sync(query: str, api_key: str, max_results: int = 5) -> list[WebSearchResult]:
    """Execute live search via Tavily AI API."""
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "include_answer": False,
        "max_results": max_results,
    }
    results: list[WebSearchResult] = []

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(url, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get("results", []):
                item_url = item.get("url") or ""
                title = item.get("title") or "Fuente Web"
                snippet = item.get("content") or ""
                if item_url:
                    results.append(
                        WebSearchResult(
                            title=title,
                            url=item_url,
                            snippet=snippet,
                            domain=_clean_domain(item_url),
                        )
                    )
        else:
            logger.warning("Tavily search returned non-200 status", extra={"status": resp.status_code, "body": resp.text[:200]})

    return results


def _search_ddg_sync(query: str, max_results: int = 5) -> list[WebSearchResult]:
    """Execute synchronous live search via ddgs / duckduckgo."""
    results: list[WebSearchResult] = []
    try:
        from ddgs import DDGS

        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
            for item in raw_results:
                url = item.get("href") or item.get("url") or ""
                title = item.get("title") or "Fuente Web"
                snippet = item.get("body") or item.get("snippet") or ""
                if url:
                    results.append(
                        WebSearchResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                            domain=_clean_domain(url),
                        )
                    )
    except Exception as exc:
        logger.warning("DuckDuckGo fallback search failed", extra={"query": query, "error": str(exc)})

    return results


def search_web_sync(query: str, max_results: int = 5) -> list[WebSearchResult]:
    """Execute live web search prioritizing Tavily with DuckDuckGo fallback."""
    clean_query = _clean_search_query(query)
    tavily_key = settings.TAVILY_API_KEY.get_secret_value().strip() if settings.TAVILY_API_KEY else ""

    # 1. Try Tavily first if key is configured
    if tavily_key:
        try:
            tavily_results = _search_tavily_sync(clean_query, tavily_key, max_results=max_results)
            if tavily_results:
                return tavily_results
        except Exception as exc:
            logger.warning("Tavily search failed, switching to DuckDuckGo fallback", extra={"error": str(exc)})

    # 2. Fallback to DuckDuckGo
    return _search_ddg_sync(clean_query, max_results=max_results)


async def search_web_async(query: str, max_results: int = 5) -> list[WebSearchResult]:
    """Asynchronous non-blocking wrapper for live search."""
    return await asyncio.to_thread(search_web_sync, query, max_results)
