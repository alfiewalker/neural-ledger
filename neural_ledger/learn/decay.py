"""Freshness decay for memory records.

Over time, a record's activation should weaken unless it is retrieved or
reinforced. This implements the prototype's time-based forgetting pressure.

Design decisions:
  - Exponential decay: well understood and deterministic.
  - Floor at `min_activation` so records never disappear entirely (explicit
    deletion is a later-phase concern, not a v1 side effect).
  - Decay is applied lazily on recall, not on a background timer, which keeps
    v1 simple and fully in-process.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone


# Minimum activation a record can decay to (prevents silent disappearance).
MIN_ACTIVATION: float = 0.05

# Default half-life in seconds: 7 days.
DEFAULT_HALF_LIFE_SECONDS: float = 7 * 24 * 3600


def apply_decay(
    current_activation: float,
    last_interaction: datetime,
    now: datetime | None = None,
    half_life_seconds: float = DEFAULT_HALF_LIFE_SECONDS,
) -> float:
    """Return the decayed activation value.

    Uses exponential decay: A(t) = A₀ * 2^(-t / half_life)
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Make both timestamps timezone-aware for safe subtraction.
    last = _to_utc(last_interaction)
    current = _to_utc(now)

    elapsed = (current - last).total_seconds()
    if elapsed <= 0:
        return current_activation

    decay_factor = math.pow(2.0, -elapsed / half_life_seconds)
    decayed = current_activation * decay_factor
    return max(decayed, MIN_ACTIVATION)


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
