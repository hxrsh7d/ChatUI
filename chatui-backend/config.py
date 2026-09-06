"""
Central configuration for the ChatUI AI gateway backend.

Everything here is read from environment variables (populated from `.env`
via python-dotenv in main.py, or from real process environment variables in
production). Nothing here is exposed to the browser; `api/providers.py`
returns only booleans ("configured: true/false") and non-secret metadata.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


BACKEND_DIR = Path(__file__).resolve().parent
# Overridable so the test suite can point this at a throwaway temp dir
# instead of ever touching real uploads/DB (see chatui-backend/conftest.py).
DATA_DIR = Path(_env("CHATUI_DATA_DIR")) if _env("CHATUI_DATA_DIR") else (BACKEND_DIR / "data")
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "chatui.sqlite3"

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# llama.cpp (local)
# ---------------------------------------------------------------------------
LLAMA_CPP_EXE = _env("LLAMA_CPP_EXE", r"C:\llama.cpp\llama-server.exe")
MODELS_DIR = _env("MODELS_DIR", r"C:\llama.cpp\models")
LLAMA_HOST = _env("LLAMA_HOST", "127.0.0.1")
LLAMA_PORT = _env_int("LLAMA_PORT", 8080)
LLAMA_DEFAULT_MODEL = _env("LLAMA_DEFAULT_MODEL", "")

# ---------------------------------------------------------------------------
# Cloud AI providers
# ---------------------------------------------------------------------------
OPENAI_API_KEY = _env("OPENAI_API_KEY")
OPENAI_BASE_URL = _env("OPENAI_BASE_URL", "https://api.openai.com/v1")

ANTHROPIC_API_KEY = _env("ANTHROPIC_API_KEY")
ANTHROPIC_BASE_URL = _env("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
ANTHROPIC_VERSION = _env("ANTHROPIC_VERSION", "2023-06-01")

GOOGLE_API_KEY = _env("GOOGLE_API_KEY")
GOOGLE_BASE_URL = _env("GOOGLE_BASE_URL", "https://generativelanguage.googleapis.com")

GROQ_API_KEY = _env("GROQ_API_KEY")
GROQ_BASE_URL = _env("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

# Arbitrary OpenAI-compatible providers (vLLM, self-hosted, third parties).
# Configured as a JSON array so more than one can be added without code
# changes, e.g.:
# CUSTOM_OPENAI_COMPATIBLE_PROVIDERS=[{"id":"vllm","name":"My vLLM box","base_url":"http://localhost:8000/v1","api_key":"","model":"llama-3-70b"}]
_raw_custom_providers = _env("CUSTOM_OPENAI_COMPATIBLE_PROVIDERS", "[]")
try:
    CUSTOM_OPENAI_COMPATIBLE_PROVIDERS: list[dict] = json.loads(_raw_custom_providers) or []
    if not isinstance(CUSTOM_OPENAI_COMPATIBLE_PROVIDERS, list):
        CUSTOM_OPENAI_COMPATIBLE_PROVIDERS = []
except json.JSONDecodeError:
    CUSTOM_OPENAI_COMPATIBLE_PROVIDERS = []

# ---------------------------------------------------------------------------
# Web search
# ---------------------------------------------------------------------------
SEARCH_PROVIDER = _env("SEARCH_PROVIDER", "").lower()  # brave | tavily | searxng | ""
BRAVE_API_KEY = _env("BRAVE_API_KEY")
TAVILY_API_KEY = _env("TAVILY_API_KEY")
SEARXNG_URL = _env("SEARXNG_URL")
SEARCH_MAX_RESULTS = _env_int("SEARCH_MAX_RESULTS", 5)

# ---------------------------------------------------------------------------
# Image generation
# ---------------------------------------------------------------------------
IMAGE_PROVIDER = _env("IMAGE_PROVIDER", "").lower()  # openai | google | ""
OPENAI_IMAGE_MODEL = _env("OPENAI_IMAGE_MODEL", "gpt-image-1")

# ---------------------------------------------------------------------------
# Documents / RAG
# ---------------------------------------------------------------------------
MAX_UPLOAD_BYTES = _env_int("MAX_UPLOAD_BYTES", 25 * 1024 * 1024)  # 25 MB
CHUNK_SIZE_CHARS = _env_int("CHUNK_SIZE_CHARS", 1200)
CHUNK_OVERLAP_CHARS = _env_int("CHUNK_OVERLAP_CHARS", 200)
RAG_TOP_K = _env_int("RAG_TOP_K", 5)

# ---------------------------------------------------------------------------
# HTTP behaviour
# ---------------------------------------------------------------------------
PROVIDER_CONNECT_TIMEOUT = _env_int("PROVIDER_CONNECT_TIMEOUT", 10)
PROVIDER_REQUEST_TIMEOUT = _env_int("PROVIDER_REQUEST_TIMEOUT", 120)
PROVIDER_MAX_RETRIES = _env_int("PROVIDER_MAX_RETRIES", 2)

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
# Protects the expensive endpoints (chat completions, document uploads)
# from a runaway client loop or a compromised browser burning through
# provider API budget. In-memory, per-client-IP, fixed window -- resets on
# restart and does not coordinate across multiple backend processes. That
# tradeoff is appropriate for a personal/small-group ChatUI instance; a
# multi-instance deployment would need a shared store (e.g. Redis) instead.
RATE_LIMIT_ENABLED = _env("RATE_LIMIT_ENABLED", "true").lower() not in ("false", "0", "")
RATE_LIMIT_CHAT_PER_MINUTE = _env_int("RATE_LIMIT_CHAT_PER_MINUTE", 20)
RATE_LIMIT_UPLOADS_PER_MINUTE = _env_int("RATE_LIMIT_UPLOADS_PER_MINUTE", 10)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# LOG_FORMAT=json gives one JSON object per line (useful if you ship logs
# somewhere); the default "text" is easier to read directly in
# chatui-backend-output.log during development.
LOG_LEVEL = _env("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = _env("LOG_FORMAT", "text").lower()

# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------
# If set, every request must include "Authorization: Bearer <ACCESS_TOKEN>".
# Leave blank for frictionless solo/personal use on your own machine; set it
# before sharing this instance with anyone else. Generate one with e.g.:
#   python -c "import secrets; print(secrets.token_urlsafe(32))"
ACCESS_TOKEN = _env("ACCESS_TOKEN")
