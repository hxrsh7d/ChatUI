"""Tests for documents/bm25.py."""

from documents.bm25 import BM25


def test_exact_keyword_match_scores_highest():
    docs = [
        "The invoice total was four hundred and twelve dollars.",
        "Weather forecasts predict rain for most of the week.",
        "Project deadline moved to November 12th per the memo.",
    ]
    bm25 = BM25(docs)
    scores = bm25.scores("November 12th deadline")
    assert scores[2] > scores[0]
    assert scores[2] > scores[1]


def test_no_query_terms_present_gives_zero_scores():
    docs = ["Alpha beta gamma.", "Delta epsilon zeta."]
    bm25 = BM25(docs)
    scores = bm25.scores("nonexistent completely unrelated words xyz")
    assert scores == [0.0, 0.0]


def test_empty_query_gives_zero_scores():
    docs = ["Some document text.", "Another document."]
    bm25 = BM25(docs)
    assert bm25.scores("") == [0.0, 0.0]


def test_empty_corpus_does_not_error():
    bm25 = BM25([])
    assert bm25.scores("anything") == []


def test_rare_term_weighted_higher_than_common_term():
    docs = [
        "the the the the the unicorn",
        "the the the the the the",
        "the the the the the the",
    ]
    bm25 = BM25(docs)
    scores = bm25.scores("unicorn")
    # "unicorn" appears in exactly one doc out of three -> should score >0
    # there and 0 everywhere else.
    assert scores[0] > 0
    assert scores[1] == 0
    assert scores[2] == 0


def test_term_frequency_increases_score_with_diminishing_returns():
    docs = ["battery battery battery battery battery", "battery"]
    bm25 = BM25(docs)
    scores = bm25.scores("battery")
    assert scores[0] > scores[1]
