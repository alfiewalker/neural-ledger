"""Path and hit ranking.

Scores each ContextPath using a weighted combination of three signals
preserved from the prototype:
  1. seed_score     — relevance of the starting node (semantic or keyword)
  2. path_bonus     — reward for having outward link context
  3. avg_activation — freshness of nodes on the path

The weights are kept in InternalPolicy so they can be tuned without touching
ranking logic.
"""

from __future__ import annotations

from dataclasses import dataclass

from neural_ledger.retrieve.paths import ContextPath


@dataclass
class RankingWeights:
    relevance: float = 0.6
    path_bonus: float = 0.2
    activation: float = 0.2

    def __post_init__(self) -> None:
        total = self.relevance + self.path_bonus + self.activation
        assert abs(total - 1.0) < 1e-6, f"Ranking weights must sum to 1.0, got {total}"


def score_path(path: ContextPath, weights: RankingWeights) -> float:
    """Combine path signals into a single comparable score in [0, 1]."""
    # path_bonus: normalise cumulative link weight to (0, 1) via sigmoid-like squash.
    # A single hop of weight 0.5 yields ~0.33; two hops of weight 1.0 yields ~0.67.
    link_depth = len(path.node_ids) - 1
    if link_depth > 0:
        avg_link_weight = path.total_link_weight / link_depth
        # Squash: tanh gives a smooth (0, 1) output.
        import math
        path_bonus = math.tanh(avg_link_weight * link_depth)
    else:
        path_bonus = 0.0

    return (
        weights.relevance * path.seed_score
        + weights.path_bonus * path_bonus
        + weights.activation * path.avg_activation
    )


def rank_paths(
    paths: list[ContextPath],
    weights: RankingWeights,
    limit: int,
    min_score: float = 0.0,
) -> list[tuple[ContextPath, float]]:
    """Return up to `limit` (path, score) pairs sorted by score descending."""
    scored = [(p, score_path(p, weights)) for p in paths]
    scored = [(p, s) for p, s in scored if s >= min_score]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def build_why(path: ContextPath, score: float, used_semantic: bool) -> str:
    """Produce a human-readable explanation for why this hit appeared."""
    parts: list[str] = []

    retrieval_method = "semantic similarity" if used_semantic else "keyword match"
    parts.append(f"Retrieved by {retrieval_method} (seed score {path.seed_score:.2f}).")

    if len(path.node_ids) > 1:
        parts.append(
            f"Expanded through {len(path.node_ids) - 1} related "
            f"{'record' if len(path.node_ids) == 2 else 'records'} via learned links."
        )

    if path.avg_activation < 0.5:
        parts.append("Note: this memory has lower freshness — it has aged since last use.")
    elif path.avg_activation >= 0.8:
        parts.append("This memory is recent and active.")

    if score >= 0.7:
        parts.append("Overall high relevance.")
    elif score < 0.3:
        parts.append("Weak match — returned as a best-available candidate.")

    return " ".join(parts)
