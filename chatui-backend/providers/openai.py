"""
OpenAI provider. Chat/completions + model discovery reuse the generic
OpenAI-compatible base; image generation is handled separately by
images/openai.py since it's a different endpoint family (/v1/images).
"""

from __future__ import annotations

import config
from providers.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    def __init__(self) -> None:
        super().__init__(
            provider_id="openai",
            display_name="OpenAI",
            base_url=config.OPENAI_BASE_URL,
            api_key=config.OPENAI_API_KEY,
            group="OpenAI",
            # Used only if live discovery via GET /v1/models fails or the
            # account can't list models; keeps the UI useful without ever
            # claiming these are confirmed-available unless the API key
            # actually works.
            static_models=["gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini", "o4-mini"],
            supports_image_generation=True,
        )

    async def is_configured(self) -> bool:
        return bool(self.api_key)

    async def list_models(self) -> list:
        models = await super().list_models()
        # OpenAI's /v1/models includes embeddings/moderation/tts/whisper
        # models too -- filter to ones that are plausibly chat models so we
        # don't advertise things this gateway can't call as chat.
        chat_like = [
            m
            for m in models
            if not any(x in m.name.lower() for x in ("embedding", "whisper", "tts", "moderation", "davinci-002", "babbage"))
        ]
        return chat_like or models
