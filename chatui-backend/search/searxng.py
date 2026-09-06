from __future__ import annotations

import httpx

import config
from search.base import SearchProvider, SearchResult


class SearxngSearchProvider(SearchProvider):
    id = "searxng"

    def __init__(self) -> None:
        self.base_url = config.SEARXNG_URL.rstrip("/") if config.SEARXNG_URL else ""

    async def is_configured(self) -> bool:
        return bool(self.base_url)

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        if not await self.is_configured():
            raise RuntimeError("SearXNG is not configured (missing SEARXNG_URL).")

        async with httpx.AsyncClient(timeout=config.PROVIDER_REQUEST_TIMEOUT) as client:
            response = await client.get(
                f"{self.base_url}/search",
                params={"q": query, "format": "json"},
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
