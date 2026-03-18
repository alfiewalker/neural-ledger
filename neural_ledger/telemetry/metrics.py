"""Observational telemetry for the Neural Ledger engine.

Telemetry is strictly observational in v1 — it counts and measures, but does
not alter behaviour. This preserves the prototype's observability without
letting metrics become a hidden second policy engine.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Generator


@dataclass
class Metrics:
    """Counters and rolling averages for engine operations."""

    # Store operations
    remember_count: int = 0

    # Retrieve operations
    recall_count: int = 0
    hit_count: int = 0       # recalls that returned ≥1 result
    miss_count: int = 0      # recalls that returned 0 results
    semantic_used: int = 0   # recalls that used semantic retrieval
    keyword_fallback_used: int = 0  # recalls that fell back to keyword

    # Learning operations
    feedback_positive: int = 0   # feedback calls with helped >= 0.5
    feedback_negative: int = 0   # feedback calls with helped < 0.5
    feedback_total: int = 0

    # Timing (cumulative seconds)
    total_recall_time: float = 0.0
    total_remember_time: float = 0.0

    # Path quality
    total_path_lengths: int = 0   # sum of path node counts across all recalls
    recall_with_paths: int = 0    # recalls where path expansion found >1 node

    def record_remember(self, elapsed: float) -> None:
        self.remember_count += 1
        self.total_remember_time += elapsed

    def record_recall(
        self,
        elapsed: float,
        hit: bool,
        used_semantic: bool,
        path_lengths: list[int],
    ) -> None:
        self.recall_count += 1
        self.total_recall_time += elapsed
        if hit:
            self.hit_count += 1
        else:
            self.miss_count += 1
        if used_semantic:
            self.semantic_used += 1
        else:
            self.keyword_fallback_used += 1
        for pl in path_lengths:
            self.total_path_lengths += pl
            if pl > 1:
                self.recall_with_paths += 1

    def record_feedback(self, helped: float) -> None:
        self.feedback_total += 1
        if helped >= 0.5:
            self.feedback_positive += 1
        else:
            self.feedback_negative += 1

    def avg_recall_time_ms(self) -> float:
        if self.recall_count == 0:
            return 0.0
        return (self.total_recall_time / self.recall_count) * 1000

    def hit_rate(self) -> float:
        if self.recall_count == 0:
            return 0.0
        return self.hit_count / self.recall_count

    def avg_path_length(self) -> float:
        if self.recall_count == 0:
            return 0.0
        return self.total_path_lengths / self.recall_count

    def to_dict(self) -> dict:
        """Export raw counter fields for persistence."""
        return {
            "remember_count": self.remember_count,
            "recall_count": self.recall_count,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "semantic_used": self.semantic_used,
            "keyword_fallback_used": self.keyword_fallback_used,
            "feedback_positive": self.feedback_positive,
            "feedback_negative": self.feedback_negative,
            "feedback_total": self.feedback_total,
            "total_recall_time": self.total_recall_time,
            "total_remember_time": self.total_remember_time,
            "total_path_lengths": self.total_path_lengths,
            "recall_with_paths": self.recall_with_paths,
        }

    def restore_from(self, data: dict) -> None:
        """Restore counter fields from a persisted dict.  Unknown keys are ignored."""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def summary(self) -> dict:
        return {
            "remember_count": self.remember_count,
            "recall_count": self.recall_count,
            "hit_rate": round(self.hit_rate(), 3),
            "miss_count": self.miss_count,
            "semantic_used": self.semantic_used,
            "keyword_fallback_used": self.keyword_fallback_used,
            "feedback_total": self.feedback_total,
            "feedback_positive": self.feedback_positive,
            "feedback_negative": self.feedback_negative,
            "avg_recall_time_ms": round(self.avg_recall_time_ms(), 2),
            "avg_path_length": round(self.avg_path_length(), 2),
        }


@contextmanager
def timed() -> Generator[list[float], None, None]:
    """Context manager that captures elapsed wall time into a single-element list."""
    result: list[float] = [0.0]
    start = time.monotonic()
    try:
        yield result
    finally:
        result[0] = time.monotonic() - start
