"""Tests for Memory.recall()."""

import pytest

from neural_ledger import Memory, MemoryHit


def _mem_with_github_memories() -> Memory:
    mem = Memory()
    mem.remember(
        "GitHub API request failed with 401 because the access token had expired",
        kind="observation",
    )
    mem.remember(
        "Refreshing the GitHub token and retrying fixed the 401 error",
        kind="procedure",
    )
    mem.remember(
        "Database connection failed due to an incorrect host value",
        kind="observation",
    )
    mem.remember(
        "Use terse bullet points in status updates",
        kind="preference",
    )
    return mem


# ------------------------------------------------------------------
# Basic correctness
# ------------------------------------------------------------------

def test_recall_returns_list_of_hits():
    mem = _mem_with_github_memories()
    hits = mem.recall("GitHub API 401 failure")
    assert isinstance(hits, list)
    assert all(isinstance(h, MemoryHit) for h in hits)


def test_recall_returns_results():
    mem = _mem_with_github_memories()
    hits = mem.recall("GitHub 401 token expired")
    assert len(hits) > 0


def test_recall_scores_are_floats_in_range():
    mem = _mem_with_github_memories()
    hits = mem.recall("GitHub 401 token expired")
    for h in hits:
        assert isinstance(h.score, float)
        assert 0.0 <= h.score <= 1.0


def test_recall_respects_limit():
    mem = _mem_with_github_memories()
    hits = mem.recall("anything", limit=2)
    assert len(hits) <= 2


def test_recall_default_limit_is_five():
    mem = Memory()
    for i in range(10):
        mem.remember(f"memory item {i}")
    hits = mem.recall("memory item")
    assert len(hits) <= 5


def test_recall_empty_store_returns_empty():
    mem = Memory()
    hits = mem.recall("anything")
    assert hits == []


def test_recall_empty_query_raises():
    mem = _mem_with_github_memories()
    with pytest.raises(ValueError, match="query"):
        mem.recall("")


def test_recall_limit_zero_raises():
    mem = _mem_with_github_memories()
    with pytest.raises(ValueError):
        mem.recall("something", limit=0)


# ------------------------------------------------------------------
# Keyword fallback (no embedding model in test env)
# ------------------------------------------------------------------

def test_recall_keyword_fallback_finds_relevant_record():
    """Without sentence-transformers, keyword retrieval must still work."""
    mem = Memory()
    mem.remember("GitHub API request failed with 401 because the access token had expired")
    mem.remember("Database connection error due to wrong host")
    hits = mem.recall("GitHub 401 token")
    # At least one result should mention GitHub.
    assert any("GitHub" in h.content or "github" in h.content.lower() for h in hits)


# ------------------------------------------------------------------
# Filters
# ------------------------------------------------------------------

def test_recall_kind_filter():
    mem = _mem_with_github_memories()
    hits = mem.recall("failed error", kind="preference")
    assert all(h.kind == "preference" for h in hits)


def test_recall_kind_filter_list():
    mem = _mem_with_github_memories()
    hits = mem.recall("error", kind=["observation", "procedure"])
    assert all(h.kind in {"observation", "procedure"} for h in hits)


def test_recall_metadata_filter():
    mem = Memory()
    mem.remember("Tool A failed", metadata={"tool": "A"})
    mem.remember("Tool B failed", metadata={"tool": "B"})
    hits = mem.recall("failed", metadata_filter={"tool": "A"})
    assert all(h.metadata.get("tool") == "A" for h in hits)


# ------------------------------------------------------------------
# with_why
# ------------------------------------------------------------------

def test_recall_with_why_populates_why_field():
    mem = _mem_with_github_memories()
    hits = mem.recall("GitHub token", with_why=True)
    assert len(hits) > 0
    assert all(isinstance(h.why, str) and len(h.why) > 0 for h in hits)


def test_recall_without_why_leaves_why_none():
    mem = _mem_with_github_memories()
    hits = mem.recall("GitHub token", with_why=False)
    assert all(h.why is None for h in hits)


# ------------------------------------------------------------------
# Namespace isolation
# ------------------------------------------------------------------

def test_namespaces_are_isolated():
    mem_a = Memory(namespace="a")
    mem_b = Memory(namespace="b")
    mem_a.remember("secret for A only")
    hits = mem_b.recall("secret for A only")
    assert len(hits) == 0
