"""Tests for Memory.remember() and Memory.remember_many()."""

import pytest

from neural_ledger import Memory, MemoryRecord


def make_mem() -> Memory:
    return Memory()


# ------------------------------------------------------------------
# remember()
# ------------------------------------------------------------------

def test_remember_returns_memory_record():
    mem = make_mem()
    record = mem.remember("User prefers terse updates")
    assert isinstance(record, MemoryRecord)


def test_remember_assigns_unique_ids():
    mem = make_mem()
    r1 = mem.remember("first memory")
    r2 = mem.remember("second memory")
    assert r1.id != r2.id


def test_remember_stores_content_and_kind():
    mem = make_mem()
    r = mem.remember("GitHub token expired", kind="observation")
    assert r.content == "GitHub token expired"
    assert r.kind == "observation"


def test_remember_default_kind_is_note():
    mem = make_mem()
    r = mem.remember("some note")
    assert r.kind == "note"


def test_remember_stores_metadata():
    mem = make_mem()
    r = mem.remember("API failed", metadata={"tool": "github", "severity": "high"})
    assert r.metadata["tool"] == "github"
    assert r.metadata["severity"] == "high"


def test_remember_empty_content_raises():
    mem = make_mem()
    with pytest.raises(ValueError, match="content"):
        mem.remember("")


def test_remember_whitespace_only_raises():
    mem = make_mem()
    with pytest.raises(ValueError, match="content"):
        mem.remember("   ")


def test_remember_empty_kind_raises():
    mem = make_mem()
    with pytest.raises(ValueError, match="kind"):
        mem.remember("valid content", kind="")


def test_remember_timestamp_is_set():
    mem = make_mem()
    r = mem.remember("something")
    assert r.timestamp is not None


# ------------------------------------------------------------------
# remember_many()
# ------------------------------------------------------------------

def test_remember_many_strings():
    mem = make_mem()
    records = mem.remember_many(["first", "second", "third"])
    assert len(records) == 3
    assert all(isinstance(r, MemoryRecord) for r in records)
    assert records[0].content == "first"


def test_remember_many_dicts():
    mem = make_mem()
    records = mem.remember_many([
        {"content": "prefer terse updates", "kind": "preference"},
        {"content": "token expired", "kind": "observation"},
    ])
    assert records[0].kind == "preference"
    assert records[1].kind == "observation"


def test_remember_many_empty_list():
    mem = make_mem()
    assert mem.remember_many([]) == []


def test_remember_many_all_ids_unique():
    mem = make_mem()
    records = mem.remember_many(["a", "b", "c", "d"])
    ids = [r.id for r in records]
    assert len(ids) == len(set(ids))


def test_remember_many_bad_type_raises():
    mem = make_mem()
    with pytest.raises(TypeError):
        mem.remember_many([123])  # type: ignore[list-item]
