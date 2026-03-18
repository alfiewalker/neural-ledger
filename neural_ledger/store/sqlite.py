"""SQLite-backed record and link stores.

Write-through caches: operations hit the in-memory dict/graph first (same
access pattern as the in-memory stores), then persist immediately to SQLite.
On __init__, all rows are loaded back from SQLite, so memory survives restart.

Thread-safety: not designed for concurrent access in v1.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import networkx as nx

from neural_ledger.internal.models import InternalLink, InternalRecord


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    id          TEXT    PRIMARY KEY,
    namespace   TEXT    NOT NULL,
    content     TEXT    NOT NULL,
    kind        TEXT    NOT NULL,
    metadata    TEXT    NOT NULL DEFAULT '{}',
    source      TEXT,
    timestamp   TEXT    NOT NULL,
    activation  REAL    NOT NULL DEFAULT 1.0,
    usefulness  REAL    NOT NULL DEFAULT 1.0,
    embedding   TEXT,
    agent_id    TEXT,
    provenance  TEXT,
    visibility  TEXT    NOT NULL DEFAULT 'local'
);

CREATE TABLE IF NOT EXISTS links (
    source_id   TEXT    NOT NULL,
    target_id   TEXT    NOT NULL,
    namespace   TEXT    NOT NULL DEFAULT 'default',
    weight      REAL    NOT NULL DEFAULT 0.5,
    timestamp   TEXT    NOT NULL,
    evidence    TEXT    NOT NULL DEFAULT '[]',
    uncertainty REAL    NOT NULL DEFAULT 0.5,
    agent_id    TEXT,
    PRIMARY KEY (source_id, target_id)
);

CREATE TABLE IF NOT EXISTS metrics (
    key     TEXT    PRIMARY KEY,
    value   TEXT    NOT NULL
);
"""

# Migration statements for databases created before Phase 3B.
# ALTER TABLE ADD COLUMN is idempotent via the try/except guard in _ensure_schema.
_MIGRATIONS = [
    "ALTER TABLE records ADD COLUMN agent_id TEXT",
    "ALTER TABLE records ADD COLUMN provenance TEXT",
    "ALTER TABLE records ADD COLUMN visibility TEXT NOT NULL DEFAULT 'local'",
    "ALTER TABLE links ADD COLUMN agent_id TEXT",
]

_METRICS_KEY = "__metrics__"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Apply schema DDL, pragmas, and idempotent column migrations.

    Safe to call from multiple stores on the same database file — every
    CREATE TABLE uses IF NOT EXISTS, and ALTER TABLE errors (duplicate column)
    are silently ignored.

    Pragmas chosen for Phase 3A (single-writer, local durable persistence):

    * journal_mode=WAL   — Write-Ahead Logging: readers do not block writers;
                           writes are crash-safe at WAL checkpoint boundaries.
    * synchronous=NORMAL — With WAL, NORMAL is crash-safe (no data loss on OS
                           crash or power failure at the WAL level).  FULL is
                           unnecessary overhead for our workload.
    * busy_timeout=5000  — Retry for up to 5 s on SQLITE_BUSY rather than
                           failing immediately.  Protects against the unlikely
                           case of a second process or thread holding a write lock.
    """
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(_SCHEMA)
    # Phase 3B column migrations: add new columns to existing databases.
    # SQLite does not support IF NOT EXISTS on ALTER TABLE ADD COLUMN, so we
    # attempt each and swallow OperationalError when the column already exists.
    for stmt in _MIGRATIONS:
        try:
            conn.execute(stmt)
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already present — no action needed.


def _dt_to_str(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _str_to_dt(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _open_conn(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# SQLiteRecordStore
# ---------------------------------------------------------------------------

class SQLiteRecordStore:
    """Write-through record store backed by SQLite."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._cache: dict[str, InternalRecord] = {}
        self._conn = _open_conn(db_path)
        _ensure_schema(self._conn)
        self._load_all()

    # ------------------------------------------------------------------
    # RecordStore protocol
    # ------------------------------------------------------------------

    def put_record(self, record: InternalRecord) -> None:
        self._cache[record.id] = record
        self._write_record(record)

    def get_record(self, record_id: str) -> InternalRecord | None:
        return self._cache.get(record_id)

    def list_records(self, namespace: str) -> list[InternalRecord]:
        return [r for r in self._cache.values() if r.namespace == namespace]

    def delete_record(self, record_id: str) -> None:
        self._cache.pop(record_id, None)
        self._conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
        self._conn.commit()

    # ------------------------------------------------------------------
    # Metrics persistence (optional extension — not part of RecordStore protocol)
    # ------------------------------------------------------------------

    def save_metrics(self, data: dict) -> None:
        """Persist metrics counters as a single JSON blob."""
        self._conn.execute(
            "INSERT OR REPLACE INTO metrics (key, value) VALUES (?, ?)",
            (_METRICS_KEY, json.dumps(data)),
        )
        self._conn.commit()

    def load_metrics(self) -> dict | None:
        """Return previously persisted metrics counters, or None if absent."""
        row = self._conn.execute(
            "SELECT value FROM metrics WHERE key = ?", (_METRICS_KEY,)
        ).fetchone()
        return json.loads(row["value"]) if row else None

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._cache)

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write_record(self, r: InternalRecord) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO records
                (id, namespace, content, kind, metadata, source,
                 timestamp, activation, usefulness, embedding,
                 agent_id, provenance, visibility)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                r.id,
                r.namespace,
                r.content,
                r.kind,
                json.dumps(r.metadata),
                r.source,
                _dt_to_str(r.timestamp),
                r.activation,
                r.usefulness,
                json.dumps(r.embedding) if r.embedding is not None else None,
                r.agent_id,
                r.provenance,
                r.visibility,
            ),
        )
        self._conn.commit()

    def _load_all(self) -> None:
        for row in self._conn.execute("SELECT * FROM records"):
            keys = row.keys()
            r = InternalRecord(
                id=row["id"],
                namespace=row["namespace"],
                content=row["content"],
                kind=row["kind"],
                metadata=json.loads(row["metadata"]),
                source=row["source"],
                timestamp=_str_to_dt(row["timestamp"]),
                activation=row["activation"],
                usefulness=row["usefulness"],
                embedding=json.loads(row["embedding"]) if row["embedding"] else None,
                agent_id=row["agent_id"] if "agent_id" in keys else None,
                provenance=row["provenance"] if "provenance" in keys else None,
                visibility=row["visibility"] if "visibility" in keys else "local",
            )
            self._cache[r.id] = r


