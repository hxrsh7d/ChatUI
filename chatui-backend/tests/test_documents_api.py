"""Tests for POST /api/documents (upload) and DELETE /api/documents/{id}."""

import config
import main
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "ACCESS_TOKEN", "")
    return TestClient(main.app)


def test_upload_txt_document(client):
    res = client.post(
        "/api/documents",
        files={"file": ("notes.txt", b"The launch date is March 3rd, 2027.", "text/plain")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ready"
    assert body["name"] == "notes.txt"
    assert "id" in body


def test_upload_rejects_unsupported_extension(client):
    res = client.post(
        "/api/documents",
        files={"file": ("app.exe", b"not really an exe but wrong extension", "application/octet-stream")},
    )
    assert res.status_code == 415


def test_upload_rejects_invalid_utf8_txt(client):
    res = client.post(
        "/api/documents",
        files={"file": ("broken.txt", bytes([0xFF, 0xFE, 0x00]), "text/plain")},
    )
    assert res.status_code == 422


def test_upload_rejects_empty_file(client):
    res = client.post(
        "/api/documents",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert res.status_code == 400


def test_upload_strips_directory_components_from_filename(client):
    res = client.post(
        "/api/documents",
        files={"file": ("../../evil/../path.txt", b"hello", "text/plain")},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "path.txt"


def test_upload_png_image_is_accepted_and_marked_ready(client, tiny_png_bytes):
    res = client.post(
        "/api/documents",
        files={"file": ("tiny.png", tiny_png_bytes, "image/png")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["type"] == "image/png"
    assert body["status"] == "ready"


def test_upload_rejects_file_with_image_extension_but_bogus_content(client):
    res = client.post(
        "/api/documents",
        files={"file": ("fake.png", b"not actually a png", "image/png")},
    )
    assert res.status_code == 422


def test_upload_rate_limit_engages_after_too_many_requests(client, monkeypatch):
    import api.documents as documents_api

    limiter = documents_api.RateLimiter(max_requests=2, window_seconds=60)
    monkeypatch.setattr(documents_api, "upload_limiter", limiter)
    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", True)

    for _ in range(2):
        res = client.post("/api/documents", files={"file": ("a.txt", b"hello", "text/plain")})
        assert res.status_code == 200

    res = client.post("/api/documents", files={"file": ("b.txt", b"hello", "text/plain")})
    assert res.status_code == 429
    assert "Retry-After" in res.headers


def test_upload_rate_limit_disabled_allows_unlimited_requests(client, monkeypatch):
    import api.documents as documents_api

    limiter = documents_api.RateLimiter(max_requests=1, window_seconds=60)
    monkeypatch.setattr(documents_api, "upload_limiter", limiter)
    monkeypatch.setattr(config, "RATE_LIMIT_ENABLED", False)

    for _ in range(3):
        res = client.post("/api/documents", files={"file": ("a.txt", b"hello", "text/plain")})
        assert res.status_code == 200


def test_delete_document_then_delete_again_is_404(client):
    upload = client.post(
        "/api/documents",
        files={"file": ("temp.txt", b"Temporary note.", "text/plain")},
    )
    doc_id = upload.json()["id"]

    res = client.delete(f"/api/documents/{doc_id}")
    assert res.status_code == 200

    res2 = client.delete(f"/api/documents/{doc_id}")
    assert res2.status_code == 404


def test_delete_unknown_document_is_404(client):
    res = client.delete("/api/documents/does-not-exist")
    assert res.status_code == 404
