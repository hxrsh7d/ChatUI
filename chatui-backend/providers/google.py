"""
Google Gemini provider.

Uses the Generative Language API's streamGenerateContent endpoint (SSE via
?alt=sse). Kept intentionally minimal per the project brief ("do not
introduce unnecessary dependencies or architectural complexity just to add
Gemini") -- plain httpx, no google-generativeai SDK dependency.
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Optional

import httpx

import config
from providers.base import AIProvider, Capabilities, ModelInfo, ProviderError

STATIC_MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro"]


class GoogleProvider(AIProvider):
    id = "google"
    display_name = "Google Gemini"

    def __init__(self) -> None:
        self.api_key = config.GOOGLE_API_KEY
        self.base_url = config.GOOGLE_BASE_URL.rstrip("/")

    async def is_configured(self) -> bool:
        return bool(self.api_key)

    async def list_models(self) -> list[ModelInfo]:
        if not await self.is_configured():
            return []

        models: list[ModelInfo] = []
        try:
            async with httpx.AsyncClient(timeout=config.PROVIDER_CONNECT_TIMEOUT) as client:
                response = await client.get(f"{self.base_url}/v1beta/models", params={"key": self.api_key})
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("models", []):
                        name = item.get("name", "")  # e.g. "models/gemini-2.0-flash"
                        model_id = name.split("/")[-1] if name else None
                        methods = item.get("supportedGenerationMethods", [])
                        if model_id and "generateContent" in methods:
                            models.append(self._to_model_info(model_id, item.get("displayName", model_id)))
        except Exception:
            pass

        if not models:
            models = [self._to_model_info(m, m) for m in STATIC_MODELS]

        return models

    def _to_model_info(self, model_id: str, display_name: str) -> ModelInfo:
        return ModelInfo(
            id=f"google:{model_id}",
            name=display_name,
            provider="google",
            group="Google",
            description="Gemini model",
            capabilities=Capabilities(
                chat=True,
                streaming=True,
                vision=True,
                documents=True,
                tools=False,
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
            raise ProviderError("Google Gemini is not configured (missing GOOGLE_API_KEY).", kind="provider_unavailable")

        contents = self._to_gemini_contents(messages, images)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        url = f"{self.base_url}/v1beta/models/{model}:streamGenerateContent"

        last_error: Optional[Exception] = None
        for attempt in range(config.PROVIDER_MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(config.PROVIDER_REQUEST_TIMEOUT, connect=config.PROVIDER_CONNECT_TIMEOUT)
                ) as client:
                    async with client.stream(
                        "POST", url, params={"key": self.api_key, "alt": "sse"}, json=payload
                    ) as response:
                        if response.status_code == 401 or response.status_code == 403:
                            raise ProviderError("Google Gemini: invalid API key.", kind="invalid_api_key", status_code=response.status_code)
                        if response.status_code == 429:
                            raise ProviderError("Google Gemini: rate limit exceeded.", kind="rate_limited", status_code=429)
                        if response.status_code >= 500:
                            raise ProviderError("Google Gemini: provider unavailable.", kind="provider_unavailable", status_code=response.status_code)
                        if response.status_code != 200:
                            body = (await response.aread()).decode(errors="replace")
                            raise ProviderError(f"Google Gemini: {body[:400]}", kind="unknown", status_code=response.status_code)

                        async for line in response.aiter_lines():
                            if not line or not line.startswith("data:"):
                                continue
                            data = line[5:].strip()
                            if not data:
                                continue
                            try:
                                chunk = json.loads(data)
                            except json.JSONDecodeError:
                                continue
                            candidates = chunk.get("candidates", [])
                            if not candidates:
                                continue
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                text = part.get("text")
                                if text:
                                    yield {"type": "token", "content": text}
                        return
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                last_error = ProviderError(f"Google Gemini: could not connect ({exc}).", kind="provider_unavailable")
            except httpx.ReadTimeout:
                last_error = ProviderError("Google Gemini: request timed out.", kind="timeout")
            except ProviderError as exc:
                if exc.kind == "invalid_api_key":
                    raise
                last_error = exc
            if attempt < config.PROVIDER_MAX_RETRIES:
                continue
        if last_error:
            raise last_error

    @staticmethod
    def _to_gemini_contents(messages: list[dict[str, Any]], images: Optional[list[dict[str, Any]]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            role = m.get("role")
            if role not in ("user", "assistant"):
                continue
            gemini_role = "model" if role == "assistant" else "user"
            out.append({"role": gemini_role, "parts": [{"text": m.get("content", "")}]})

        if images:
            for i in range(len(out) - 1, -1, -1):
                if out[i]["role"] == "user":
                    for img in images:
                        out[i]["parts"].append(
                            {"inlineData": {"mimeType": img["mime_type"], "data": img["data_base64"]}}
                        )
                    break

        return out
