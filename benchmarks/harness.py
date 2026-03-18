"""Benchmark harness for the coding-agent failure-memory scenario.

Provides:
  - ScenarioLoader: loads the JSON dataset
  - KeywordBaseline: pure token-overlap retrieval, no learning
  - SemanticBaseline: embedding similarity only, no path expansion, no learning
  - NeuralLedgerCondition: full engine with feedback
  - BenchmarkResult / run_benchmark: metrics and the comparison driver
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from neural_ledger import Memory
from neural_ledger.retrieve.keyword import KeywordRetriever
from neural_ledger.internal.models import InternalRecord
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

DATASET_PATH = Path(__file__).parent.parent / "proof" / "datasets" / "coding_agent_failure_memory.json"


@dataclass
class ScenarioRecord:
    id: str
    kind: str
    content: str
    metadata: dict[str, Any]


@dataclass
class ScenarioQuery:
    id: str
    text: str
    oracle_useful: list[str]


@dataclass
class ScenarioDataset:
    records: list[ScenarioRecord]
    queries: list[ScenarioQuery]
    feedback_positive: dict[str, Any]
    feedback_negative: dict[str, Any]


def load_dataset(path: Path = DATASET_PATH) -> ScenarioDataset:
    data = json.loads(path.read_text())
    records = [
        ScenarioRecord(
            id=r["id"],
            kind=r["kind"],
            content=r["content"],
            metadata=r.get("metadata", {}),
        )
        for r in data["records"]
    ]
    queries = [
        ScenarioQuery(
            id=q["id"],
            text=q["text"],
            oracle_useful=q["oracle_useful"],
        )
        for q in data["queries"]
    ]
    return ScenarioDataset(
        records=records,
        queries=queries,
        feedback_positive=data["feedback_positive"],
        feedback_negative=data["feedback_negative"],
    )


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

@dataclass
class QueryResult:
    query_id: str
    ranked_ids: list[str]          # result IDs in rank order (position 0 = best)
    oracle_useful: list[str]

    def rank_of(self, record_id: str) -> int:
        """0-based rank; returns len(ranked_ids) if not found (worst case)."""
        try:
            return self.ranked_ids.index(record_id)
        except ValueError:
            return len(self.ranked_ids)

    def top_k_useful(self, k: int = 3) -> bool:
        """True if any oracle-useful record appears in the top-k results."""
        top_ids = set(self.ranked_ids[:k])
        return bool(top_ids & set(self.oracle_useful))

    def mean_useful_rank(self) -> float:
        """Mean 0-based rank of oracle-useful records (lower = better)."""
        if not self.oracle_useful:
            return 0.0
        ranks = [self.rank_of(uid) for uid in self.oracle_useful]
        return sum(ranks) / len(ranks)


@dataclass
class BenchmarkResult:
    system: str
    phase: str                          # "before_feedback" | "after_feedback"
    query_results: list[QueryResult] = field(default_factory=list)

    def top3_useful(self, query_id: str) -> bool:
        for qr in self.query_results:
            if qr.query_id == query_id:
                return qr.top_k_useful(3)
        return False

    def mean_useful_rank(self, query_id: str) -> float:
        for qr in self.query_results:
            if qr.query_id == query_id:
                return qr.mean_useful_rank()
        return float("inf")

    def summary_row(self, query_id: str) -> dict:
        for qr in self.query_results:
            if qr.query_id == query_id:
                return {
                    "system": self.system,
                    "phase": self.phase,
                    "query": query_id,
                    "top3_useful": qr.top_k_useful(3),
                    "mean_useful_rank": round(qr.mean_useful_rank(), 2),
                    "ranked_ids": qr.ranked_ids[:5],
                }
        return {}


# ---------------------------------------------------------------------------
# Keyword baseline
# ---------------------------------------------------------------------------

class KeywordBaseline:
    """Pure token-overlap retrieval. No learning, no graph, no embeddings."""

    name = "keyword"

    def __init__(self, dataset: ScenarioDataset) -> None:
        now = datetime.now(timezone.utc)
        self._records = [
            InternalRecord(
                id=r.id,
                content=r.content,
                kind=r.kind,
                metadata=r.metadata,
                source=None,
                timestamp=now,
                namespace="baseline",
            )
            for r in dataset.records
        ]
        self._retriever = KeywordRetriever()

    def retrieve(self, query: ScenarioQuery, limit: int = 10) -> QueryResult:
        results = self._retriever.retrieve(query.text, self._records, limit=limit)
        ranked_ids = [rid for rid, _ in results]
        return QueryResult(
            query_id=query.id,
            ranked_ids=ranked_ids,
            oracle_useful=query.oracle_useful,
        )

    def run(self, queries: list[ScenarioQuery]) -> BenchmarkResult:
        result = BenchmarkResult(system=self.name, phase="static")
        for q in queries:
            result.query_results.append(self.retrieve(q))
        return result


# ---------------------------------------------------------------------------
# Semantic-only baseline
# ---------------------------------------------------------------------------

class SemanticBaseline:
    """Embedding similarity only. No path expansion and no feedback learning.

    Falls back to keyword retrieval when sentence-transformers is not installed,
    clearly labelling itself as keyword-fallback so results are not mis-reported.
    """

    def __init__(self, dataset: ScenarioDataset) -> None:
        from neural_ledger.retrieve.semantic import SemanticRetriever, make_default_encoder
        encoder = make_default_encoder()
        self._retriever = SemanticRetriever(encoder)
        self._available = self._retriever.available
        self.name = "semantic" if self._available else "semantic(keyword-fallback)"

        now = datetime.now(timezone.utc)
        self._records = [
            InternalRecord(
                id=r.id,
                content=r.content,
                kind=r.kind,
                metadata=r.metadata,
                source=None,
                timestamp=now,
                namespace="baseline",
            )
            for r in dataset.records
        ]

        # Pre-encode all records.
        if self._available:
            for rec in self._records:
                rec.embedding = self._retriever.encode(rec.content)

        self._kw_fallback = KeywordRetriever()

    def retrieve(self, query: ScenarioQuery, limit: int = 10) -> QueryResult:
        if self._available:
            qemb = self._retriever.encode(query.text)
            results = self._retriever.retrieve(qemb, self._records, limit=limit)
        else:
            results = self._kw_fallback.retrieve(query.text, self._records, limit=limit)
        ranked_ids = [rid for rid, _ in results]
        return QueryResult(
            query_id=query.id,
            ranked_ids=ranked_ids,
            oracle_useful=query.oracle_useful,
        )

    def run(self, queries: list[ScenarioQuery]) -> BenchmarkResult:
        result = BenchmarkResult(system=self.name, phase="static")
        for q in queries:
            result.query_results.append(self.retrieve(q))
        return result


# ---------------------------------------------------------------------------
# Neural Ledger condition
# ---------------------------------------------------------------------------

class NeuralLedgerCondition:
    """Full Neural Ledger engine with co-retrieval links and feedback learning."""

    name = "neural_ledger"

    def __init__(self, dataset: ScenarioDataset) -> None:
        self._dataset = dataset
        # Map stable scenario IDs (r1..r10) to internal Memory record IDs.
        self._id_map: dict[str, str] = {}   # scenario_id -> memory record id
        self._rev_map: dict[str, str] = {}  # memory record id -> scenario_id
        self._mem = Memory()
        self._load_records()

    def _load_records(self) -> None:
        for r in self._dataset.records:
            record = self._mem.remember(
                content=r.content,
                kind=r.kind,
                metadata=r.metadata,
            )
            self._id_map[r.id] = record.id
            self._rev_map[record.id] = r.id

    def retrieve(self, query: ScenarioQuery, limit: int = 10) -> QueryResult:
        hits = self._mem.recall(query.text, limit=limit)
        ranked_scenario_ids = [
            self._rev_map[h.id] for h in hits if h.id in self._rev_map
        ]
        return QueryResult(
            query_id=query.id,
            ranked_ids=ranked_scenario_ids,
            oracle_useful=query.oracle_useful,
        )

    def apply_feedback(
        self,
        target_scenario_ids: list[str],
        helped: float,
        reason: str | None = None,
    ) -> None:
        memory_ids = [
            self._id_map[sid]
            for sid in target_scenario_ids
            if sid in self._id_map
        ]
        if memory_ids:
            self._mem.feedback(memory_ids, helped=helped, reason=reason)

    def run_before(self, queries: list[ScenarioQuery]) -> BenchmarkResult:
        result = BenchmarkResult(system=self.name, phase="before_feedback")
        for q in queries:
            result.query_results.append(self.retrieve(q))
        return result

    def run_after(self, queries: list[ScenarioQuery]) -> BenchmarkResult:
        result = BenchmarkResult(system=self.name, phase="after_feedback")
        for q in queries:
            result.query_results.append(self.retrieve(q))
        return result
