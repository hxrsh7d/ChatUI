"""Groq provider. Groq exposes an OpenAI-compatible API, so this is a thin
configuration of the shared OpenAICompatibleProvider -- no duplicated HTTP
logic."""

from __future__ import annotations

import config
from providers.openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    def __init__(self) -> None:
        super().__init__(
            provider_id="groq",
            display_name="Groq",
            base_url=config.GROQ_BASE_URL,
            api_key=config.GROQ_API_KEY,
            group="Groq",
            static_models=["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
            supports_image_generation=False,
        )

    async def is_configured(self) -> bool:
        return bool(self.api_key)
