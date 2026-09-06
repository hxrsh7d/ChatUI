from __future__ import annotations

import httpx

import config
from search.base import SearchProvider, SearchResult


class TavilySearchProvider(SearchProvider):
    id = "tavily"

    def __init__(self) -> None:
        self.api_key = config.TAVILY_API_KEY

    async def is_configured(self) -> bool:
        return bool(self.api_key)

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        if not await self.is_configured():
            raise RuntimeError("Tavily is not configured (missing TAVILY_API_KEY).")

        async with httpx.AsyncClient(timeout=config.PROVIDER_REQUEST_TIMEOUT) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": self.api_key, "query": query, "max_results": max_results},
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("results", [])[:max_results]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                )
            )
        return results
