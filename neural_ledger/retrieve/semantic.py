"""Semantic retrieval using dense embeddings.

Returns (record_id, cosine_similarity) pairs sorted by similarity descending.
Silently returns an empty list when no embedding model is available — the
keyword fallback in the main pipeline handles that case.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neural_ledger.internal.models import InternalRecord


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class SemanticRetriever:
    """Retrieves candidates by embedding cosine similarity.

    The encoder is injected at construction time so the rest of the engine
    stays decoupled from any specific embedding library.
    """

    def __init__(self, encoder: "_Encoder | None" = None) -> None:
        # encoder must implement encode(text: str) -> list[float]
        self._encoder = encoder

    @property
    def available(self) -> bool:
        return self._encoder is not None

    def encode(self, text: str) -> list[float] | None:
        if self._encoder is None:
            return None
        return self._encoder.encode(text)

    def retrieve(
        self,
        query_embedding: list[float],
        records: list["InternalRecord"],
        limit: int,
        min_score: float = 0.0,
    ) -> list[tuple[str, float]]:
        """Return up to `limit` (record_id, score) pairs sorted by score desc."""
        if not query_embedding:
            return []

        scored: list[tuple[str, float]] = []
        for record in records:
            if record.embedding is None:
                continue
            score = _cosine(query_embedding, record.embedding)
            if score >= min_score:
                scored.append((record.id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]


# ---------------------------------------------------------------------------
# Lightweight encoder shim — used when sentence-transformers is available.
# ---------------------------------------------------------------------------

class _SentenceTransformerEncoder:
    """Thin wrapper around sentence-transformers so the import is lazy."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._model = SentenceTransformer(model_name)
        except ImportError:
            self._model = None

    @property
    def available(self) -> bool:
        return self._model is not None

    def encode(self, text: str) -> list[float]:
        if self._model is None:
            return []
        result = self._model.encode(text, convert_to_numpy=True)
        return result.tolist()


def make_default_encoder() -> "_SentenceTransformerEncoder | None":
    """Return an encoder if sentence-transformers is installed, else None."""
    enc = _SentenceTransformerEncoder()
    return enc if enc.available else None
