"""Tests for providers/registry.py -- the model-id-to-provider router."""

import config
from providers.base import ProviderError
from providers.registry import ProviderRegistry

import pytest


def test_resolve_bare_filename_routes_to_local():
    reg = ProviderRegistry()
    provider, model_id = reg.resolve("some-model.gguf")
    assert provider is reg.local
    assert model_id == "some-model.gguf"


def test_resolve_prefixed_model_routes_to_named_provider():
    reg = ProviderRegistry()

    provider, model_id = reg.resolve("openai:gpt-4o-mini")
    assert provider is reg.openai
    assert model_id == "gpt-4o-mini"

    provider, model_id = reg.resolve("anthropic:claude-sonnet-5")
    assert provider is reg.anthropic
    assert model_id == "claude-sonnet-5"

    provider, model_id = reg.resolve("google:gemini-2.0-flash")
    assert provider is reg.google
    assert model_id == "gemini-2.0-flash"

    provider, model_id = reg.resolve("groq:llama-3.3-70b-versatile")
    assert provider is reg.groq
    assert model_id == "llama-3.3-70b-versatile"


def test_resolve_unknown_provider_raises():
    reg = ProviderRegistry()
    with pytest.raises(ProviderError):
        reg.resolve("nonexistent-provider:some-model")


def test_resolve_empty_model_raises():
    reg = ProviderRegistry()
    with pytest.raises(ProviderError):
        reg.resolve("")


def test_resolve_custom_provider_two_part_prefix(monkeypatch):
    monkeypatch.setattr(
        config,
        "CUSTOM_OPENAI_COMPATIBLE_PROVIDERS",
        [{"id": "myvllm", "name": "My vLLM", "base_url": "http://localhost:9000/v1", "api_key": "", "model": "llama-3-70b"}],
    )
    reg = ProviderRegistry()
    provider, model_id = reg.resolve("custom:myvllm:llama-3-70b")
    assert provider.id == "custom:myvllm"
    assert model_id == "llama-3-70b"


def test_resolve_unknown_custom_slug_raises(monkeypatch):
    monkeypatch.setattr(config, "CUSTOM_OPENAI_COMPATIBLE_PROVIDERS", [])
    reg = ProviderRegistry()
    with pytest.raises(ProviderError):
        reg.resolve("custom:doesnotexist:some-model")


def test_add_custom_provider_is_immediately_usable(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    reg = ProviderRegistry()
    provider_id = reg.add_custom_provider(name="My Server", base_url="http://localhost:9000/v1", api_key="", model="llama-3")

    assert provider_id == "custom:my-server"
    assert reg.get(provider_id) is not None
    provider, model_id = reg.resolve(f"{provider_id}:llama-3")
    assert provider.id == provider_id
    assert model_id == "llama-3"


def test_add_custom_provider_persists_across_new_registry_instances(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    reg1 = ProviderRegistry()
    reg1.add_custom_provider(name="My Server", base_url="http://localhost:9000/v1", api_key="secret", model="llama-3")

    reg2 = ProviderRegistry()  # simulates a fresh backend restart
    assert reg2.get("custom:my-server") is not None
    listed = reg2.list_custom_providers()
    assert any(p["id"] == "custom:my-server" for p in listed)
    # api_key must never appear in listing metadata
    assert all("api_key" not in p for p in listed)


def test_remove_custom_provider_removes_it_and_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    reg = ProviderRegistry()
    provider_id = reg.add_custom_provider(name="Temp Server", base_url="http://localhost:9001/v1", api_key="", model="m")

    removed = reg.remove_custom_provider(provider_id)
    assert removed is True
    assert reg.get(provider_id) is None

    reg2 = ProviderRegistry()
    assert reg2.get(provider_id) is None


def test_remove_unknown_custom_provider_returns_false(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    reg = ProviderRegistry()
    assert reg.remove_custom_provider("custom:does-not-exist") is False


def test_env_configured_custom_provider_cannot_be_removed_via_api_method(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(
        config,
        "CUSTOM_OPENAI_COMPATIBLE_PROVIDERS",
        [{"id": "envserver", "name": "Env Server", "base_url": "http://localhost:9002/v1", "api_key": "", "model": "m"}],
    )
    reg = ProviderRegistry()
    assert reg.remove_custom_provider("custom:envserver") is False
    assert reg.get("custom:envserver") is not None


def test_duplicate_provider_names_get_distinct_slugs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    reg = ProviderRegistry()
    id1 = reg.add_custom_provider(name="My Server", base_url="http://localhost:9000/v1", api_key="", model="m")
    id2 = reg.add_custom_provider(name="My Server", base_url="http://localhost:9003/v1", api_key="", model="m")
    assert id1 != id2


@pytest.mark.asyncio
async def test_openai_not_configured_when_no_api_key():
    reg = ProviderRegistry()
    assert await reg.openai.is_configured() is False


@pytest.mark.asyncio
async def test_list_all_models_never_raises_even_with_no_providers_configured():
    reg = ProviderRegistry()
    models = await reg.list_all_models()
    assert isinstance(models, list)
