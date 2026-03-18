"""Store factory — selects in-memory or SQLite stores based on persist_path."""

from __future__ import annotations

from neural_ledger.store.in_memory import InMemoryLinkStore, InMemoryRecordStore
from neural_ledger.store.sqlite import SQLiteLinkStore, SQLiteRecordStore


def make_stores(
    persist_path: str | None,
) -> tuple[InMemoryRecordStore | SQLiteRecordStore, InMemoryLinkStore | SQLiteLinkStore]:
    """Return (record_store, link_store) appropriate for persist_path.

    If persist_path is None, returns in-memory stores (volatile).
    Otherwise returns SQLite-backed stores that survive restart.
    """
    if persist_path is None:
        return InMemoryRecordStore(), InMemoryLinkStore()
    return SQLiteRecordStore(persist_path), SQLiteLinkStore(persist_path)
