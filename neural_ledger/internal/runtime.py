"""Runtime: wires together stores, retrieval pipeline, and learning engine.

The Memory facade delegates to the Runtime, keeping api.py thin.
The Runtime owns all subsystem references and orchestrates multi-step flows.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from neural_ledger.internal.compiler import Compiler
from neural_ledger.internal.models import InternalLink, InternalRecord
from neural_ledger.internal.policy import InternalPolicy
from neural_ledger.learn.decay import apply_decay
from neural_ledger.learn.feedback import apply_feedback
from neural_ledger.retrieve.keyword import KeywordRetriever
from neural_ledger.retrieve.paths import ContextPath, expand_paths
from neural_ledger.retrieve.ranking import build_why, rank_paths
from neural_ledger.retrieve.semantic import SemanticRetriever, make_default_encoder
from neural_ledger.store.factory import make_stores
from neural_ledger.telemetry.metrics import Metrics, timed
from neural_ledger.types import MemoryConfig, MemoryHit, MemoryRecord


class Runtime:
    """Internal engine instance bound to one namespace."""

    def __init__(
        self,
        namespace: str,
        config: MemoryConfig,
        persist_path: str | None = None,
        agent_id: str | None = None,
    ) -> None:
        self.namespace = namespace
        self.config = config
        self.agent_id = agent_id
        self.policy = InternalPolicy()
        self.compiler = Compiler(namespace)
        self.record_store, self.link_store = make_stores(persist_path)
        self.metrics = Metrics()
        self._restore_metrics()

        # Semantic retriever: silently None if sentence-transformers not installed.
        encoder = make_default_encoder()
        self.semantic = SemanticRetriever(encoder)
        self.keyword = KeywordRetriever()

    # ------------------------------------------------------------------
    # Remember
    # ------------------------------------------------------------------

    def remember(
        self,
        content: str,
        kind: str,
        metadata: dict[str, Any],
        source: str | None,
        timestamp: datetime | None,
        agent_id: str | None = None,
        provenance: str | None = None,
        visibility: str = "local",
    ) -> MemoryRecord:
        with timed() as elapsed:
            embedding = self.semantic.encode(content) if self.semantic.available else None
            internal = self.compiler.compile_record(
                content=content,
                kind=kind,
                metadata=metadata,
                source=source,
                timestamp=timestamp,
                embedding=embedding,
                agent_id=agent_id if agent_id is not None else self.agent_id,
                provenance=provenance,
                visibility=visibility,
            )
            self.record_store.put_record(internal)

        self.metrics.record_remember(elapsed[0])
        self._persist_metrics()

        return MemoryRecord(
            id=internal.id,
            content=internal.content,
            kind=internal.kind,
            metadata=internal.metadata,
            source=internal.source,
            timestamp=internal.timestamp,
            agent_id=internal.agent_id,
            provenance=internal.provenance,
            visibility=internal.visibility,
        )

    # ------------------------------------------------------------------
    # Recall
    # ------------------------------------------------------------------

    def recall(
        self,
        query: str,
        limit: int,
        kind_filter: str | list[str] | None,
        metadata_filter: dict | None,
        min_score: float,
        with_why: bool,
        scope: str = "local",
    ) -> list[MemoryHit]:
        with timed() as elapsed:
            hits, ranked_paths = self._recall_inner(
                query, limit, kind_filter, metadata_filter, min_score, with_why, scope
            )

        path_lengths = [len(p.node_ids) for p, _ in ranked_paths] if ranked_paths else [0]
        self.metrics.record_recall(
            elapsed=elapsed[0],
            hit=len(hits) > 0,
            used_semantic=self.semantic.available,
            path_lengths=path_lengths,
        )
        self._persist_metrics()
        return hits

    def _recall_inner(
        self,
        query: str,
        limit: int,
        kind_filter: str | list[str] | None,
        metadata_filter: dict | None,
        min_score: float,
        with_why: bool,
        scope: str = "local",
    ) -> tuple[list[MemoryHit], list[tuple[ContextPath, float]]]:
        all_records = self.record_store.list_records(self.namespace)
        if not all_records:
            return [], []

        # Apply scope (visibility) filter before kind/metadata filters.
        all_records = _filter_by_scope(all_records, scope, self.agent_id)

        # Apply optional filters before retrieval.
        records = _filter_records(all_records, kind_filter, metadata_filter)
        if not records:
            return [], []

        # Apply decay to activations (lazy, on recall).
        now = datetime.now(timezone.utc)
        for r in records:
            r.activation = apply_decay(
                r.activation,
                r.timestamp,
                now=now,
                half_life_seconds=self.policy.half_life_seconds,
            )

        # Stage 1+2: candidate generation with fallback.
        used_semantic = False
        candidates: list[tuple[str, float]] = []

        if self.semantic.available:
            query_emb = self.semantic.encode(query)
            if query_emb:
                candidates = self.semantic.retrieve(
                    query_emb,
                    records,
                    limit=self.policy.candidate_limit,
                    min_score=0.0,
                )
                used_semantic = bool(candidates)

        if not candidates:
            candidates = self.keyword.retrieve(
                query, records, limit=self.policy.candidate_limit, min_score=0.0
            )

        if not candidates:
            return [], []

        # Scale candidate scores by each seed's learned usefulness prior.
        # This is the primary mechanism by which feedback affects rankings:
        # positive feedback raises usefulness → record scores higher on recall;
        # negative feedback lowers usefulness → record scores lower even if
        # its keyword/semantic score is high.
        candidates = [
            (rid, score * (self.record_store.get_record(rid).usefulness
                           if self.record_store.get_record(rid) else 1.0))
            for rid, score in candidates
        ]
        # Re-sort after usefulness scaling (order may have changed).
        candidates.sort(key=lambda x: x[1], reverse=True)

        # Stage 3: path expansion.
        paths = expand_paths(
            seed_candidates=candidates,
            record_store=self.record_store,
            link_store=self.link_store,
            namespace=self.namespace,
            max_depth=self.policy.path_expansion_depth,
            max_paths=self.policy.path_expansion_max,
        )

        # Stage 4+5: rank and select.
        ranked = rank_paths(
            paths,
            weights=self.policy.ranking_weights,
            limit=limit,
            min_score=min_score,
        )

        hits: list[MemoryHit] = []
        for path, score in ranked:
            seed_id = path.seed_id
            if seed_id is None:
                continue
            record = self.record_store.get_record(seed_id)
            if record is None:
                continue

            why_text: str | None = None
            if with_why or self.config.explain_recall:
                why_text = build_why(path, score, used_semantic)

            hits.append(
                MemoryHit(
                    id=record.id,
                    content=record.content,
                    score=round(score, 4),
                    kind=record.kind,
                    metadata=record.metadata,
                    source=record.source,
                    timestamp=record.timestamp,
                    why=why_text,
                    agent_id=record.agent_id,
                    provenance=record.provenance,
                )
            )

        # Create co-retrieval links between records that appear in the same
        # result set. These links are what feedback later strengthens — they
        # are the graph that path expansion traverses in future recalls.
        hit_ids = [h.id for h in hits]
        for i in range(len(hit_ids)):
            for j in range(i + 1, len(hit_ids)):
                self.ensure_link(hit_ids[i], hit_ids[j])
                self.ensure_link(hit_ids[j], hit_ids[i])

        return hits, ranked

    # ------------------------------------------------------------------
    # Feedback
    # ------------------------------------------------------------------

    def feedback(
        self,
        record_ids: list[str],
        helped: float,
        reason: str | None,
        metadata: dict | None,
    ) -> None:
        self.metrics.record_feedback(helped)
        apply_feedback(
            record_ids=record_ids,
            helped=helped,
            record_store=self.record_store,
            link_store=self.link_store,
            reason=reason,
        )
        self._persist_metrics()
        # Sync mutations back to the store.  apply_feedback mutates InternalRecord
        # and InternalLink objects in-place; for SQLite-backed stores the write-through
        # cache needs an explicit re-put to flush those changes to disk.
        # For in-memory stores this is a cheap identity operation.
        for rid in record_ids:
            record = self.record_store.get_record(rid)
            if record is not None:
                self.record_store.put_record(record)
            for link in self.link_store.get_links_to(rid):
                self.link_store.add_link(link)
            for link in self.link_store.get_links_from(rid):
                self.link_store.add_link(link)

    # ------------------------------------------------------------------
    # Link management — called internally when records are co-retrieved
    # ------------------------------------------------------------------

    def ensure_link(self, source_id: str, target_id: str) -> None:
        """Create a link between two records if it does not already exist."""
        if source_id == target_id:
            return
        if self.link_store.get_link(source_id, target_id) is None:
            self.link_store.add_link(InternalLink(
                source_id=source_id,
                target_id=target_id,
                weight=self.policy.initial_link_weight,
                namespace=self.namespace,
                agent_id=self.agent_id,
            ))


    # ------------------------------------------------------------------
    # Metrics persistence helpers
    # ------------------------------------------------------------------

    def _restore_metrics(self) -> None:
        """Load persisted metrics counters if the store supports it."""
        if hasattr(self.record_store, "load_metrics"):
            saved = self.record_store.load_metrics()
            if saved:
                self.metrics.restore_from(saved)

    def _persist_metrics(self) -> None:
        """Write current metrics to the store if the store supports it."""
        if hasattr(self.record_store, "save_metrics"):
            self.record_store.save_metrics(self.metrics.to_dict())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Explicitly close any open database connections."""
        if hasattr(self.record_store, "close"):
            self.record_store.close()
        if hasattr(self.link_store, "close"):
            self.link_store.close()


