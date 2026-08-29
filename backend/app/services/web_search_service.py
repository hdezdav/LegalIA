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
    # Strip markdown and bracketed tags like [AGENT: ...], [MODO: ...]
    cleaned = re.sub(r"\[[^\]]+\]", "", query)
    cleaned = re.sub(r"Consulta del litigante:\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"Analiza este documento[^\n]*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if len(cleaned) >= 3 else query.strip()


def _search_tavily_sync(query: str, api_key: str, max_results: int = 6) -> list[WebSearchResult]:
    """Execute live search via Tavily AI API with advanced depth and answer synthesis."""
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "include_answer": True,
        "include_domains": [],
        "max_results": max_results,
    }
    results: list[WebSearchResult] = []

    with httpx.Client(timeout=12.0) as client:
        resp = client.post(url, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            
            # If Tavily synthesized a direct factual answer, include it as first grounding item
            tavily_answer = data.get("answer")
            if tavily_answer and len(tavily_answer) > 20:
                results.append(
                    WebSearchResult(
                        title="Síntesis de Información Actualizada (Tavily AI)",
                        url="https://tavily.com",
                        snippet=tavily_answer,
                        domain="tavily.com",
                    )
                )

            for item in data.get("results", []):
                item_url = item.get("url") or ""
                title = item.get("title") or "Fuente Web Oficial"
                snippet = item.get("content") or ""
                if item_url and not any(r.url == item_url for r in results):
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
                if url and not any(r.url == url for r in results):
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


def search_web_sync(query: str, max_results: int = 6) -> list[WebSearchResult]:
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
