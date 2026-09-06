"""Tests for rate_limit.py."""

from rate_limit import RateLimiter


def test_allows_requests_under_the_limit():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        allowed, retry_after = limiter.check("client-a")
        assert allowed is True
        assert retry_after == 0.0


def test_blocks_requests_over_the_limit():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        limiter.check("client-a")
    allowed, retry_after = limiter.check("client-a")
    assert allowed is False
    assert retry_after > 0


def test_different_clients_have_independent_limits():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    allowed_a, _ = limiter.check("client-a")
    allowed_b, _ = limiter.check("client-b")
    assert allowed_a is True
    assert allowed_b is True


def test_old_hits_expire_out_of_the_window():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    limiter.check("client-a")
    blocked, _ = limiter.check("client-a")
    assert blocked is False

    # simulate the window having passed by manually rewinding recorded hits
    limiter._hits["client-a"][0] -= 61
    allowed, _ = limiter.check("client-a")
    assert allowed is True


def test_reset_clears_all_clients():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    limiter.check("client-a")
    limiter.reset()
    allowed, _ = limiter.check("client-a")
    assert allowed is True
