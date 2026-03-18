"""Context path expansion.

Starting from a set of seed candidates, follows outgoing links in the graph
to build context paths. A path captures a chain of related records rather
than isolated nearest-neighbour hits, preserving the prototype's graph-aware
behaviour.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neural_ledger.internal.models import InternalLink, InternalRecord
    from neural_ledger.store.in_memory import InMemoryLinkStore, InMemoryRecordStore


@dataclass
class ContextPath:
    """A path of related records rooted at a seed candidate."""

    # Ordered list of record IDs from seed outward.
    node_ids: list[str] = field(default_factory=list)
    # Relevance score of the seed (from semantic or keyword retrieval).
    seed_score: float = 0.0
    # Cumulative link weight along the path.
    total_link_weight: float = 0.0
    # Average activation across all nodes on the path.
    avg_activation: float = 1.0

    @property
    def seed_id(self) -> str | None:
        return self.node_ids[0] if self.node_ids else None


def expand_paths(
    seed_candidates: list[tuple[str, float]],
    record_store: "InMemoryRecordStore",
    link_store: "InMemoryLinkStore",
    namespace: str,
    max_depth: int = 2,
    max_paths: int = 10,
) -> list[ContextPath]:
    """Expand each seed candidate into a context path by following links.

    Uses bounded BFS without revisiting nodes, so cycle-safe by construction.
    Each seed produces at most one path (the best one found by weight).
    """
    paths: list[ContextPath] = []

    for seed_id, seed_score in seed_candidates[:max_paths]:
        seed_record = record_store.get_record(seed_id)
        if seed_record is None or seed_record.namespace != namespace:
            continue

        path = _bfs_best_path(
            start_id=seed_id,
            seed_score=seed_score,
            record_store=record_store,
            link_store=link_store,
            namespace=namespace,
            max_depth=max_depth,
        )
        paths.append(path)

    return paths


def _bfs_best_path(
    start_id: str,
    seed_score: float,
    record_store: "InMemoryRecordStore",
    link_store: "InMemoryLinkStore",
    namespace: str,
    max_depth: int,
) -> ContextPath:
    """BFS from start_id, collecting the highest-weight path up to max_depth."""
    # Each queue entry: (current_id, path_so_far, cumulative_weight, visited)
    best: ContextPath = ContextPath(
        node_ids=[start_id],
        seed_score=seed_score,
        total_link_weight=0.0,
        avg_activation=_activation(start_id, record_store),
    )

    queue: deque[tuple[str, list[str], float, set[str]]] = deque()
    queue.append((start_id, [start_id], 0.0, {start_id}))

    while queue:
        current_id, current_path, current_weight, visited = queue.popleft()

        if len(current_path) - 1 >= max_depth:
            continue

        for link in link_store.get_links_from(current_id):
            target_id = link.target_id
            if target_id in visited:
                continue
            target_record = record_store.get_record(target_id)
            if target_record is None or target_record.namespace != namespace:
                continue

            new_path = current_path + [target_id]
            new_weight = current_weight + link.weight
            new_visited = visited | {target_id}

            # Keep this as the best path if it has higher cumulative weight.
            if new_weight > best.total_link_weight:
                activations = [
                    _activation(nid, record_store) for nid in new_path
                ]
                best = ContextPath(
                    node_ids=new_path,
                    seed_score=seed_score,
                    total_link_weight=new_weight,
                    avg_activation=sum(activations) / len(activations),
                )

            queue.append((target_id, new_path, new_weight, new_visited))

    return best


def _activation(record_id: str, record_store: "InMemoryRecordStore") -> float:
    record = record_store.get_record(record_id)
    return record.activation if record is not None else 0.0
