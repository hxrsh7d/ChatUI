"""Tests for metrics.py."""

from metrics import Metrics, normalize_path


def test_normalize_path_collapses_uuid_segments():
    assert normalize_path("/api/documents/3fa85f64-5717-4562-b3fc-2c963f66afa6") == "/api/documents/{id}"


def test_normalize_path_leaves_short_static_segments_alone():
    assert normalize_path("/api/providers") == "/api/providers"
    assert normalize_path("/health") == "/health"


def test_record_request_tracks_count_and_errors():
    m = Metrics()
    m.record_request("GET", "/health", 200, 0.01)
    m.record_request("GET", "/health", 200, 0.02)
    m.record_request("GET", "/health", 500, 0.03)

    snapshot = m.snapshot()
    stat = snapshot["requests"]["GET /health"]
    assert stat["count"] == 3
    assert stat["errors"] == 1


def test_record_request_normalizes_dynamic_segments_into_one_key():
    m = Metrics()
    m.record_request("DELETE", "/api/documents/11111111-1111-1111-1111-111111111111", 200, 0.01)
    m.record_request("DELETE", "/api/documents/22222222-2222-2222-2222-222222222222", 200, 0.01)

    snapshot = m.snapshot()
    assert snapshot["requests"]["DELETE /api/documents/{id}"]["count"] == 2
    assert len(snapshot["requests"]) == 1


def test_record_provider_call_tracks_success_and_errors_separately():
    m = Metrics()
    m.record_provider_call("openai", 0.5, is_error=False)
    m.record_provider_call("openai", 1.5, is_error=True)

    stat = m.snapshot()["providers"]["openai"]
    assert stat["count"] == 2
    assert stat["errors"] == 1
    assert stat["max_ms"] == 1500.0


def test_reset_clears_everything():
    m = Metrics()
    m.record_request("GET", "/health", 200, 0.01)
    m.record_provider_call("openai", 0.5, is_error=False)
    m.reset()

    snapshot = m.snapshot()
    assert snapshot["requests"] == {}
    assert snapshot["providers"] == {}
