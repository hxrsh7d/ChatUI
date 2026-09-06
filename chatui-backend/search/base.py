from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str = ""


class SearchProvider(ABC):
    id: str = "base"

    @abstractmethod
    async def is_configured(self) -> bool: ...

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]: ...
