"""Tests for the ACCESS_TOKEN enforcement middleware in main.py."""

import config
import main
from fastapi.testclient import TestClient


def test_open_when_no_token_configured(monkeypatch):
    monkeypatch.setattr(config, "ACCESS_TOKEN", "")
    client = TestClient(main.app)
    assert client.get("/health").status_code == 200


def test_blocks_request_without_token_when_configured(monkeypatch):
    monkeypatch.setattr(config, "ACCESS_TOKEN", "secret123")
    client = TestClient(main.app)
    assert client.get("/health").status_code == 401


def test_allows_request_with_correct_token(monkeypatch):
    monkeypatch.setattr(config, "ACCESS_TOKEN", "secret123")
    client = TestClient(main.app)
    res = client.get("/health", headers={"Authorization": "Bearer secret123"})
    assert res.status_code == 200


def test_rejects_wrong_token(monkeypatch):
    monkeypatch.setattr(config, "ACCESS_TOKEN", "secret123")
    client = TestClient(main.app)
    res = client.get("/health", headers={"Authorization": "Bearer wrong-token"})
    assert res.status_code == 401


def test_rejects_malformed_authorization_header(monkeypatch):
    monkeypatch.setattr(config, "ACCESS_TOKEN", "secret123")
    client = TestClient(main.app)
    res = client.get("/health", headers={"Authorization": "secret123"})  # missing "Bearer " prefix
    assert res.status_code == 401


def test_root_liveness_never_requires_token(monkeypatch):
    monkeypatch.setattr(config, "ACCESS_TOKEN", "secret123")
    client = TestClient(main.app)
    assert client.get("/").status_code == 200


def test_v1_models_is_protected(monkeypatch):
    monkeypatch.setattr(config, "ACCESS_TOKEN", "secret123")
    client = TestClient(main.app)
    assert client.get("/v1/models").status_code == 401


def test_api_providers_is_protected(monkeypatch):
    monkeypatch.setattr(config, "ACCESS_TOKEN", "secret123")
    client = TestClient(main.app)
    assert client.get("/api/providers").status_code == 401