# ---------------------------------------------------------------------------
# SQLiteLinkStore
# ---------------------------------------------------------------------------

class SQLiteLinkStore:
    """Write-through link store backed by SQLite.

    Keeps a networkx DiGraph in memory for traversal and cycle detection,
    with every mutation written through to SQLite immediately.

    Ensures the schema independently — safe to construct before or after
    SQLiteRecordStore on the same database file.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._graph: nx.DiGraph = nx.DiGraph()
        self._conn = _open_conn(db_path)
        _ensure_schema(self._conn)   # idempotent; creates tables if not yet present
        self._load_all()

    # ------------------------------------------------------------------
    # LinkStore protocol
    # ------------------------------------------------------------------

    def add_link(self, link: InternalLink) -> None:
        self._graph.add_edge(link.source_id, link.target_id, link=link)
        self._write_link(link)

    def update_link(self, source_id: str, target_id: str, **attrs: Any) -> None:
        if not self._graph.has_edge(source_id, target_id):
            return
        link: InternalLink = self._graph[source_id][target_id]["link"]
        for key, value in attrs.items():
            if hasattr(link, key):
                setattr(link, key, value)
        self._write_link(link)

    def get_link(self, source_id: str, target_id: str) -> InternalLink | None:
        if self._graph.has_edge(source_id, target_id):
            return self._graph[source_id][target_id]["link"]
        return None

    def get_links_from(self, source_id: str) -> list[InternalLink]:
        if not self._graph.has_node(source_id):
            return []
        return [
            self._graph[source_id][target]["link"]
            for target in self._graph.successors(source_id)
        ]

    def get_links_to(self, target_id: str) -> list[InternalLink]:
        if not self._graph.has_node(target_id):
            return []
        return [
            self._graph[source][target_id]["link"]
            for source in self._graph.predecessors(target_id)
        ]

    def neighbours(self, source_id: str) -> list[str]:
        if not self._graph.has_node(source_id):
            return []
        return list(self._graph.successors(source_id))

    def has_cycle(self) -> bool:
        return not nx.is_directed_acyclic_graph(self._graph)

    def find_cycle(self) -> list[str] | None:
        try:
            return nx.find_cycle(self._graph)  # type: ignore[return-value]
        except nx.NetworkXNoCycle:
            return None

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    def close(self) -> None:
        self._conn.close()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _write_link(self, link: InternalLink) -> None:
        self._conn.execute(
            """
            INSERT OR REPLACE INTO links
                (source_id, target_id, namespace, weight, timestamp, evidence, uncertainty,
                 agent_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                link.source_id,
                link.target_id,
                link.namespace,
                link.weight,
                _dt_to_str(link.timestamp),
                json.dumps(link.evidence),
                link.uncertainty,
                link.agent_id,
            ),
        )
        self._conn.commit()

    def _load_all(self) -> None:
        for row in self._conn.execute("SELECT * FROM links"):
            keys = row.keys()
            link = InternalLink(
                source_id=row["source_id"],
                target_id=row["target_id"],
                namespace=row["namespace"],
                weight=row["weight"],
                timestamp=_str_to_dt(row["timestamp"]),
                evidence=json.loads(row["evidence"]),
                uncertainty=row["uncertainty"],
                agent_id=row["agent_id"] if "agent_id" in keys else None,
            )
            self._graph.add_edge(link.source_id, link.target_id, link=link)
