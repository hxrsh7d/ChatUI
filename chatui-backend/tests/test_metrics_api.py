"""Tests for GET /api/metrics -- protected like everything else, and
actually populated by real request traffic."""

import config
import main
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "ACCESS_TOKEN", "")
    return TestClient(main.app)


def test_metrics_endpoint_protected_when_access_token_set(monkeypatch):
    monkeypatch.setattr(config, "ACCESS_TOKEN", "secret123")
    client = TestClient(main.app)
    assert client.get("/api/metrics").status_code == 401


def test_metrics_endpoint_returns_expected_shape(client):
    res = client.get("/api/metrics")
    assert res.status_code == 200
    body = res.json()
    assert "uptime_seconds" in body
    assert "requests" in body
    assert "providers" in body


def test_metrics_reflect_real_request_traffic(client):
    client.get("/health")
    client.get("/health")

    res = client.get("/api/metrics")
    body = res.json()
    assert body["requests"]["GET /health"]["count"] >= 2


def test_metrics_track_provider_call_after_unconfigured_chat_error(client):
    client.post(
        "/api/chat",
        json={"model": "openai:gpt-4o-mini", "messages": [{"role": "user", "content": "hi"}]},
    )
    res = client.get("/api/metrics")
    body = res.json()
    assert "openai" in body["providers"]
    assert body["providers"]["openai"]["errors"] >= 1
