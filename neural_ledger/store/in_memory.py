"""In-memory implementations of RecordStore and LinkStore.

Uses plain dicts for records and networkx for the link graph.
networkx gives us cycle detection, BFS, and neighbour traversal for free,
while staying fully in-process with no setup friction.
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from neural_ledger.internal.models import InternalLink, InternalRecord


class InMemoryRecordStore:
    """Thread-unsafe in-memory record store keyed by record ID."""

    def __init__(self) -> None:
        self._records: dict[str, InternalRecord] = {}

    # ------------------------------------------------------------------
    # RecordStore protocol
    # ------------------------------------------------------------------

    def put_record(self, record: InternalRecord) -> None:
        self._records[record.id] = record

    def get_record(self, record_id: str) -> InternalRecord | None:
        return self._records.get(record_id)

    def list_records(self, namespace: str) -> list[InternalRecord]:
        return [r for r in self._records.values() if r.namespace == namespace]

    def delete_record(self, record_id: str) -> None:
        self._records.pop(record_id, None)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._records)


class InMemoryLinkStore:
    """In-memory directed graph of links between memory records.

    Each edge stores the full InternalLink as edge data.
    """

    def __init__(self) -> None:
        self._graph: nx.DiGraph = nx.DiGraph()

    # ------------------------------------------------------------------
    # LinkStore protocol
    # ------------------------------------------------------------------

    def add_link(self, link: InternalLink) -> None:
        self._graph.add_edge(
            link.source_id,
            link.target_id,
            link=link,
        )

    def update_link(self, source_id: str, target_id: str, **attrs: Any) -> None:
        if not self._graph.has_edge(source_id, target_id):
            return
        edge_data = self._graph[source_id][target_id]
        link: InternalLink = edge_data["link"]
        for key, value in attrs.items():
            if hasattr(link, key):
                setattr(link, key, value)

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
