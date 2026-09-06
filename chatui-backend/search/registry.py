from __future__ import annotations

from typing import Optional

import config
from search.base import SearchProvider, SearchResult
from search.brave import BraveSearchProvider
from search.searxng import SearxngSearchProvider
from search.tavily import TavilySearchProvider

_PROVIDERS: dict[str, SearchProvider] = {
    "brave": BraveSearchProvider(),
    "tavily": TavilySearchProvider(),
    "searxng": SearxngSearchProvider(),
}


async def get_active_provider() -> Optional[SearchProvider]:
    """Returns the configured SEARCH_PROVIDER if it's actually usable, else
    falls back to the first provider that happens to be configured (so
    setting just BRAVE_API_KEY without also setting SEARCH_PROVIDER=brave
    still works), else None."""
    if config.SEARCH_PROVIDER:
        provider = _PROVIDERS.get(config.SEARCH_PROVIDER)
        if provider and await provider.is_configured():
            return provider
        return None

    for provider in _PROVIDERS.values():
        if await provider.is_configured():
            return provider
    return None


async def is_search_available() -> bool:
    return await get_active_provider() is not None


def build_context_block(results: list[SearchResult]) -> str:
    if not results:
        return ""
    parts = ["Web search results for the user's question:"]
    for i, r in enumerate(results, start=1):
        parts.append(f"\n[{i}] {r.title}\n{r.url}\n{r.snippet}")
    parts.append(
        "\nGround your answer in the results above and mention when information comes from them. "
        "If they don't answer the question, say so."
    )
    return "\n".join(parts)
