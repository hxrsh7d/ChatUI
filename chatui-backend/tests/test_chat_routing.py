"""
Tests for POST /api/chat.

These deliberately stick to paths that never require a real provider
network call (unconfigured-provider errors, bad input, unknown model) --
see tests/test_rag_integration.py for a real end-to-end RAG retrieval test
that also goes through this endpoint's document-context injection.
"""

import json

import config
import main
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "ACCESS_TOKEN", "")
    return TestClient(main.app)


def _sse_events(response) -> list[dict]:
    events = []
    for line in response.iter_lines():
        if isinstance(line, bytes):
            line = line.decode()
        if line.startswith("data:"):
            events.append(json.loads(line[len("data:") :].strip()))
    return events


def test_chat_missing_messages_returns_error_event(client):
    res = client.post("/api/chat", json={"model": "openai:gpt-4o-mini", "messages": []})
    events = _sse_events(res)
    assert any(e["type"] == "error" for e in events)
    assert not any(e["type"] == "token" for e in events)


def test_chat_unconfigured_openai_returns_clear_error(client):
    res = client.post(
        "/api/chat",
        json={"model": "openai:gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]},
    )
    events = _sse_events(res)
    errors = [e for e in events if e["type"] == "error"]
    assert errors
    assert "not configured" in errors[0]["message"].lower()


def test_chat_unconfigured_anthropic_returns_clear_error(client):
    res = client.post(
        "/api/chat",
        json={"model": "anthropic:claude-sonnet-5", "messages": [{"role": "user", "content": "hi"}]},
    )
    events = _sse_events(res)
    errors = [e for e in events if e["type"] == "error"]
    assert errors
    assert "not configured" in errors[0]["message"].lower()


def test_chat_unknown_provider_prefix_returns_error(client):
    res = client.post(
        "/api/chat",
        json={"model": "nonexistent:some-model", "messages": [{"role": "user", "content": "hi"}]},
    )
    events = _sse_events(res)
    assert any(e["type"] == "error" for e in events)


def test_chat_image_generation_unconfigured_returns_clear_error(client):
    res = client.post(
        "/api/chat",
        json={
            "model": "openai:gpt-4o-mini",
            "messages": [{"role": "user", "content": "a cat wearing a hat"}],
            "imageGeneration": True,
        },
    )
    events = _sse_events(res)
    errors = [e for e in events if e["type"] == "error"]
    assert errors
    assert "image generation" in errors[0]["message"].lower()


def test_chat_web_search_unconfigured_returns_clear_error(client):
    res = client.post(
        "/api/chat",
        json={
            "model": "openai:gpt-4o-mini",
            "messages": [{"role": "user", "content": "what happened in the news today"}],
            "webSearch": True,
        },
    )
    events = _sse_events(res)
    errors = [e for e in events if e["type"] == "error"]
    assert errors
    assert "web search" in errors[0]["message"].lower()


def test_chat_local_model_without_llama_server_returns_error(client):
    # No llama-server running in the test environment -> bare (unprefixed)
    # model id routes to the local provider, which should fail clearly
    # rather than hang.
    res = client.post(
        "/api/chat",
        json={"model": "some-model.gguf", "messages": [{"role": "user", "content": "hi"}]},
    )
    events = _sse_events(res)
    assert any(e["type"] == "error" for e in events)


def test_chat_rate_limit_engages_after_too_many_requests(client, monkeypatch):
    import main as main_module

    limiter = main_module.RateLimiter(max_requests=2, window_seconds=60)
    monkeypatch.setattr(main_module, "chat_limiter", limiter)
    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)

    for _ in range(2):
        res = client.post(
            "/api/chat", json={"model": "openai:gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]}
        )
        assert res.status_code == 200

    res = client.post(
        "/api/chat", json={"model": "openai:gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]}
    )
    assert res.status_code == 200  # still 200 (SSE stream), rate-limit is signalled via the SSE error event
    events = _sse_events(res)
    errors = [e for e in events if e["type"] == "error"]
    assert errors
    assert "too many" in errors[0]["message"].lower()
