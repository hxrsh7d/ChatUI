"""
Simple in-memory rate limiter.

Protects the expensive endpoints (chat completions, document uploads) from
a runaway client loop or a compromised browser burning through provider
API budget. This is a fixed-window counter per client IP -- intentionally
simple and in-memory only (resets on restart, does not coordinate across
multiple backend processes). That's an appropriate tradeoff for a
personal/small-group ChatUI instance; a multi-instance deployment would
need a shared store (e.g. Redis) instead.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str) -> tuple[bool, float]:
        """Records a hit for `key` if under the limit. Returns (allowed,
        retry_after_seconds) -- retry_after_seconds is 0 when allowed."""
        now = time.monotonic()
        hits = self._hits[key]

        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()

        if len(hits) >= self.max_requests:
            retry_after = self.window_seconds - (now - hits[0])
            return False, max(retry_after, 0.0)

        hits.append(now)
        return True, 0.0

    def reset(self) -> None:
        """Test hook: clear all recorded hits."""
        self._hits.clear()
