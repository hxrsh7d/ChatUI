"""
Shared pytest setup.

Two things must happen BEFORE any app module (config, main, providers.*,
documents.*, ...) is imported anywhere in the test suite, or they won't
take effect:

1. Point the backend's data directory at a throwaway temp dir, so tests
   never read or write the real uploads folder / sqlite database.
2. Force every provider API key / search / image env var to an explicit
   empty string (not just "unset") so that IF a developer runs the test
   suite locally with a real chatui-backend/.env sitting on disk, that
   file's real secrets never leak into the test run and no test can
   accidentally place a live network call to a real provider. We set
   them to "" rather than deleting them because python-dotenv's
   load_dotenv() (called from main.py) does not override variables that
   already exist in the environment -- so an explicit "" wins over
   whatever a real .env file says, while a deleted/missing key would not.

Because conftest.py is always imported by pytest before any sibling test
module in the same directory, this module-level code is guaranteed to run
first.
"""

import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

_TEST_DATA_DIR = tempfile.mkdtemp(prefix="chatui-test-data-")
os.environ["CHATUI_DATA_DIR"] = _TEST_DATA_DIR

for _key in (
    "ACCESS_TOKEN",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GROQ_API_KEY",
    "BRAVE_API_KEY",
    "TAVILY_API_KEY",
    "SEARXNG_URL",
    "SEARCH_PROVIDER",
    "IMAGE_PROVIDER",
):
    os.environ[_key] = ""
os.environ["CUSTOM_OPENAI_COMPATIBLE_PROVIDERS"] = "[]"

import pytest  # noqa: E402


def make_tiny_png() -> bytes:
    """A minimal, structurally valid 1x1 PNG, built from stdlib only
    (struct + zlib) so tests don't need an image library dependency."""
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00" + bytes([255, 0, 0])
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


@pytest.fixture
def tiny_png_bytes() -> bytes:
    return make_tiny_png()


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """The chat/upload rate limiters are module-level singletons shared
    across the whole test session (mirroring how they run in the real
    app). Without resetting them between tests, hits accumulate and an
    unrelated later test can get spuriously 429'd. Runs automatically for
    every test."""
    import api.documents as documents_api
    import main as main_module

    main_module.chat_limiter.reset()
    documents_api.upload_limiter.reset()
    yield
    main_module.chat_limiter.reset()
    documents_api.upload_limiter.reset()


@pytest.fixture(autouse=True)
def _reset_metrics():
    """Same reasoning as _reset_rate_limiters: metrics is a module-level
    singleton shared across the whole test session."""
    from metrics import metrics

    metrics.reset()
    yield
    metrics.reset()


@pytest.fixture(autouse=True)
def _reset_custom_providers():
    """Same reasoning again: providers.registry.registry is a module-level
    singleton shared across the whole test session, so custom providers
    added via POST /api/providers/custom in one test would otherwise leak
    into every test after it."""
    from providers.registry import registry

    registry._reset_user_added_custom_providers_for_tests()
    yield
    registry._reset_user_added_custom_providers_for_tests()
