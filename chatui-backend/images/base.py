from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GeneratedImage:
    url: str
    prompt: str = ""


class ImageProvider(ABC):
    id: str = "base"

    @abstractmethod
    async def is_configured(self) -> bool: ...

    @abstractmethod
    async def generate(self, prompt: str, size: str = "1024x1024") -> GeneratedImage: ...
