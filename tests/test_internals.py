"""Tests for internal engine behaviours that must be preserved from the prototype."""

import math
from datetime import datetime, timedelta, timezone

import pytest

from neural_ledger import Memory
from neural_ledger.learn.confidence import compute_confidence, compute_uncertainty
from neural_ledger.learn.decay import MIN_ACTIVATION, apply_decay
from neural_ledger.retrieve.keyword import KeywordRetriever, _tokenise
from neural_ledger.retrieve.paths import ContextPath, expand_paths
from neural_ledger.retrieve.ranking import RankingWeights, rank_paths, score_path
from neural_ledger.store.in_memory import InMemoryLinkStore, InMemoryRecordStore
from neural_ledger.internal.models import InternalLink, InternalRecord


# ---------------------------------------------------------------------------
# Confidence and uncertainty
# ---------------------------------------------------------------------------

def test_uncertainty_no_evidence():
    assert compute_uncertainty([]) == 0.5


def test_uncertainty_all_positive():
    """Consistent positive evidence should yield low uncertainty."""
    u = compute_uncertainty([1.0, 1.0, 0.9, 1.0])
    assert u < 0.2


def test_uncertainty_all_negative():
    """Consistent negative evidence should also yield low uncertainty."""
    u = compute_uncertainty([0.0, 0.0, 0.1, 0.0])
    assert u < 0.2


def test_uncertainty_conflicting():
    """Conflicting evidence yields higher uncertainty."""
    u_conflict = compute_uncertainty([1.0, 0.0, 1.0, 0.0, 1.0, 0.0])
    u_consistent = compute_uncertainty([1.0, 1.0, 1.0, 1.0])
    assert u_conflict > u_consistent


def test_confidence_is_complement_of_uncertainty():
    evidence = [0.8, 0.9, 0.7]
    assert abs(compute_confidence(evidence) - (1.0 - compute_uncertainty(evidence))) < 1e-9


# ---------------------------------------------------------------------------
# Decay
# ---------------------------------------------------------------------------

def test_decay_reduces_activation():
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=14)  # 2 half-lives
    decayed = apply_decay(1.0, old_time, now=now)
    assert decayed < 1.0


def test_decay_two_halflives_approximately_quarter():
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=14)  # 2 × 7-day half-life
    decayed = apply_decay(1.0, old_time, now=now)
    assert abs(decayed - 0.25) < 0.01


def test_decay_floor_respected():
    """Decay must never go below MIN_ACTIVATION."""
    now = datetime.now(timezone.utc)
    ancient = now - timedelta(days=365 * 10)
    decayed = apply_decay(1.0, ancient, now=now)
    assert decayed >= MIN_ACTIVATION


def test_decay_no_time_passed_unchanged():
    now = datetime.now(timezone.utc)
    activation = apply_decay(0.8, now, now=now)
    assert activation == pytest.approx(0.8, abs=1e-6)


# ---------------------------------------------------------------------------
# Keyword retrieval
# ---------------------------------------------------------------------------

def test_tokenise_removes_stop_words():
    tokens = _tokenise("the quick brown fox")
    assert "the" not in tokens
    assert "quick" in tokens
    assert "fox" in tokens


def test_keyword_retriever_finds_relevant():
    from neural_ledger.internal.models import InternalRecord
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    records = [
        InternalRecord("r1", "GitHub token expired", "obs", {}, None, now, namespace="default"),
        InternalRecord("r2", "Database host wrong", "obs", {}, None, now, namespace="default"),
        InternalRecord("r3", "Slack webhook failed", "obs", {}, None, now, namespace="default"),
    ]
    kr = KeywordRetriever()
    results = kr.retrieve("GitHub token", records, limit=3)
    top_id = results[0][0] if results else None
    assert top_id == "r1"


def test_keyword_retriever_empty_query_returns_records():
    from neural_ledger.internal.models import InternalRecord
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    records = [
        InternalRecord("r1", "something", "note", {}, None, now, namespace="default"),
    ]
    kr = KeywordRetriever()
    # All-stop-word query gracefully returns records rather than crashing.
    results = kr.retrieve("the a an", records, limit=5)
    assert isinstance(results, list)


# ---------------------------------------------------------------------------
# Path expansion
# ---------------------------------------------------------------------------

def test_path_expansion_single_node_no_links():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    rs = InMemoryRecordStore()
    ls = InMemoryLinkStore()
    record = InternalRecord("r1", "some content", "note", {}, None, now, namespace="ns")
    rs.put_record(record)

    paths = expand_paths([("r1", 0.9)], rs, ls, namespace="ns")
    assert len(paths) == 1
    assert paths[0].seed_id == "r1"
    assert paths[0].seed_score == 0.9
    assert paths[0].node_ids == ["r1"]


