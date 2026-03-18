"""Compiler: translates public remember() inputs into InternalRecord.

Separating compilation from the Runtime keeps runtime.py focused on
orchestration and makes the public-to-internal translation testable
and replaceable in one place.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from neural_ledger.internal.models import InternalRecord


class Compiler:
    """Translates public inputs into engine-internal representations."""

    def __init__(self, namespace: str) -> None:
        self.namespace = namespace

    def compile_record(
        self,
        content: str,
        kind: str,
        metadata: dict[str, Any],
        source: str | None,
        timestamp: datetime | None,
        embedding: list[float] | None = None,
        agent_id: str | None = None,
        provenance: str | None = None,
        visibility: str = "local",
    ) -> InternalRecord:
        """Produce an InternalRecord ready for storage."""
        now = timestamp or datetime.now(timezone.utc)
        return InternalRecord(
            id=str(uuid.uuid4()),
            content=content,
            kind=kind,
            metadata=metadata,
            source=source,
            timestamp=now,
            activation=1.0,
            embedding=embedding,
            namespace=self.namespace,
            agent_id=agent_id,
            provenance=provenance,
            visibility=visibility,
        )
