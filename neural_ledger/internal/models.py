"""Internal data representations — richer than public types, never exposed directly."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class InternalRecord:
    """A memory record as stored inside the engine."""

    id: str
    content: str
    kind: str
    metadata: dict[str, Any]
    source: str | None
    timestamp: datetime
    # Freshness signal: starts at 1.0, decays over time, reset on interaction.
    activation: float = 1.0
    # Learned usefulness prior: updated by feedback independently of link weights.
    # Positive feedback raises it (→ retrieved more readily); negative lowers it.
    # Range: [0.05, 2.0].  Default 1.0 = no prior opinion.
    usefulness: float = 1.0
    # Optional dense embedding vector; None when semantic model is unavailable.
    embedding: list[float] | None = None
    # Namespace for logical separation.
    namespace: str = "default"
    # Phase 3B — governed shared memory fields.
    # agent_id: identity of the agent that created this record.  None = legacy/unattributed.
    agent_id: str | None = None
    # provenance: source event, run identifier, or tool that produced this record.
    provenance: str | None = None
    # visibility: "local" (only the owning agent, within its namespace) or
    #             "shared" (all agents within the same namespace).
    visibility: str = "local"


@dataclass
class InternalLink:
    """A directed relationship between two records, with learned weight."""

    source_id: str
    target_id: str
    # Current learned weight: [0.0, 1.0]. Starts at a neutral prior.
    weight: float = 0.5
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # History of feedback signals applied to this link: each entry is in [0, 1].
    # Positive feedback appends values near 1.0; negative near 0.0.
    evidence: list[float] = field(default_factory=list)
    # Uncertainty derived from evidence variance; 0 = certain, 1 = maximally uncertain.
    uncertainty: float = 0.5
    namespace: str = "default"
    # Phase 3B — identity of the agent that created this link.  None = unattributed.
    agent_id: str | None = None

    def confidence(self) -> float:
        """Confidence is the complement of uncertainty."""
        return 1.0 - self.uncertainty
