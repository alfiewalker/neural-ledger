"""Neural Ledger — a lightweight memory engine.

Memory is not storage. It is judgement.

Public API::

    from neural_ledger import Memory, MemoryRecord, MemoryHit, MemoryConfig

The Memory class is the only class most users ever need.
"""

from neural_ledger.api import Memory
from neural_ledger.types import MemoryConfig, MemoryHit, MemoryRecord

__all__ = ["Memory", "MemoryRecord", "MemoryHit", "MemoryConfig"]
__version__ = "0.1.0a1"
