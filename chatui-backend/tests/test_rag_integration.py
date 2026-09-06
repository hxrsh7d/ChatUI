"""
End-to-end test of the RAG pipeline: upload a real document through the
actual HTTP API, then retrieve from it, and confirm retrieval actually
prefers the relevant chunk over an irrelevant one from a second document --
this is the "must not blindly dump every document into the prompt"
guarantee the project brief calls out.
"""

import config
import main
import pytest
from fastapi.testclient import TestClient

from documents.rag import build_context_block, retrieve


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(config, "ACCESS_TOKEN", "")
    return TestClient(main.app)


@pytest.mark.asyncio
async def test_retrieval_prefers_relevant_document_over_irrelevant_one(client):
    doc_a = client.post(
        "/api/documents",
        files={
            "file": (
                "nightingale.txt",
                b"Project Nightingale is a sodium-ion battery research effort led by "
                b"Dr. Amara Okafor. In August 2025 the team reached 340 Wh/kg energy "
                b"density in laboratory prototypes.",
                "text/plain",
            )
        },
    )
    doc_b = client.post(
        "/api/documents",
        files={
            "file": (
                "recipe.txt",
                b"To make a good omelette, whisk three eggs with a pinch of salt, "
                b"then cook gently in butter over low heat, folding once.",
                "text/plain",
            )
        },
    )
    assert doc_a.status_code == 200
    assert doc_b.status_code == 200
    doc_a_id = doc_a.json()["id"]
    doc_b_id = doc_b.json()["id"]

    chunks = await retrieve(
        "Who leads Project Nightingale and what milestone did they reach?",
        [doc_a_id, doc_b_id],
    )

    assert chunks, "expected at least one retrieved chunk"
    assert chunks[0].document_id == doc_a_id
    assert "Okafor" in chunks[0].text

    context = build_context_block(chunks)
    assert "Okafor" in context
    # the irrelevant recipe document should not dominate the top result
    assert chunks[0].document_id != doc_b_id


@pytest.mark.asyncio
async def test_retrieval_with_no_attachments_returns_nothing(client):
    chunks = await retrieve("anything", [])
    assert chunks == []


@pytest.mark.asyncio
async def test_retrieval_ignores_documents_that_failed_processing(client):
    # A document that never made it to "ready" (e.g. failed upload) must
    # never be silently included in retrieval.
    bad = client.post(
        "/api/documents",
        files={"file": ("broken.txt", bytes([0xFF, 0xFE]), "text/plain")},
    )
    assert bad.status_code == 422  # rejected before a document row could be marked ready

    good = client.post(
        "/api/documents",
        files={"file": ("ok.txt", b"The meeting is scheduled for Tuesday at 3pm.", "text/plain")},
    )
    doc_id = good.json()["id"]

    chunks = await retrieve("When is the meeting?", [doc_id])
    assert chunks
    assert all(c.document_id == doc_id for c in chunks)


@pytest.mark.asyncio
async def test_bm25_fusion_beats_keyword_stuffed_distractor(client):
    # An adversarial but realistic case: one document is boilerplate that
    # repeats generic query terms densely without containing the answer;
    # a separate document mentions those same terms only once each but
    # contains the actual answer. Raw term-frequency / bag-of-words
    # similarity (what the offline hashing embedder alone computes)
    # rewards repetition and ranks the keyword-stuffed distractor above
    # the real answer. BM25's IDF down-weighting of common repeated terms
    # and term-frequency saturation fixes this -- exactly the case
    # documents/rag.py's RRF fusion is meant to cover. Uses two separate
    # documents (not two chunks of one document) so chunk overlap can't
    # blend the two signals together and mask the effect.
    stuffing_doc = client.post(
        "/api/documents",
        files={
            "file": (
                "boilerplate.txt",
                ("finance review invoice process schedule budget " * 25).strip().encode(),
                "text/plain",
            )
        },
    )
    answer_doc = client.post(
        "/api/documents",
        files={
            "file": (
                "answer.txt",
                b"The finance review of invoice processing found the refund amount was "
                b"4290 dollars, approved by the budget schedule committee on a single pass.",
                "text/plain",
            )
        },
    )
    stuffing_id = stuffing_doc.json()["id"]
    answer_id = answer_doc.json()["id"]

    chunks = await retrieve("finance review invoice refund amount", [stuffing_id, answer_id], top_k=1)

    assert chunks
    assert chunks[0].document_id == answer_id
    assert "4290" in chunks[0].text


@pytest.mark.asyncio
async def test_hybrid_retrieval_surfaces_exact_keyword_match_the_offline_embedder_alone_would_likely_miss(client):
    # The local hashing-trick embedder has no real semantic understanding --
    # it can easily fail to distinguish a chunk containing the *exact*
    # answer from a chunk that merely shares generic topic words with a
    # short, sparse query. BM25 (blended in via RRF in rag.retrieve) is
    # specifically strong at exact identifiers like invoice/PO numbers,
    # which is exactly what this test exercises end-to-end.
    doc = client.post(
        "/api/documents",
        files={
            "file": (
                "invoices.txt",
                b"Invoice INV-88214 covers consulting services for the March engagement.\n\n"
                b"Invoice INV-40093 covers hardware procurement for the new office.\n\n"
                b"Invoice INV-55510 covers the annual software license renewal.\n\n"
                b"General notes: all invoices are payable net-30 from the issue date, "
                b"and finance reviews outstanding invoices every Friday.",
                "text/plain",
            )
        },
    )
    doc_id = doc.json()["id"]

    chunks = await retrieve("What does invoice INV-40093 cover?", [doc_id], top_k=1)

    assert chunks
    assert "INV-40093" in chunks[0].text
    assert "hardware procurement" in chunks[0].text
