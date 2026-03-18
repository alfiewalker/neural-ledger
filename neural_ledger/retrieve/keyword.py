"""Keyword-based retrieval fallback.

Uses simple token overlap (a lightweight TF-style score) so the system
works without any embedding model installed. Always returns results as long
as there are records — this is the safety net for the retrieval pipeline.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neural_ledger.internal.models import InternalRecord

# Common English stop words to strip before scoring.
_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "for",
    "of", "and", "or", "but", "with", "was", "be", "by", "as",
    "are", "this", "that", "from", "have", "has", "had", "not",
    "been", "were", "will", "would", "could", "should", "can",
    "i", "my", "me", "we", "our", "you", "your", "they", "their",
})


def _tokenise(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {t for t in tokens if t not in _STOP_WORDS and len(t) > 1}


def _score(query_tokens: set[str], record_tokens: set[str]) -> float:
    if not query_tokens or not record_tokens:
        return 0.0
    overlap = query_tokens & record_tokens
    # Jaccard-like: overlap / union, but weighted toward query coverage.
    query_coverage = len(overlap) / len(query_tokens)
    jaccard = len(overlap) / len(query_tokens | record_tokens)
    return 0.7 * query_coverage + 0.3 * jaccard


class KeywordRetriever:
    """Falls back to token-overlap scoring when embeddings are unavailable."""

    def retrieve(
        self,
        query: str,
        records: list["InternalRecord"],
        limit: int,
        min_score: float = 0.0,
    ) -> list[tuple[str, float]]:
        """Return up to `limit` (record_id, score) pairs sorted by score desc."""
        query_tokens = _tokenise(query)
        if not query_tokens:
            return [(r.id, 0.0) for r in records[:limit]]

        scored: list[tuple[str, float]] = []
        for record in records:
            record_tokens = _tokenise(record.content)
            score = _score(query_tokens, record_tokens)
            if score >= min_score:
                scored.append((record.id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]
