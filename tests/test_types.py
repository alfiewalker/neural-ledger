"""Tests for public dataclasses."""

from datetime import datetime, timezone

from neural_ledger import MemoryConfig, MemoryHit, MemoryRecord


def test_memory_record_fields():
    now = datetime.now(timezone.utc)
    r = MemoryRecord(
        id="abc",
        content="hello",
        kind="note",
        metadata={"key": "val"},
        source="test",
        timestamp=now,
    )
    assert r.id == "abc"
    assert r.content == "hello"
    assert r.kind == "note"
    assert r.metadata == {"key": "val"}
    assert r.source == "test"
    assert r.timestamp == now


def test_memory_hit_why_defaults_to_none():
    now = datetime.now(timezone.utc)
    h = MemoryHit(
        id="x", content="y", score=0.5, kind="note",
        metadata={}, source=None, timestamp=now
    )
    assert h.why is None


def test_memory_config_defaults():
    cfg = MemoryConfig()
    assert cfg.default_limit == 5
    assert cfg.explain_recall is False
    assert cfg.auto_learn_from_feedback is True
    assert cfg.min_score == 0.0
