"""
Generic OpenAI-compatible chat provider.

OpenAI, Groq, vLLM, and most self-hosted inference servers all speak the
same `/v1/chat/completions` + `/v1/models` dialect. Rather than duplicate
that HTTP logic per vendor, every OpenAI-shaped provider (OpenAIProvider,
GroqProvider, CustomOpenAICompatibleProvider) subclasses this class and
only customizes id/display_name/base_url/api_key/known-model fallback list.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Optional

import httpx

import config
from providers.base import AIProvider, Capabilities, ModelInfo, ProviderError

VISION_HINTS = ("vision", "gpt-4o", "gpt-4.1", "gpt-5", "o3", "o4", "4o-mini", "llama-3.2-90b-vision", "llama-3.2-11b-vision")


def _looks_vision_capable(model_id: str) -> bool:
    lowered = model_id.lower()
    return any(hint in lowered for hint in VISION_HINTS)


class OpenAICompatibleProvider(AIProvider):
    id = "openai_compatible"
    display_name = "OpenAI-compatible"

    def __init__(
        self,
        *,
        provider_id: str,
        display_name: str,
        base_url: str,
        api_key: str,
        group: str,
        static_models: Optional[list[str]] = None,
        supports_image_generation: bool = False,
    ) -> None:
        self.id = provider_id
        self.display_name = display_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.group = group
        self.static_models = static_models or []
        self.supports_image_generation = supports_image_generation

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def is_configured(self) -> bool:
        # A custom/local endpoint may legitimately need no API key (e.g. a
        # local vLLM server), so "configured" means "has a base URL", not
        # "has a key".
        return bool(self.base_url)

    async def list_models(self) -> list[ModelInfo]:
        if not await self.is_configured():
            return []

        models: list[ModelInfo] = []
        try:
            async with httpx.AsyncClient(timeout=config.PROVIDER_CONNECT_TIMEOUT) as client:
                response = await client.get(f"{self.base_url}/models", headers=self._headers())
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("data", []):
                        model_id = item.get("id")
                        if not model_id:
                            continue
                        models.append(self._to_model_info(model_id))
        except Exception:
            pass  # fall through to static fallback below

        if not models and self.static_models:
            models = [self._to_model_info(m) for m in self.static_models]

        return models

    def _to_model_info(self, model_id: str) -> ModelInfo:
        return ModelInfo(
            id=f"{self.id}:{model_id}",
            name=model_id,
            provider=self.id,
            group=self.group,
            description=f"{self.display_name} model",
            capabilities=Capabilities(
                chat=True,
                streaming=True,
                vision=_looks_vision_capable(model_id),
                documents=True,
                tools=True,
                web_search=False,
                image_generation=self.supports_image_generation and "image" in model_id.lower(),
            ),
        )

    async def stream_chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: Optional[str] = None,
        images: Optional[list[dict[str, Any]]] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        if not await self.is_configured():
            raise ProviderError(f"{self.display_name} is not configured (missing API key or base URL).", kind="provider_unavailable")

        full_messages: list[dict[str, Any]] = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(self._inject_images(messages, images))

        payload = {
            "model": model,
            "messages": full_messages,
            "stream": True,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        last_error: Optional[Exception] = None
        for attempt in range(config.PROVIDER_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(config.PROVIDER_REQUEST_TIMEOUT, connect=config.PROVIDER_CONNECT_TIMEOUT)) as client:
                    async with client.stream("POST", f"{self.base_url}/chat/completions", headers=self._headers(), json=payload) as response:
                        if response.status_code == 401:
                            raise ProviderError(f"{self.display_name}: invalid API key.", kind="invalid_api_key", status_code=401)
                        if response.status_code == 429:
                            raise ProviderError(f"{self.display_name}: rate limit exceeded.", kind="rate_limited", status_code=429)
                        if response.status_code >= 500:
                            raise ProviderError(f"{self.display_name}: provider unavailable.", kind="provider_unavailable", status_code=response.status_code)
                        if response.status_code != 200:
                            error_text = (await response.aread()).decode(errors="replace")
                            raise ProviderError(f"{self.display_name}: {error_text[:400]}", kind="unknown", status_code=response.status_code)

                        async for line in response.aiter_lines():
                            if not line or not line.startswith("data:"):
                                continue
                            data = line[5:].strip()
                            if data == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                            except json.JSONDecodeError:
                                continue
                            choices = chunk.get("choices", [])
                            if not choices:
                                continue
                            delta = choices[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield {"type": "token", "content": content}
                        return
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                last_error = ProviderError(f"{self.display_name}: could not connect ({exc}).", kind="provider_unavailable")
            except httpx.ReadTimeout as exc:
                last_error = ProviderError(f"{self.display_name}: request timed out.", kind="timeout")
            except ProviderError as exc:
                if exc.kind in ("invalid_api_key",):
                    raise  # never retry auth failures
                last_error = exc
            if attempt < config.PROVIDER_MAX_RETRIES:
                continue
        if last_error:
            raise last_error

    def _inject_images(self, messages: list[dict[str, Any]], images: Optional[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        if not images:
            return messages
        out = [dict(m) for m in messages]
        for i in range(len(out) - 1, -1, -1):
            if out[i].get("role") == "user":
                content_blocks: list[dict[str, Any]] = [{"type": "text", "text": out[i].get("content", "")}]
                for img in images:
                    content_blocks.append(
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{img['mime_type']};base64,{img['data_base64']}"},
                        }
                    )
                out[i]["content"] = content_blocks
                break
        return out
