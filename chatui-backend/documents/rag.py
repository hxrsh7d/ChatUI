"""
Retrieval step of the RAG pipeline: given a user query and a set of
attached document ids, return the most relevant chunks (not the whole
document) so we never "blindly dump" irrelevant documents into the prompt.

Retrieval combines two independent signals via Reciprocal Rank Fusion (RRF)
rather than relying on embedding similarity alone:
  1. Dense embedding cosine similarity -- good at semantic/paraphrase match
  2. BM25 lexical scoring             -- good at exact keywords/dates/names

RRF is used instead of a weighted-sum blend because it needs no per-query
score normalization: it only cares about each signal's RANKING, so it's
robust even though embedding cosine similarity and BM25 scores live on
completely different numeric scales.
"""

from __future__ import annotations

from dataclasses import dataclass

import config
from documents import store
from documents.bm25 import BM25
from documents.embeddings import cosine_similarity, embed_texts

RRF_K = 60  # standard reciprocal-rank-fusion constant


@dataclass
class RetrievedChunk:
    document_id: str
    document_name: str
    text: str
    score: float


def _ranks_desc(scores: list[float]) -> list[int]:
    """For each index, its 0-based rank when scores are sorted descending
    (rank 0 = highest score). Ties keep stable original order."""
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    ranks = [0] * len(scores)
    for rank, idx in enumerate(order):
        ranks[idx] = rank
    return ranks


async def retrieve(query: str, attachment_ids: list[str], top_k: int | None = None) -> list[RetrievedChunk]:
    if not attachment_ids or not query.strip():
        return []

    top_k = top_k or config.RAG_TOP_K

    documents = {d["id"]: d for d in store.get_documents(attachment_ids)}
    ready_ids = [doc_id for doc_id, d in documents.items() if d["status"] == "ready"]
    if not ready_ids:
        return []

    chunks = store.get_chunks_for_documents(ready_ids)
    if not chunks:
        return []

    texts = [c["text"] for c in chunks]

    # Signal 1: dense embedding similarity (semantic)
    (query_vector,), _backend = await embed_texts([query])
    embedding_scores = [cosine_similarity(query_vector, c["embedding"]) for c in chunks]

    # Signal 2: BM25 (lexical -- names, dates, numbers, exact phrases)
    bm25_scores = BM25(texts).scores(query)

    embedding_ranks = _ranks_desc(embedding_scores)
    bm25_ranks = _ranks_desc(bm25_scores)

    fused_scores = [
        1.0 / (RRF_K + embedding_ranks[i] + 1) + 1.0 / (RRF_K + bm25_ranks[i] + 1) for i in range(len(chunks))
    ]

    # Primary sort: fused RRF score. Secondary tie-break: BM25 rank. RRF can
    # produce EXACT ties (e.g. with only two chunks whose two signals fully
    # disagree, each ranking #1 on one signal and #2 on the other -- which
    # is symmetric by construction). Without a deterministic secondary key,
    # the outcome would depend on incidental chunk ordering. BM25 is
    # preferred as the tie-break because it's a precise, well-understood
    # signal, whereas the embedding side of the fusion may be the crude
    # offline hashing fallback (see documents/embeddings.py) when no cloud
    # embedding provider is configured.
    order = sorted(range(len(chunks)), key=lambda i: (fused_scores[i], -bm25_ranks[i]), reverse=True)
    scored = [
        RetrievedChunk(
            document_id=chunks[i]["document_id"],
            document_name=documents[chunks[i]["document_id"]]["name"],
            text=chunks[i]["text"],
            score=fused_scores[i],
        )
        for i in order
    ]
    return scored[:top_k]


def build_context_block(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return ""
    parts = ["Relevant excerpts from the user's attached document(s):"]
    for i, c in enumerate(chunks, start=1):
        parts.append(f"\n[{i}] From \"{c.document_name}\":\n{c.text}")
    parts.append(
        "\nUse the excerpts above to answer the user's question when relevant. "
        "If the excerpts don't contain the answer, say so rather than guessing."
    )
    return "\n".join(parts)


async def process_and_store_document(doc_id: str, text: str) -> None:
    from documents.chunker import chunk_text

    chunks = chunk_text(text)
    if not chunks:
        store.mark_document_error(doc_id, "Document contained no usable text after chunking.")
        return

    vectors, backend = await embed_texts(chunks)
    store.add_chunks(doc_id, chunks, vectors)
    store.mark_document_ready(doc_id, backend)
