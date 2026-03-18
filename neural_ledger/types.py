"""Public-facing dataclasses returned by the Neural Ledger API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class MemoryRecord:
    """Returned by remember(). Represents a stored memory."""

    id: str
    content: str
    kind: str
    metadata: dict[str, Any]
    source: str | None
    timestamp: datetime
    agent_id: str | None = None
    provenance: str | None = None
    visibility: str = "local"


@dataclass(slots=True)
class MemoryHit:
    """Returned by recall(). Represents a retrieved memory with a relevance score."""

    id: str
    content: str
    score: float
    kind: str
    metadata: dict[str, Any]
    source: str | None
    timestamp: datetime
    why: str | None = None
    agent_id: str | None = None
    provenance: str | None = None


@dataclass(slots=True)
class MemoryConfig:
    """Optional configuration for Memory. All fields have sensible defaults."""

    default_limit: int = 5
    explain_recall: bool = False
    auto_learn_from_feedback: bool = True
    min_score: float = 0.0
