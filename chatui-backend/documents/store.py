"""
Storage layer for uploaded documents and their chunk embeddings.

Uses stdlib sqlite3 -- no separate vector-database service to run, which
fits the brief's "do not add a massive infrastructure dependency
unnecessarily" and "simplest appropriate persistence" guidance. Chunk
vectors are stored as JSON arrays of floats and compared with plain-Python
cosine similarity in rag.py; this is entirely adequate for the handful-to-
low-thousands of chunks a personal ChatUI instance will accumulate, and the
module is small enough to swap for Chroma/FAISS/Qdrant later without
touching any caller outside this file.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Optional

import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size INTEGER NOT NULL,
    status TEXT NOT NULL,
    error TEXT,
    created_at REAL NOT NULL,
    embedding_backend TEXT,
    kind TEXT NOT NULL DEFAULT 'text'
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS image_blobs (
    document_id TEXT PRIMARY KEY,
    mime_type TEXT NOT NULL,
    data_base64 TEXT NOT NULL,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
"""


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)


def create_document(name: str, mime_type: str, size: int, kind: str = "text") -> str:
    doc_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            "INSERT INTO documents (id, name, mime_type, size, status, error, created_at, embedding_backend, kind) "
            "VALUES (?, ?, ?, ?, 'processing', NULL, ?, NULL, ?)",
            (doc_id, name, mime_type, size, time.time(), kind),
        )
    return doc_id


def store_image_blob(doc_id: str, mime_type: str, data_base64: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO image_blobs (document_id, mime_type, data_base64) VALUES (?, ?, ?)",
            (doc_id, mime_type, data_base64),
        )
        conn.execute("UPDATE documents SET status = 'ready' WHERE id = ?", (doc_id,))


def get_image_blobs(doc_ids: list[str]) -> list[dict[str, Any]]:
    if not doc_ids:
        return []
    placeholders = ",".join("?" for _ in doc_ids)
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM image_blobs WHERE document_id IN ({placeholders})", doc_ids
        ).fetchall()
        return [dict(r) for r in rows]


def mark_document_ready(doc_id: str, embedding_backend: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE documents SET status = 'ready', embedding_backend = ? WHERE id = ?",
            (embedding_backend, doc_id),
        )


def mark_document_error(doc_id: str, error: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE documents SET status = 'error', error = ? WHERE id = ?", (error, doc_id))


def add_chunks(doc_id: str, texts: list[str], vectors: list[list[float]]) -> None:
    with _connect() as conn:
        conn.executemany(
            "INSERT INTO chunks (id, document_id, chunk_index, text, embedding) VALUES (?, ?, ?, ?, ?)",
            [
                (str(uuid.uuid4()), doc_id, idx, text, json.dumps(vector))
                for idx, (text, vector) in enumerate(zip(texts, vectors))
            ],
        )


def get_document(doc_id: str) -> Optional[dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        return dict(row) if row else None


def get_documents(doc_ids: list[str]) -> list[dict[str, Any]]:
    if not doc_ids:
        return []
    placeholders = ",".join("?" for _ in doc_ids)
    with _connect() as conn:
        rows = conn.execute(f"SELECT * FROM documents WHERE id IN ({placeholders})", doc_ids).fetchall()
        return [dict(r) for r in rows]


def get_chunks_for_documents(doc_ids: list[str]) -> list[dict[str, Any]]:
    if not doc_ids:
        return []
    placeholders = ",".join("?" for _ in doc_ids)
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM chunks WHERE document_id IN ({placeholders}) ORDER BY document_id, chunk_index",
            doc_ids,
        ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["embedding"] = json.loads(d["embedding"])
            out.append(d)
        return out


def delete_document(doc_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM chunks WHERE document_id = ?", (doc_id,))
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
