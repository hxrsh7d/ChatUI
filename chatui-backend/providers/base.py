"""
Provider abstraction.

Every AI backend (local llama.cpp, OpenAI, Anthropic, Google, Groq, or an
arbitrary OpenAI-compatible endpoint) implements the `AIProvider` interface
below. The rest of the application (chat routing, model discovery,
capability reporting) only talks to this interface, never to a specific
vendor SDK/API directly. This is what makes the gateway "provider-agnostic":
new vendors can be added by writing a new adapter, not by touching the
chat endpoint or the frontend.

Streaming contract
-------------------
`stream_chat` is an async generator that yields plain dicts. These dicts
are the SAME shape the frontend's SSE parser (see app/src/services/api.ts)
already understands:

    {"type": "token", "content": "..."}
    {"type": "search_status", "status": "..."}
    {"type": "citations", "citations": [...]}
    {"type": "image", "image": {...}}
    {"type": "error", "message": "..."}
    {"type": "done"}

Providers should NOT yield "done" themselves unless they need to end the
stream early on error; the gateway (api/chat.py) appends the terminal
"done" event once the provider generator is exhausted successfully.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Optional


@dataclass
class Capabilities:
    chat: bool = True
    streaming: bool = True
    vision: bool = False
    documents: bool = True  # RAG context injection works for any text model
    tools: bool = False
    web_search: bool = False
    image_generation: bool = False

    def to_dict(self) -> dict:
        return {
            "chat": self.chat,
            "streaming": self.streaming,
            "vision": self.vision,
            "documents": self.documents,
            "tools": self.tools,
            "web_search": self.web_search,
            "image_generation": self.image_generation,
        }


@dataclass
class ModelInfo:
    id: str  # globally unique, e.g. "openai:gpt-4o-mini" or a raw gguf filename for local models
    name: str
    provider: str
    group: str
    description: str = ""
    context_length: Optional[int] = None
    capabilities: Capabilities = field(default_factory=Capabilities)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "group": self.group,
            "description": self.description,
            "context_length": self.context_length,
            "capabilities": self.capabilities.to_dict(),
        }


class ProviderError(Exception):
    """Normalized provider error. `kind` is one of the categories listed
    in the project brief (invalid_api_key, rate_limited, model_unavailable,
    provider_unavailable, timeout, context_too_large, unsupported, unknown).
    """

    def __init__(self, message: str, kind: str = "unknown", status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.kind = kind
        self.status_code = status_code


class AIProvider(ABC):
    """Base class every provider adapter implements."""

    id: str = "base"
    display_name: str = "Base Provider"

    @abstractmethod
    async def is_configured(self) -> bool:
        """Whether this provider has the credentials/config it needs."""

    @abstractmethod
    async def list_models(self) -> list[ModelInfo]:
        """Return the models this provider currently exposes. Must reflect
        REAL availability -- never invent models that aren't actually
        callable."""

    @abstractmethod
    def stream_chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        *,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system: Optional[str] = None,
        images: Optional[list[dict[str, Any]]] = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream a chat completion. `messages` is the normalized
        [{"role": "user"|"assistant", "content": "..."}] format. `images`
        (if given) is a list of {"mime_type": ..., "data_base64": ...}
        attached to the LATEST user turn, only sent if the model supports
        vision.
        """

    async def test_connection(self) -> dict[str, Any]:
        """Lightweight connectivity check used by POST /api/providers/test.
        Default implementation just tries to list models."""
        try:
            models = await self.list_models()
            return {"ok": True, "models": len(models)}
        except ProviderError as exc:
            return {"ok": False, "error": exc.message, "kind": exc.kind}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc), "kind": "unknown"}
