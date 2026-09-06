"""Tests for GET/POST /api/providers/custom and DELETE /api/providers/custom/{id}."""

import config
import main
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ACCESS_TOKEN", "")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    return TestClient(main.app)


def test_list_custom_providers_starts_empty(client):
    res = client.get("/api/providers/custom")
    assert res.status_code == 200
    assert res.json() == {"providers": []}


def test_add_custom_provider_success(client):
    res = client.post(
        "/api/providers/custom",
        json={"name": "My vLLM box", "base_url": "http://localhost:8001/v1", "api_key": "sk-test", "model": "llama-3-70b"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == "custom:my-vllm-box"
    assert "api_key" not in body


def test_added_provider_appears_in_listing_without_api_key(client):
    client.post(
        "/api/providers/custom",
        json={"name": "My vLLM box", "base_url": "http://localhost:8001/v1", "api_key": "sk-test", "model": "llama-3-70b"},
    )
    res = client.get("/api/providers/custom")
    providers = res.json()["providers"]
    assert len(providers) == 1
    assert providers[0]["name"] == "My vLLM box"
    assert "api_key" not in providers[0]


def test_added_provider_appears_in_general_providers_listing(client):
    client.post(
        "/api/providers/custom",
        json={"name": "My vLLM box", "base_url": "http://localhost:8001/v1", "api_key": "", "model": "llama-3-70b"},
    )
    res = client.get("/api/providers")
    ids = [p["id"] for p in res.json()["ai_providers"]]
    assert "custom:my-vllm-box" in ids


def test_add_custom_provider_missing_name_rejected(client):
    res = client.post("/api/providers/custom", json={"base_url": "http://localhost:8001/v1"})
    assert res.status_code == 400


def test_add_custom_provider_missing_base_url_rejected(client):
    res = client.post("/api/providers/custom", json={"name": "Test"})
    assert res.status_code == 400


def test_add_custom_provider_invalid_url_rejected(client):
    res = client.post("/api/providers/custom", json={"name": "Test", "base_url": "not-a-url"})
    assert res.status_code == 400


def test_delete_custom_provider_success(client):
    add_res = client.post(
        "/api/providers/custom",
        json={"name": "Temp", "base_url": "http://localhost:8002/v1", "api_key": "", "model": "m"},
    )
    provider_id = add_res.json()["id"]

    del_res = client.delete(f"/api/providers/custom/{provider_id}")
    assert del_res.status_code == 200

    res = client.get("/api/providers/custom")
    assert res.json()["providers"] == []


def test_delete_unknown_custom_provider_is_404(client):
    res = client.delete("/api/providers/custom/custom:does-not-exist")
    assert res.status_code == 404


def test_custom_provider_endpoints_protected_when_access_token_set(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "ACCESS_TOKEN", "secret123")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    client = TestClient(main.app)
    assert client.get("/api/providers/custom").status_code == 401
    assert client.post("/api/providers/custom", json={"name": "x", "base_url": "http://x/v1"}).status_code == 401
