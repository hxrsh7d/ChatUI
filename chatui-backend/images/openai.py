from __future__ import annotations

import httpx

import config
from images.base import GeneratedImage, ImageProvider


class OpenAIImageProvider(ImageProvider):
    id = "openai"

    def __init__(self) -> None:
        self.api_key = config.OPENAI_API_KEY
        self.base_url = config.OPENAI_BASE_URL.rstrip("/")
        self.model = config.OPENAI_IMAGE_MODEL

    async def is_configured(self) -> bool:
        return bool(self.api_key)

    async def generate(self, prompt: str, size: str = "1024x1024") -> GeneratedImage:
        if not await self.is_configured():
            raise RuntimeError("OpenAI image generation is not configured (missing OPENAI_API_KEY).")

        async with httpx.AsyncClient(timeout=config.PROVIDER_REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{self.base_url}/images/generations",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": self.model, "prompt": prompt, "size": size, "n": 1},
            )
            if response.status_code != 200:
                body = response.text[:400]
                raise RuntimeError(f"OpenAI image generation failed ({response.status_code}): {body}")
            data = response.json()

        item = (data.get("data") or [{}])[0]
        if item.get("url"):
            return GeneratedImage(url=item["url"], prompt=prompt)
        if item.get("b64_json"):
            return GeneratedImage(url=f"data:image/png;base64,{item['b64_json']}", prompt=prompt)

        raise RuntimeError("OpenAI image generation returned no image data.")
