"""Tests for Memory.feedback() and the learning effect on recall ranking."""

import pytest

from neural_ledger import Memory


def _mem_with_noisy_memories() -> Memory:
    """Set up a memory with one clearly useful record and several noise records."""
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
        "GitHub API rate limit caused a temporary 403 response",
        kind="observation",
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
# Basic feedback acceptance
# ------------------------------------------------------------------

def test_feedback_bool_true_accepted():
    mem = _mem_with_noisy_memories()
    hits = mem.recall("GitHub 401 token")
    mem.feedback(hits, helped=True)  # must not raise


def test_feedback_bool_false_accepted():
    mem = _mem_with_noisy_memories()
    hits = mem.recall("GitHub 401 token")
    mem.feedback(hits, helped=False)


def test_feedback_float_accepted():
    mem = _mem_with_noisy_memories()
    hits = mem.recall("GitHub 401 token")
    mem.feedback(hits, helped=0.8)


def test_feedback_zero_float_accepted():
    mem = _mem_with_noisy_memories()
    hits = mem.recall("GitHub 401")
    mem.feedback(hits, helped=0.0)


def test_feedback_accepts_single_hit():
    mem = _mem_with_noisy_memories()
    hits = mem.recall("GitHub 401 token")
    assert len(hits) > 0
    mem.feedback(hits[0], helped=True)


def test_feedback_accepts_list_of_ids():
    mem = _mem_with_noisy_memories()
    hits = mem.recall("GitHub 401 token")
    ids = [h.id for h in hits]
    mem.feedback(ids, helped=True)


def test_feedback_accepts_single_id_string():
    mem = _mem_with_noisy_memories()
    hits = mem.recall("GitHub 401 token")
    mem.feedback(hits[0].id, helped=True)


def test_feedback_empty_list_does_not_raise():
    mem = _mem_with_noisy_memories()
    mem.feedback([], helped=True)


# ------------------------------------------------------------------
# Validation
# ------------------------------------------------------------------

def test_feedback_helped_too_high_raises():
    mem = _mem_with_noisy_memories()
    hits = mem.recall("GitHub 401 token")
    with pytest.raises(ValueError, match="helped"):
        mem.feedback(hits, helped=1.5)


def test_feedback_helped_negative_raises():
    mem = _mem_with_noisy_memories()
    hits = mem.recall("GitHub 401 token")
    with pytest.raises(ValueError, match="helped"):
        mem.feedback(hits, helped=-0.1)


def test_feedback_bad_type_raises():
    mem = _mem_with_noisy_memories()
    hits = mem.recall("GitHub 401 token")
    with pytest.raises(TypeError):
        mem.feedback(hits, helped="yes")  # type: ignore[arg-type]


# ------------------------------------------------------------------
# Learning effect: positive feedback improves recall rank
# ------------------------------------------------------------------

def test_positive_feedback_improves_rank_of_useful_record():
    """The canonical claim: feedback raises useful records in the ranking."""
    mem = Memory()
    # Plant the useful record and several noise records.
    useful = mem.remember(
        "GitHub API request failed with 401 because the access token had expired",
        kind="observation",
    )
    mem.remember("GitHub API rate limit caused a temporary 403 response", kind="observation")
    mem.remember("Database connection failed due to wrong host", kind="observation")
    mem.remember("Slack webhook failed, signing secret missing", kind="observation")
    mem.remember("CI pipeline failed due to stale lock file", kind="observation")

    query = "How should I fix this GitHub API 401 failure?"

    def rank_of(record_id: str, hits) -> int:
        for i, h in enumerate(hits):
            if h.id == record_id:
                return i
        return 999  # not found

    # Recall before feedback.
    hits_before = mem.recall(query, limit=10)
    rank_before = rank_of(useful.id, hits_before)

    # Apply positive feedback to the useful record.
    mem.feedback(useful.id, helped=True)
    mem.feedback(useful.id, helped=True)
    mem.feedback(useful.id, helped=True)

    # Recall after feedback.
    hits_after = mem.recall(query, limit=10)
    rank_after = rank_of(useful.id, hits_after)

    # The useful record must appear somewhere after feedback.
    assert rank_after < 999, "Useful record not found in results after feedback"
    # Its rank should improve or stay at the top.
    assert rank_after <= rank_before, (
        f"Expected rank to improve after feedback: before={rank_before}, after={rank_after}"
    )


def test_negative_feedback_does_not_crash():
    """Negative feedback must complete without errors."""
    mem = Memory()
    mem.remember("GitHub API rate limit caused a 403")
    hits = mem.recall("GitHub API error")
    mem.feedback(hits, helped=False, reason="Rate limit is not the cause here")
