"""Tests for documents/chunker.py."""

from documents.chunker import chunk_text


def test_short_text_single_chunk():
    chunks = chunk_text("Just one short paragraph.", chunk_size=1000, overlap=100)
    assert chunks == ["Just one short paragraph."]


def test_empty_text_no_chunks():
    assert chunk_text("", chunk_size=1000, overlap=100) == []
    assert chunk_text("   \n\n  ", chunk_size=1000, overlap=100) == []


def test_long_text_splits_into_multiple_chunks_within_size_bound():
    paragraphs = [f"Paragraph number {i} with some filler content to add length to it." for i in range(30)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, chunk_size=300, overlap=50)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 300 + 50  # small slack allowed for a single oversized paragraph edge case


def test_no_chunk_is_empty():
    text = "\n\n".join(f"Sentence {i}." for i in range(50))
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert all(c.strip() for c in chunks)


def test_hard_split_of_a_single_oversized_paragraph_overlaps_deterministically():
    long_para = "x" * 1000  # one giant "paragraph" forces the hard-split branch
    chunks = chunk_text(long_para, chunk_size=300, overlap=50)
    assert len(chunks) > 1
    for i in range(len(chunks) - 1):
        # consecutive hard-split slices should share the configured overlap
        assert chunks[i][-50:] == chunks[i + 1][:50]


def test_all_original_content_is_preserved_across_chunks():
    paragraphs = [f"Unique-marker-{i}" for i in range(20)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, chunk_size=80, overlap=10)
    joined = " ".join(chunks)
    for marker in paragraphs:
        assert marker in joined
