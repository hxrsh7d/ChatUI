from __future__ import annotations

import httpx

import config
from search.base import SearchProvider, SearchResult


class BraveSearchProvider(SearchProvider):
    id = "brave"

    def __init__(self) -> None:
        self.api_key = config.BRAVE_API_KEY

    async def is_configured(self) -> bool:
        return bool(self.api_key)

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        if not await self.is_configured():
            raise RuntimeError("Brave Search is not configured (missing BRAVE_API_KEY).")

        async with httpx.AsyncClient(timeout=config.PROVIDER_REQUEST_TIMEOUT) as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": max_results},
                headers={"Accept": "application/json", "X-Subscription-Token": self.api_key},
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for item in data.get("web", {}).get("results", [])[:max_results]:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                )
            )
        return results
