from __future__ import annotations

from typing import Optional

import config
from images.base import ImageProvider
from images.openai import OpenAIImageProvider

_PROVIDERS: dict[str, ImageProvider] = {
    "openai": OpenAIImageProvider(),
}


async def get_active_provider() -> Optional[ImageProvider]:
    if config.IMAGE_PROVIDER:
        provider = _PROVIDERS.get(config.IMAGE_PROVIDER)
        if provider and await provider.is_configured():
            return provider
        return None

    for provider in _PROVIDERS.values():
        if await provider.is_configured():
            return provider
    return None


async def is_image_generation_available() -> bool:
    return await get_active_provider() is not None
