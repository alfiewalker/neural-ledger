"""Public configuration for Neural Ledger.

Separated from types.py so config can evolve independently of the
return-type dataclasses. Both are re-exported from neural_ledger.__init__.
"""

from neural_ledger.types import MemoryConfig

__all__ = ["MemoryConfig"]
