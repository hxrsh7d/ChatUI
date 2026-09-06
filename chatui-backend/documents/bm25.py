"""
Pure-Python BM25 (Okapi BM25) lexical ranking -- no external dependency.

Dense embeddings (the local hashing trick, or OpenAI/Google embeddings when
configured) are good at *semantic* similarity but often underweight exact
keyword, number, and name matches -- exactly what document Q&A questions
frequently hinge on ("what date", "who is the lead", "which version").
BM25 is a decades-old, still state-of-the-practice lexical ranking function
that excels at precisely that, and is cheap enough to run on every query
against a personal document set with zero added infrastructure.

documents/rag.py combines this with embedding similarity via Reciprocal
Rank Fusion rather than relying on either signal alone.
"""

from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25:
    """BM25 scorer over a fixed corpus of documents (chunks)."""

    def __init__(self, documents: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_tokens = [_tokenize(d) for d in documents]
        self.doc_lengths = [len(tokens) for tokens in self.doc_tokens]
        self.avg_doc_length = (sum(self.doc_lengths) / len(self.doc_lengths)) if self.doc_lengths else 0.0
        self.doc_freqs = [Counter(tokens) for tokens in self.doc_tokens]

        df: Counter[str] = Counter()
        for tokens in self.doc_tokens:
            for term in set(tokens):
                df[term] += 1

        n_docs = len(documents)
        self.idf: dict[str, float] = {
            term: math.log(1 + (n_docs - freq + 0.5) / (freq + 0.5)) for term, freq in df.items()
        }

    def scores(self, query: str) -> list[float]:
        """Returns one BM25 score per document, in the original document order."""
        query_terms = _tokenize(query)
        results = [0.0] * len(self.doc_tokens)

        if not query_terms or not self.doc_tokens:
            return results

        for i, freqs in enumerate(self.doc_freqs):
            doc_len = self.doc_lengths[i]
            score = 0.0
            for term in query_terms:
                if term not in freqs:
                    continue
                idf = self.idf.get(term, 0.0)
                if idf <= 0:
                    continue
                tf = freqs[term]
                denom = tf + self.k1 * (1 - self.b + self.b * doc_len / (self.avg_doc_length or 1))
                score += idf * (tf * (self.k1 + 1)) / denom
            results[i] = score

        return results
