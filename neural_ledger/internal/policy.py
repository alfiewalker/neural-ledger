"""Internal policy: ranking weights, thresholds, and retrieval defaults.

All tunable engine behaviour lives here so the public API and the retrieval /
learning modules stay decoupled from numeric choices.
"""

from __future__ import annotations

from dataclasses import dataclass

from neural_ledger.retrieve.ranking import RankingWeights


@dataclass
class InternalPolicy:
    """Central location for all engine-room defaults."""

    # Retrieval
    candidate_limit: int = 20           # initial candidates before path expansion
    path_expansion_depth: int = 2       # max hops from each seed
    path_expansion_max: int = 15        # max number of seeds to expand

    # Ranking
    ranking_weights: RankingWeights = None  # type: ignore[assignment]

    # Decay
    half_life_seconds: float = 7 * 24 * 3600  # 7 days

    # Links
    initial_link_weight: float = 0.5    # prior weight when a new link is created

    def __post_init__(self) -> None:
        if self.ranking_weights is None:
            self.ranking_weights = RankingWeights()
