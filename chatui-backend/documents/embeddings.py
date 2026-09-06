"""
Embeddings for the local RAG pipeline.

Per the project brief ("do not add a massive infrastructure dependency
unnecessarily", "a local/simple vector database is acceptable"), this uses
a deterministic local hashing vectorizer (a bag-of-words / TF hashed into a
fixed-size vector, L2-normalized) as the zero-config, fully offline
fallback -- no downloaded model, no GPU, no network access required.

If a cloud API key is configured, its embeddings are used instead
automatically for better retrieval quality, preferring OpenAI, then Google
Gemini, then falling back to local hashing:
  1. OpenAI text-embedding-3-small (if OPENAI_API_KEY is set)
  2. Google gemini-embedding-001   (if GOOGLE_API_KEY is set)
  3. Local hashing vectorizer      (always available, zero config)

This is the "modular so the vector store can later be replaced" hook the
brief asks for; swapping in a different embedding backend only means
changing `embed_texts` below. Retrieval also blends in BM25 lexical
scoring regardless of which embedding backend is active (see
documents/rag.py) since dense embeddings alone -- especially the offline
hashing fallback -- tend to underweight exact keyword/date/name matches.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Optional

import httpx

import config

VECTOR_DIM = 512
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _hash_embed(text: str) -> list[float]:
    """Deterministic offline embedding: hash each token into a bucket of a
    fixed-size vector (the 'hashing trick'), weight by term frequency, then
    L2-normalize so cosine similarity is comparable across documents."""
    vec = [0.0] * VECTOR_DIM
    tokens = _tokenize(text)
    if not tokens:
        return vec

    for token in tokens:
        digest = hashlib.md5(token.encode("utf-8")).hexdigest()
        bucket = int(digest, 16) % VECTOR_DIM
        sign = 1.0 if int(digest, 16) % 2 == 0 else -1.0
        vec[bucket] += sign

    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


async def _openai_embed(texts: list[str]) -> Optional[list[list[float]]]:
    if not config.OPENAI_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=config.PROVIDER_REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{config.OPENAI_BASE_URL}/embeddings",
                headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": "text-embedding-3-small", "input": texts},
            )
            if response.status_code != 200:
                return None
            data = response.json()
            items = data.get("data", [])
            if len(items) != len(texts):
                return None
            return [item["embedding"] for item in items]
    except Exception:
        return None


async def _google_embed(texts: list[str]) -> Optional[list[list[float]]]:
    if not config.GOOGLE_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=config.PROVIDER_REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{config.GOOGLE_BASE_URL}/v1beta/models/gemini-embedding-001:batchEmbedContents",
                params={"key": config.GOOGLE_API_KEY},
                json={
                    "requests": [
                        {"model": "models/gemini-embedding-001", "content": {"parts": [{"text": t}]}}
                        for t in texts
                    ]
                },
            )
            if response.status_code != 200:
                return None
            data = response.json()
            embeddings = data.get("embeddings", [])
            if len(embeddings) != len(texts):
                return None
            return [e["values"] for e in embeddings]
    except Exception:
        return None


async def embed_texts(texts: list[str]) -> tuple[list[list[float]], str]:
    """Returns (vectors, backend_name). Tries OpenAI, then Google, for
    better retrieval quality, falls back to the offline hashing vectorizer
    so RAG always works even with zero cloud config."""
    if not texts:
        return [], "none"

    openai_vectors = await _openai_embed(texts)
    if openai_vectors is not None and len(openai_vectors) == len(texts):
        return openai_vectors, "openai:text-embedding-3-small"

    google_vectors = await _google_embed(texts)
    if google_vectors is not None and len(google_vectors) == len(texts):
        return google_vectors, "google:gemini-embedding-001"

    return [_hash_embed(t) for t in texts], "local-hashing"


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (norm_a * norm_b)
