"""
Persists custom OpenAI-compatible providers added at runtime through the
Settings UI, so they survive a backend restart.

Kept separate from CUSTOM_OPENAI_COMPATIBLE_PROVIDERS (the env-var-
configured list in config.py): that one is code/ops-configured and
read-only from the API's perspective; this one is user-configured through
the UI and is what POST/DELETE /api/providers/custom read and write.
Both end up registered in the same provider registry at runtime (see
providers/registry.py) and are otherwise indistinguishable to callers.

Stored as plain JSON in the data dir (gitignored). API keys are stored in
plaintext here, the same as they would be in a .env file -- this is
appropriate for a personal/small-group self-hosted instance, not a
multi-tenant SaaS; see the project README for the broader threat model
(ACCESS_TOKEN gates the whole instance, not per-provider).
"""

from __future__ import annotations

import json
from typing import Any

import config


def _path():
    # Computed on every call (not a module-level constant) so tests can
    # redirect config.DATA_DIR via monkeypatch and actually have it take
    # effect -- a fixed constant would freeze in whatever DATA_DIR was at
    # import time.
    return config.DATA_DIR / "custom_providers.json"


def load() -> list[dict[str, Any]]:
    path = _path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save(providers: list[dict[str, Any]]) -> None:
    _path().write_text(json.dumps(providers, indent=2))
