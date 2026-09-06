"""
Lightweight in-memory metrics.

No external dependency (no prometheus_client) per this project's stated
preference for minimal added infrastructure -- this tracks simple
counters/timers, good enough for a personal/small-group instance to
answer "is this slow" / "is this provider failing", not a full
observability stack. Exposed read-only via GET /api/metrics (behind
ACCESS_TOKEN like everything else, since latency/error patterns can hint
at usage). Resets on restart; does not persist or aggregate across
multiple backend processes.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from dataclasses import dataclass

_ID_SEGMENT_RE = re.compile(r"^[0-9a-fA-F-]{8,}$")


def normalize_path(path: str) -> str:
    """Collapses path segments that look like generated IDs (document
    UUIDs, etc.) to '{id}' so metrics don't grow one key per unique
    document/request forever."""
    parts = path.split("/")
    return "/".join(("{id}" if _ID_SEGMENT_RE.match(p) else p) for p in parts)


@dataclass
class _Stat:
    count: int = 0
    errors: int = 0
    total_seconds: float = 0.0
    max_seconds: float = 0.0

    def record(self, seconds: float, is_error: bool = False) -> None:
        self.count += 1
        if is_error:
            self.errors += 1
        self.total_seconds += seconds
        self.max_seconds = max(self.max_seconds, seconds)

    def to_dict(self) -> dict:
        avg = (self.total_seconds / self.count) if self.count else 0.0
        return {
            "count": self.count,
            "errors": self.errors,
            "avg_ms": round(avg * 1000, 1),
            "max_ms": round(self.max_seconds * 1000, 1),
        }


class Metrics:
    def __init__(self) -> None:
        self.started_at = time.time()
        self._requests: dict[str, _Stat] = defaultdict(_Stat)
        self._providers: dict[str, _Stat] = defaultdict(_Stat)

    def record_request(self, method: str, path: str, status_code: int, seconds: float) -> None:
        key = f"{method} {normalize_path(path)}"
        self._requests[key].record(seconds, is_error=status_code >= 400)

    def record_provider_call(self, provider_id: str, seconds: float, is_error: bool) -> None:
        self._providers[provider_id].record(seconds, is_error=is_error)

    def snapshot(self) -> dict:
        return {
            "uptime_seconds": round(time.time() - self.started_at, 1),
            "requests": {k: v.to_dict() for k, v in sorted(self._requests.items())},
            "providers": {k: v.to_dict() for k, v in sorted(self._providers.items())},
        }

    def reset(self) -> None:
        """Test hook."""
        self._requests.clear()
        self._providers.clear()
        self.started_at = time.time()


metrics = Metrics()
