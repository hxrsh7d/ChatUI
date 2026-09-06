"""Tests for documents/embeddings.py -- the offline hashing embedder."""

import pytest

from documents.embeddings import cosine_similarity, embed_texts


@pytest.mark.asyncio
async def test_local_hashing_embedder_is_deterministic():
    vectors1, backend1 = await embed_texts(["hello world", "goodbye world"])
    vectors2, backend2 = await embed_texts(["hello world", "goodbye world"])
    assert backend1 == "local-hashing"
    assert vectors1 == vectors2


@pytest.mark.asyncio
async def test_empty_input_returns_empty_output():
    vectors, backend = await embed_texts([])
    assert vectors == []
    assert backend == "none"


@pytest.mark.asyncio
async def test_similar_texts_score_higher_than_unrelated_text():
    vectors, _ = await embed_texts(
        [
            "The cat sat on the mat",
            "A cat was sitting on a mat",
            "Quantum physics and string theory research",
        ]
    )
    sim_related = cosine_similarity(vectors[0], vectors[1])
    sim_unrelated = cosine_similarity(vectors[0], vectors[2])
    assert sim_related > sim_unrelated


def test_cosine_similarity_identical_vectors_is_one():
    v = [1.0, 0.0, 0.0]
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal_vectors_is_zero():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_similarity_mismatched_lengths_returns_zero_not_error():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0
