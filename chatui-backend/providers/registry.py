"""
Provider registry.

Owns one instance of each configured provider and routes a model id to the
right one.

Model id scheme
----------------
Local llama.cpp models keep their RAW GGUF FILENAME as the id (no prefix),
exactly as the original single-file backend behaved -- this preserves
backward compatibility with anything (browser localStorage, bookmarked
requests) that already references a bare filename.

Every cloud/custom provider's models are prefixed as "<provider_id>:<model>",
e.g. "openai:gpt-4o-mini", "anthropic:claude-sonnet-5", "google:gemini-2.0-flash",
"groq:llama-3.3-70b-versatile", "custom:<slug>:<model>".

`resolve(model_id)` returns (provider, provider_model_id) so callers never
need to know the prefixing scheme themselves.
"""

from __future__ import annotations

import re
from typing import Any, Optional

import config
from logging_config import get_logger
from providers.anthropic import AnthropicProvider
from providers.base import AIProvider, ModelInfo, ProviderError
from providers.custom_store import load as load_custom_providers, save as save_custom_providers
from providers.google import GoogleProvider
from providers.groq import GroqProvider
from providers.llama_cpp import LlamaCppProvider
from providers.openai import OpenAIProvider
from providers.openai_compatible import OpenAICompatibleProvider

logger = get_logger("provider_registry")


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "custom"


class ProviderRegistry:
    def __init__(self) -> None:
        self.local = LlamaCppProvider()
        self.openai = OpenAIProvider()
        self.anthropic = AnthropicProvider()
        self.google = GoogleProvider()
        self.groq = GroqProvider()

        self.custom: dict[str, OpenAICompatibleProvider] = {}
        # Metadata for listing/management (GET /api/providers/custom) --
        # never includes api_key. "source" distinguishes providers
        # configured via the CUSTOM_OPENAI_COMPATIBLE_PROVIDERS env var
        # (code/ops-configured, read-only from the API) from ones added at
        # runtime through the Settings UI (deletable via the API, and
        # persisted to providers/custom_store.py so they survive restarts).
        self.custom_meta: dict[str, dict[str, Any]] = {}

        for entry in config.CUSTOM_OPENAI_COMPATIBLE_PROVIDERS:
            self._register_custom(entry, source="env")

        for entry in load_custom_providers():
            self._register_custom(entry, source="user")

        self._cloud_providers: dict[str, AIProvider] = {
            "openai": self.openai,
            "anthropic": self.anthropic,
            "google": self.google,
            "groq": self.groq,
            **self.custom,
        }

    def _register_custom(self, entry: dict[str, Any], *, source: str) -> str:
        name = entry.get("name") or entry.get("id") or "custom"
        # entry["id"], if present, is a bare slug (never "custom:"-prefixed
        # -- see add_custom_provider, which is the only writer of this
        # field for persisted entries).
        base_slug = str(entry.get("id") or name)
        slug = _slugify(base_slug)
        provider_id = f"custom:{slug}"
        # Guard against two entries slugifying to the same id (e.g. two
        # providers both named "My Server").
        suffix = 2
        while provider_id in self.custom:
            provider_id = f"custom:{slug}-{suffix}"
            suffix += 1

        self.custom[provider_id] = OpenAICompatibleProvider(
            provider_id=provider_id,
            display_name=name,
            base_url=entry.get("base_url", ""),
            api_key=entry.get("api_key", ""),
            group=name,
            static_models=[entry["model"]] if entry.get("model") else [],
        )
        self.custom_meta[provider_id] = {
            "id": provider_id,
            "name": name,
            "base_url": entry.get("base_url", ""),
            "model": entry.get("model", ""),
            "source": source,
        }
        return provider_id

    def add_custom_provider(self, *, name: str, base_url: str, api_key: str, model: str) -> str:
        """Registers a new custom provider immediately (usable in the very
        next request) and persists it so it survives a restart. Returns
        the new provider's id."""
        entry: dict[str, Any] = {"name": name, "base_url": base_url, "api_key": api_key, "model": model}
        provider_id = self._register_custom(entry, source="user")
        self._cloud_providers[provider_id] = self.custom[provider_id]

        # Persist the bare slug (not the "custom:"-prefixed id) as "id" so
        # reloading this entry on next startup regenerates the SAME
        # provider_id via _register_custom above, rather than double-
        # prefixing it.
        entry["id"] = provider_id.removeprefix("custom:")
        persisted = load_custom_providers()
        persisted.append(entry)
        save_custom_providers(persisted)

        logger.info(f"added custom provider {provider_id} ({base_url})")
        return provider_id

    def remove_custom_provider(self, provider_id: str) -> bool:
        """Returns False if the id doesn't exist or isn't a user-added
        (as opposed to env-configured) custom provider -- env-configured
        ones are only removable by editing .env, since deleting them here
        would just be undone on the next restart."""
        meta = self.custom_meta.get(provider_id)
        if meta is None or meta["source"] != "user":
            return False

        del self.custom[provider_id]
        del self.custom_meta[provider_id]
        del self._cloud_providers[provider_id]

        target_slug = provider_id.removeprefix("custom:")
        persisted = [p for p in load_custom_providers() if p.get("id") != target_slug]
        save_custom_providers(persisted)

        logger.info(f"removed custom provider {provider_id}")
        return True

    def list_custom_providers(self) -> list[dict[str, Any]]:
        return list(self.custom_meta.values())

    def _reset_user_added_custom_providers_for_tests(self) -> None:
        """Test-only hook: removes any custom providers added at runtime
        (source == 'user') from in-memory state, without touching
        env-configured ones or the on-disk store. The shared `registry`
        singleton lives for the whole test session, so without this,
        providers added by one test would leak into the next."""
        for provider_id in [pid for pid, meta in self.custom_meta.items() if meta["source"] == "user"]:
            self.custom.pop(provider_id, None)
            self.custom_meta.pop(provider_id, None)
            self._cloud_providers.pop(provider_id, None)

    def all_providers(self) -> list[AIProvider]:
        return [self.local, *self._cloud_providers.values()]

    def get(self, provider_id: str) -> Optional[AIProvider]:
        if provider_id == "local":
            return self.local
        return self._cloud_providers.get(provider_id)

    async def list_all_models(self) -> list[ModelInfo]:
        models: list[ModelInfo] = []
        for provider in self.all_providers():
            try:
                if await provider.is_configured():
                    models.extend(await provider.list_models())
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"{getattr(provider, 'id', provider)} discovery failed: {exc}")
        return models

    def resolve(self, model_id: str) -> tuple[AIProvider, str]:
        """Given a (possibly prefixed) model id, return the provider that
        should serve it and the model id AS THAT PROVIDER expects it."""
        if not model_id:
            raise ProviderError("No model specified.", kind="model_unavailable")

        if ":" not in model_id:
            # Backward-compatible: bare filename => local llama.cpp model.
            return self.local, model_id

        provider_id, _, provider_model_id = model_id.partition(":")
        # Custom providers use a two-part prefix: "custom:<slug>:<model>"
        if provider_id == "custom":
            slug, _, real_model = provider_model_id.partition(":")
            full_provider_id = f"custom:{slug}"
            provider = self._cloud_providers.get(full_provider_id)
            if provider is None:
                raise ProviderError(f"Unknown custom provider '{slug}'.", kind="provider_unavailable")
            return provider, real_model

        provider = self._cloud_providers.get(provider_id)
        if provider is None:
            raise ProviderError(f"Unknown provider '{provider_id}'.", kind="provider_unavailable")
        return provider, provider_model_id


registry = ProviderRegistry()