def _filter_by_scope(
    records: list[InternalRecord],
    scope: str,
    agent_id: str | None,
) -> list[InternalRecord]:
    """Apply visibility / scope filtering.

    scope="local"  — records owned by this agent (or legacy unattributed records).
    scope="shared" — records explicitly shared by any agent in this namespace.
    scope="merged" — local + shared (union).

    Backward compatibility: records with agent_id=None and visibility="local"
    are treated as unattributed legacy records and are always included in
    scope="local" and scope="merged", regardless of the caller's agent_id.
    """
    if scope == "shared":
        return [r for r in records if r.visibility == "shared"]

    # Local: records owned by this agent, plus legacy unattributed records.
    def _is_local(r: InternalRecord) -> bool:
        if r.visibility != "local":
            return False
        return r.agent_id == agent_id or r.agent_id is None

    if scope == "local":
        return [r for r in records if _is_local(r)]

    # "merged" (and any unrecognised value falls back to merged).
    return [r for r in records if _is_local(r) or r.visibility == "shared"]


def _filter_records(
    records: list[InternalRecord],
    kind_filter: str | list[str] | None,
    metadata_filter: dict | None,
) -> list[InternalRecord]:
    result = records

    if kind_filter is not None:
        kinds = {kind_filter} if isinstance(kind_filter, str) else set(kind_filter)
        result = [r for r in result if r.kind in kinds]

    if metadata_filter:
        result = [
            r
            for r in result
            if all(r.metadata.get(k) == v for k, v in metadata_filter.items())
        ]

    return result