def test_path_expansion_follows_links():
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    rs = InMemoryRecordStore()
    ls = InMemoryLinkStore()
    for rid in ["r1", "r2", "r3"]:
        rs.put_record(InternalRecord(rid, f"content {rid}", "note", {}, None, now, namespace="ns"))
    ls.add_link(InternalLink("r1", "r2", weight=0.8, namespace="ns"))
    ls.add_link(InternalLink("r2", "r3", weight=0.7, namespace="ns"))

    paths = expand_paths([("r1", 0.9)], rs, ls, namespace="ns", max_depth=2)
    assert len(paths) == 1
    # The path should extend beyond the seed.
    assert len(paths[0].node_ids) > 1


def test_path_expansion_no_cycles():
    """A cycle in the graph must not cause infinite expansion."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    rs = InMemoryRecordStore()
    ls = InMemoryLinkStore()
    for rid in ["r1", "r2"]:
        rs.put_record(InternalRecord(rid, f"content {rid}", "note", {}, None, now, namespace="ns"))
    ls.add_link(InternalLink("r1", "r2", weight=0.8, namespace="ns"))
    ls.add_link(InternalLink("r2", "r1", weight=0.8, namespace="ns"))  # cycle

    paths = expand_paths([("r1", 0.9)], rs, ls, namespace="ns", max_depth=3)
    # Must complete without hanging or crashing.
    assert paths is not None
    # No node should appear twice in a single path.
    for path in paths:
        assert len(path.node_ids) == len(set(path.node_ids))


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def test_ranking_weights_sum_to_one():
    w = RankingWeights()
    assert abs(w.relevance + w.path_bonus + w.activation - 1.0) < 1e-9


def test_ranking_weights_bad_sum_raises():
    with pytest.raises(AssertionError):
        RankingWeights(relevance=0.5, path_bonus=0.5, activation=0.5)


def test_score_path_higher_seed_score_wins():
    w = RankingWeights()
    p_high = ContextPath(node_ids=["a"], seed_score=0.9, total_link_weight=0.0, avg_activation=0.5)
    p_low = ContextPath(node_ids=["b"], seed_score=0.1, total_link_weight=0.0, avg_activation=0.5)
    assert score_path(p_high, w) > score_path(p_low, w)


def test_rank_paths_respects_limit():
    w = RankingWeights()
    paths = [
        ContextPath(node_ids=[f"r{i}"], seed_score=float(i) / 10, total_link_weight=0.0, avg_activation=1.0)
        for i in range(8)
    ]
    ranked = rank_paths(paths, w, limit=3)
    assert len(ranked) <= 3


def test_rank_paths_sorted_descending():
    w = RankingWeights()
    paths = [
        ContextPath(node_ids=["a"], seed_score=0.3, total_link_weight=0.0, avg_activation=1.0),
        ContextPath(node_ids=["b"], seed_score=0.9, total_link_weight=0.0, avg_activation=1.0),
        ContextPath(node_ids=["c"], seed_score=0.6, total_link_weight=0.0, avg_activation=1.0),
    ]
    ranked = rank_paths(paths, w, limit=3)
    scores = [s for _, s in ranked]
    assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------

def test_cycle_detection_no_cycle():
    ls = InMemoryLinkStore()
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    ls.add_link(InternalLink("a", "b", namespace="ns"))
    ls.add_link(InternalLink("b", "c", namespace="ns"))
    assert ls.has_cycle() is False


def test_cycle_detection_with_cycle():
    ls = InMemoryLinkStore()
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    ls.add_link(InternalLink("a", "b", namespace="ns"))
    ls.add_link(InternalLink("b", "c", namespace="ns"))
    ls.add_link(InternalLink("c", "a", namespace="ns"))  # creates cycle
    assert ls.has_cycle() is True


def test_find_cycle_returns_none_when_none():
    ls = InMemoryLinkStore()
    ls.add_link(InternalLink("a", "b", namespace="ns"))
    assert ls.find_cycle() is None


def test_find_cycle_returns_cycle_edges():
    ls = InMemoryLinkStore()
    ls.add_link(InternalLink("a", "b", namespace="ns"))
    ls.add_link(InternalLink("b", "a", namespace="ns"))
    result = ls.find_cycle()
    assert result is not None


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

def test_telemetry_counts_remember():
    mem = Memory()
    mem.remember("one")
    mem.remember("two")
    summary = mem.metrics()
    assert summary["remember_count"] == 2


def test_telemetry_counts_recall():
    mem = Memory()
    mem.remember("something")
    mem.recall("something")
    mem.recall("something else")
    summary = mem.metrics()
    assert summary["recall_count"] == 2


def test_telemetry_counts_feedback():
    mem = Memory()
    mem.remember("item")
    hits = mem.recall("item")
    mem.feedback(hits, helped=True)
    mem.feedback(hits, helped=False)
    summary = mem.metrics()
    assert summary["feedback_total"] == 2
    assert summary["feedback_positive"] == 1
    assert summary["feedback_negative"] == 1
