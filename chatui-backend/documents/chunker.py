"""Simple, dependency-free text chunker with overlap.

Splits on paragraph boundaries first, then packs paragraphs into chunks up
to `chunk_size` characters, carrying `overlap` characters of trailing
context into the next chunk so a fact split across a boundary is still
retrievable from at least one chunk.
"""

from __future__ import annotations

import re

import config


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    chunk_size = chunk_size or config.CHUNK_SIZE_CHARS
    overlap = overlap or config.CHUNK_OVERLAP_CHARS

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(para) > chunk_size:
            # Paragraph itself is too big; hard-split it.
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(para), chunk_size - overlap):
                chunks.append(para[i : i + chunk_size])
            continue

        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            chunks.append(current)
            # carry overlap from the end of the previous chunk
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n\n{para}".strip()

    if current:
        chunks.append(current)

    return chunks
