"""
Anthropic Claude provider.

Converts the gateway's normalized message format into Anthropic's Messages
API format (system prompt is a top-level field, not a message; content can
be plain text or a list of blocks for vision) and translates Anthropic's
SSE event stream (message_start / content_block_delta / message_stop) back
into the gateway's normalized {"type": "token", ...} events.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Optional

import httpx

import config
from providers.base import AIProvider, Capabilities, ModelInfo, ProviderError

# Fallback list used only if the live GET /v1/models call fails (e.g. no
# network to Anthropic yet, or the account can't list models). Never shown
# as "connected" unless is_configured() is true (API key present).
STATIC_MODELS = [
    ("claude-opus-4-8", "Claude Opus 4.8"),
    ("claude-sonnet-5", "Claude Sonnet 5"),
    ("claude-haiku-4-5-20251001", "Claude Haiku 4.5"),
]


class AnthropicProvider(AIProvider):
    id = "anthropic"
    display_name = "Anthropic"

    def __init__(self) -> None:
        self.api_key = config.ANTHROPIC_API_KEY
        self.base_url = config.ANTHROPIC_BASE_URL.rstrip("/")
        self.version = config.ANTHROPIC_VERSION

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": self.version,
            "content-type": "application/json",
        }

    async def is_configured(self) -> bool:
        return bool(self.api_key)

    async def list_models(self) -> list[ModelInfo]:
        if not await self.is_configured():
            return []

        models: list[ModelInfo] = []
        try:
            async with httpx.AsyncClient(timeout=config.PROVIDER_CONNECT_TIMEOUT) as client:
                response = await client.get(f"{self.base_url}/v1/models", headers=self._headers())
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("data", []):
                        model_id = item.get("id")
                        if not model_id:
                            continue
                        models.append(self._to_model_info(model_id, item.get("display_name", model_id)))
        except Exception:
            pass

        if not models:
            models = [self._to_model_info(mid, name) for mid, name in STATIC_MODELS]

        return models

    def _to_model_info(self, model_id: str, display_name: str) -> ModelInfo:
        return ModelInfo(
            id=f"anthropic:{model_id}",
            name=display_name,
            provider="anthropic",
            group="Anthropic",
            description="Claude model",
            capabilities=Capabilities(
                chat=True,
                streaming=True,
                vision=True,
                documents=True,
                tools=True,
                web_search=False,
                image_generation=False,
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
            raise ProviderError("Anthropic is not configured (missing ANTHROPIC_API_KEY).", kind="provider_unavailable")

        anthropic_messages = self._to_anthropic_messages(messages, images)

        payload: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if system:
            payload["system"] = system

        last_error: Optional[Exception] = None
        for attempt in range(config.PROVIDER_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(config.PROVIDER_REQUEST_TIMEOUT, connect=config.PROVIDER_CONNECT_TIMEOUT)
                ) as client:
                    async with client.stream("POST", f"{self.base_url}/v1/messages", headers=self._headers(), json=payload) as response:
                        if response.status_code == 401:
                            raise ProviderError("Anthropic: invalid API key.", kind="invalid_api_key", status_code=401)
                        if response.status_code == 429:
                            raise ProviderError("Anthropic: rate limit exceeded.", kind="rate_limited", status_code=429)
                        if response.status_code == 413 or response.status_code == 400:
                            body = (await response.aread()).decode(errors="replace")
                            if "context" in body.lower() or "too long" in body.lower() or "tokens" in body.lower():
                                raise ProviderError("Anthropic: request exceeds the model's context window.", kind="context_too_large", status_code=response.status_code)
                            raise ProviderError(f"Anthropic: {body[:400]}", kind="unknown", status_code=response.status_code)
                        if response.status_code >= 500:
                            raise ProviderError("Anthropic: provider unavailable.", kind="provider_unavailable", status_code=response.status_code)
                        if response.status_code != 200:
                            body = (await response.aread()).decode(errors="replace")
                            raise ProviderError(f"Anthropic: {body[:400]}", kind="unknown", status_code=response.status_code)

                        async for line in response.aiter_lines():
                            if not line or not line.startswith("data:"):
                                continue
                            data = line[5:].strip()
                            if not data:
                                continue
                            try:
                                event = json.loads(data)
                            except json.JSONDecodeError:
                                continue

                            event_type = event.get("type")
                            if event_type == "content_block_delta":
                                delta = event.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    text = delta.get("text")
                                    if text:
                                        yield {"type": "token", "content": text}
                            elif event_type == "error":
                                err = event.get("error", {})
                                raise ProviderError(err.get("message", "Anthropic stream error."), kind="unknown")
                        return
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                last_error = ProviderError(f"Anthropic: could not connect ({exc}).", kind="provider_unavailable")
            except httpx.ReadTimeout:
                last_error = ProviderError("Anthropic: request timed out.", kind="timeout")
            except ProviderError as exc:
                if exc.kind == "invalid_api_key":
                    raise
                last_error = exc
            if attempt < config.PROVIDER_MAX_RETRIES:
                continue
        if last_error:
            raise last_error

    @staticmethod
    def _to_anthropic_messages(messages: list[dict[str, Any]], images: Optional[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            role = m.get("role")
            if role not in ("user", "assistant"):
                continue  # system handled separately via the top-level `system` field
            out.append({"role": role, "content": m.get("content", "")})

        if images:
            for i in range(len(out) - 1, -1, -1):
                if out[i]["role"] == "user":
                    text = out[i]["content"] if isinstance(out[i]["content"], str) else ""
                    blocks: list[dict[str, Any]] = []
                    if text:
                        blocks.append({"type": "text", "text": text})
                    for img in images:
                        blocks.append(
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": img["mime_type"],
                                    "data": img["data_base64"],
                                },
                            }
                        )
                    out[i]["content"] = blocks
                    break

        return out
