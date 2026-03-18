"""Public API for Neural Ledger.

The Memory class is the only thing most users ever need.
All internal complexity is hidden behind these four verbs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from neural_ledger.internal.runtime import Runtime
from neural_ledger.types import MemoryConfig, MemoryHit, MemoryRecord


class Memory:
    """A lightweight memory engine that remembers, recalls, and learns.

    Usage::

        from neural_ledger import Memory

        mem = Memory()
        mem.remember("GitHub API failed because the token expired", kind="observation")
        hits = mem.recall("How should I fix this 401 error?", with_why=True)
        mem.feedback(hits, helped=True)
    """

    def __init__(
        self,
        persist_path: str | None = None,
        namespace: str = "default",
        agent_id: str | None = None,
        config: MemoryConfig | None = None,
    ) -> None:
        """Create a Memory instance.

        Args:
            persist_path: Path to a SQLite file for persistent storage.
                          Pass None (the default) for a fully in-memory instance.
                          When given, memory survives process restart.
            namespace:    Logical name for this memory space. Allows multiple
                          independent Memory instances to coexist in the same
                          process without colliding.
            agent_id:     Identity of the agent using this Memory instance.
                          When set, records written by this instance carry the
                          agent_id, enabling governed shared memory (Phase 3B).
                          Pass None (the default) for single-agent operation.
            config:       Optional configuration. Sensible defaults are used if
                          omitted — no configuration required to get started.
        """
        resolved_config = config if config is not None else MemoryConfig()
        self._runtime = Runtime(
            namespace=namespace,
            config=resolved_config,
            persist_path=persist_path,
            agent_id=agent_id,
        )

    # ------------------------------------------------------------------
    # remember
    # ------------------------------------------------------------------

    def remember(
        self,
        content: str,
        *,
        kind: str = "note",
        metadata: dict[str, Any] | None = None,
        source: str | None = None,
        timestamp: datetime | None = None,
        visibility: str = "local",
        provenance: str | None = None,
    ) -> MemoryRecord:
        """Store a piece of experience.

        Args:
            content:    The text of the memory. Must be a non-empty string.
            kind:       Optional label such as 'note', 'observation', 'preference',
                        'fact', or 'procedure'. No schema enforced.
            metadata:   Optional free-form key-value pairs.
            source:     Optional identifier for the originating tool or system.
            timestamp:  Override the record timestamp (default: now).
            visibility: 'local' (default) — visible only to this agent.
                        'shared' — visible to all agents in the same namespace.
            provenance: Optional identifier for the run, event, or tool that
                        produced this memory (e.g. 'run-123', 'tool:github_api').

        Returns:
            MemoryRecord with an assigned ID.
        """
        _require_non_empty_str(content, "content")
        _require_non_empty_str(kind, "kind")
        _validate_visibility(visibility)

        return self._runtime.remember(
            content=content,
            kind=kind,
            metadata=metadata or {},
            source=source,
            timestamp=timestamp,
            visibility=visibility,
            provenance=provenance,
        )

    # ------------------------------------------------------------------
    # remember_many
    # ------------------------------------------------------------------

    def remember_many(
        self,
        contents: list[str] | list[dict[str, Any]],
        *,
        default_kind: str = "note",
        default_metadata: dict[str, Any] | None = None,
        source: str | None = None,
        default_visibility: str = "local",
    ) -> list[MemoryRecord]:
        """Store several memories at once.

        Accepts either a list of strings or a list of dicts with at least
        a 'content' key. Extra dict keys ('kind', 'metadata', 'source',
        'timestamp', 'visibility', 'provenance') are forwarded to remember().

        Args:
            contents:           List of strings or dicts.
            default_kind:       Fallback kind when not specified in each item.
            default_metadata:   Fallback metadata when not specified in each item.
            source:             Shared source label for all items.
            default_visibility: Fallback visibility ('local' or 'shared') when
                                not specified in each dict item.

        Returns:
            List of MemoryRecord in the same order as the input.
        """
        _validate_visibility(default_visibility)

        if not contents:
            return []

        records: list[MemoryRecord] = []
        for item in contents:
            if isinstance(item, str):
                records.append(
                    self.remember(
                        content=item,
                        kind=default_kind,
                        metadata=default_metadata,
                        source=source,
                        visibility=default_visibility,
                    )
                )
            elif isinstance(item, dict):
                content = item.get("content", "")
                _require_non_empty_str(content, "content (in remember_many item)")
                records.append(
                    self.remember(
                        content=content,
                        kind=item.get("kind", default_kind),
                        metadata=item.get("metadata", default_metadata),
                        source=item.get("source", source),
                        timestamp=item.get("timestamp"),
                        visibility=item.get("visibility", default_visibility),
                        provenance=item.get("provenance"),
                    )
                )
            else:
                raise TypeError(
                    f"remember_many expects strings or dicts, got {type(item).__name__}"
                )

        return records

    # ------------------------------------------------------------------
    # recall
    # ------------------------------------------------------------------

    def recall(
        self,
        query: str,
        *,
        limit: int | None = None,
        kind: str | list[str] | None = None,
        metadata_filter: dict[str, Any] | None = None,
        min_score: float | None = None,
        with_why: bool = False,
        scope: str = "local",
    ) -> list[MemoryHit]:
        """Retrieve the most relevant memories for a query.

        Args:
            query:           The question or context to search with.
            limit:           Maximum number of hits to return
                             (default: config.default_limit = 5).
            kind:            Filter by one or more kind labels.
            metadata_filter: Filter by exact metadata key-value pairs.
            min_score:       Drop hits below this score
                             (default: config.min_score = 0.0).
            with_why:        When True, populate hit.why with a human-readable
                             explanation of why each result appeared.
            scope:           'local' (default) — this agent's own memories only.
                             'shared' — shared memories from all agents.
                             'merged' — local + shared, ranked together.

        Returns:
            List of MemoryHit sorted by relevance score descending.
        """
        _require_non_empty_str(query, "query")
        _validate_scope(scope)

        resolved_limit = limit if limit is not None else self._runtime.config.default_limit
        if resolved_limit < 1:
            raise ValueError("limit must be at least 1")

        resolved_min_score = (
            min_score if min_score is not None else self._runtime.config.min_score
        )

        return self._runtime.recall(
            query=query,
            limit=resolved_limit,
            kind_filter=kind,
            metadata_filter=metadata_filter,
            min_score=resolved_min_score,
            with_why=with_why,
            scope=scope,
        )

    # ------------------------------------------------------------------
    # feedback
    # ------------------------------------------------------------------

    def feedback(
        self,
        hits_or_ids: "list[MemoryHit] | list[str] | MemoryHit | str",
        *,
        helped: "bool | float",
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Tell Neural Ledger whether retrieved memories helped.

        This is the core learning signal. Positive feedback strengthens the
        links that produced the hits; negative feedback weakens them.

        Args:
            hits_or_ids: The hits returned by recall(), or a list of record IDs,
                         or a single hit or ID.
            helped:      True / False for simple usage, or a float in [0, 1]
                         for finer control.
            reason:      Optional human-readable reason (accepted and forwarded
                         to the learning engine; persistence is a Phase 3 concern).
            metadata:    Optional key-value context (accepted; not yet persisted in v1).
        """
        helped_float = _validate_helped(helped)
        record_ids = _normalise_hits_or_ids(hits_or_ids)

        if not record_ids:
            return

        self._runtime.feedback(
            record_ids=record_ids,
            helped=helped_float,
            reason=reason,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def metrics(self) -> dict:
        """Return a summary of engine telemetry."""
        return self._runtime.metrics.summary()

    def close(self) -> None:
        """Explicitly close any open database connections.

        For in-memory instances this is a no-op.
        For persistent instances it flushes and closes the SQLite connection.
        Memory can also be used as a context manager::

            with Memory(persist_path="memory.db") as mem:
                mem.remember("...")
        """
        self._runtime.close()

    def __enter__(self) -> "Memory":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------

def _require_non_empty_str(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string, got {value!r}")


def _validate_helped(helped: "bool | float") -> float:
    if isinstance(helped, bool):
        return 1.0 if helped else 0.0
    if isinstance(helped, (int, float)):
        val = float(helped)
        if not (0.0 <= val <= 1.0):
            raise ValueError(
                f"helped must be a bool or a float between 0 and 1, got {val}"
            )
        return val
    raise TypeError(
        f"helped must be bool or float, got {type(helped).__name__}"
    )


_VALID_VISIBILITY = {"local", "shared"}
_VALID_SCOPE = {"local", "shared", "merged"}


def _validate_visibility(visibility: str) -> None:
    if visibility not in _VALID_VISIBILITY:
        raise ValueError(
            f"visibility must be 'local' or 'shared', got {visibility!r}"
        )


def _validate_scope(scope: str) -> None:
    if scope not in _VALID_SCOPE:
        raise ValueError(
            f"scope must be 'local', 'shared', or 'merged', got {scope!r}"
        )


def _normalise_hits_or_ids(
    hits_or_ids: "list[MemoryHit] | list[str] | MemoryHit | str",
) -> list[str]:
    if isinstance(hits_or_ids, str):
        return [hits_or_ids]
    if isinstance(hits_or_ids, MemoryHit):
        return [hits_or_ids.id]
    if isinstance(hits_or_ids, list):
        ids: list[str] = []
        for item in hits_or_ids:
            if isinstance(item, MemoryHit):
                ids.append(item.id)
            elif isinstance(item, str):
                ids.append(item)
            else:
                raise TypeError(
                    f"feedback list items must be MemoryHit or str, got {type(item).__name__}"
                )
        return ids
    raise TypeError(
        f"hits_or_ids must be a MemoryHit, str, or list thereof, "
        f"got {type(hits_or_ids).__name__}"
    )
