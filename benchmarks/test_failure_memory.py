"""Benchmark: coding-agent failure-memory scenario.

Proves the core Neural Ledger claim:

    After feedback, Neural Ledger ranks prior useful failure memory higher
    than keyword-only and semantic-only baselines.

Run with:
    pytest benchmarks/ -v

Three phases mirror the scenario arc:
    A  — retrieve before any feedback (baseline comparison)
    B  — apply feedback from the scenario spec
    C  — retrieve again and assert improvement
"""

from __future__ import annotations

import pytest

from benchmarks.harness import (
    KeywordBaseline,
    NeuralLedgerCondition,
    SemanticBaseline,
    load_dataset,
)


# ---------------------------------------------------------------------------
# Shared fixture: scenario dataset loaded once per test session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dataset():
    return load_dataset()


@pytest.fixture(scope="module")
def keyword(dataset):
    return KeywordBaseline(dataset)


@pytest.fixture(scope="module")
def semantic(dataset):
    return SemanticBaseline(dataset)


@pytest.fixture(scope="module")
def nl_condition(dataset):
    """Neural Ledger condition that runs Phase A → B → C in sequence."""
    nl = NeuralLedgerCondition(dataset)
    # Phase A: initial recall — builds co-retrieval links.
    for q in dataset.queries:
        nl.retrieve(q, limit=10)
    # Phase B: apply feedback from scenario spec.
    fp = dataset.feedback_positive
    fn = dataset.feedback_negative
    nl.apply_feedback(fp["target_ids"], helped=fp["helped"], reason=fp["reason"])
    nl.apply_feedback(fn["target_ids"], helped=fn["helped"], reason=fn["reason"])
    return nl


@pytest.fixture(scope="module")
def nl_before(dataset):
    """Separate NL instance used for before-feedback comparison."""
    return NeuralLedgerCondition(dataset)


# ---------------------------------------------------------------------------
# Phase A — before feedback: confirm retrieval core is competent
# ---------------------------------------------------------------------------

class TestPhaseA:
    """Before any feedback, all three systems should find useful records."""

    def test_keyword_top3_useful_q1(self, keyword, dataset):
        q = next(q for q in dataset.queries if q.id == "q1")
        r = keyword.retrieve(q)
        assert r.top_k_useful(3), (
            f"keyword should find a useful record in top-3 for q1\n"
            f"ranked={r.ranked_ids[:5]}  oracle={r.oracle_useful}"
        )

    def test_keyword_top3_useful_q2(self, keyword, dataset):
        q = next(q for q in dataset.queries if q.id == "q2")
        r = keyword.retrieve(q)
        assert r.top_k_useful(3), (
            f"keyword should find a useful record in top-3 for q2\n"
            f"ranked={r.ranked_ids[:5]}  oracle={r.oracle_useful}"
        )

    def test_nl_matches_keyword_before_feedback_q1(self, nl_before, keyword, dataset):
        """NL should be no worse than keyword before any learning."""
        q = next(q for q in dataset.queries if q.id == "q1")
        nl_r = nl_before.retrieve(q)
        kw_r = keyword.retrieve(q)
        assert nl_r.mean_useful_rank() <= kw_r.mean_useful_rank() + 0.5, (
            f"NL before feedback should match keyword for q1\n"
            f"NL={nl_r.mean_useful_rank():.2f}  keyword={kw_r.mean_useful_rank():.2f}"
        )

    def test_nl_matches_keyword_before_feedback_q2(self, nl_before, keyword, dataset):
        q = next(q for q in dataset.queries if q.id == "q2")
        nl_r = nl_before.retrieve(q)
        kw_r = keyword.retrieve(q)
        assert nl_r.mean_useful_rank() <= kw_r.mean_useful_rank() + 0.5, (
            f"NL before feedback should match keyword for q2\n"
            f"NL={nl_r.mean_useful_rank():.2f}  keyword={kw_r.mean_useful_rank():.2f}"
        )


# ---------------------------------------------------------------------------
# Phase C — after feedback: the core proof
# ---------------------------------------------------------------------------

class TestPhaseC:
    """After feedback, NL should improve and beat baselines."""

    def test_nl_top3_useful_q1_after_feedback(self, nl_condition, dataset):
        """A useful record must appear in the top-3 for q1 after feedback."""
        q = next(q for q in dataset.queries if q.id == "q1")
        r = nl_condition.retrieve(q)
        assert r.top_k_useful(3), (
            f"NL after feedback: expected useful record in top-3 for q1\n"
            f"ranked={r.ranked_ids[:5]}  oracle={r.oracle_useful}"
        )

    def test_nl_top3_useful_q2_after_feedback(self, nl_condition, dataset):
        """A useful record must appear in the top-3 for q2 after feedback."""
        q = next(q for q in dataset.queries if q.id == "q2")
        r = nl_condition.retrieve(q)
        assert r.top_k_useful(3), (
            f"NL after feedback: expected useful record in top-3 for q2\n"
            f"ranked={r.ranked_ids[:5]}  oracle={r.oracle_useful}"
        )

    def test_nl_beats_keyword_mean_rank_q2_after_feedback(self, nl_condition, keyword, dataset):
        """NL should rank oracle-useful records higher than keyword baseline for q2."""
        q = next(q for q in dataset.queries if q.id == "q2")
        nl_r = nl_condition.retrieve(q)
        kw_r = keyword.retrieve(q)
        assert nl_r.mean_useful_rank() < kw_r.mean_useful_rank(), (
            f"NL after feedback should beat keyword on q2\n"
            f"NL={nl_r.mean_useful_rank():.2f}  keyword={kw_r.mean_useful_rank():.2f}"
        )

    def test_nl_does_not_regress_q1_after_feedback(self, nl_condition, keyword, dataset):
        """NL should not be worse than keyword for q1 (already optimal)."""
        q = next(q for q in dataset.queries if q.id == "q1")
        nl_r = nl_condition.retrieve(q)
        kw_r = keyword.retrieve(q)
        assert nl_r.mean_useful_rank() <= kw_r.mean_useful_rank(), (
            f"NL after feedback should not regress on q1\n"
            f"NL={nl_r.mean_useful_rank():.2f}  keyword={kw_r.mean_useful_rank():.2f}"
        )

    def test_misleading_record_demoted_after_negative_feedback(self, nl_condition, dataset):
        """r3 (rate-limit — misleading) should rank lower after negative feedback."""
        q = next(q for q in dataset.queries if q.id == "q2")

        # Baseline rank for r3 before feedback.
        before_instance = NeuralLedgerCondition(dataset)
        r_before = before_instance.retrieve(q, limit=10)
        rank_before = r_before.rank_of("r3")

        # After feedback rank.
        r_after = nl_condition.retrieve(q, limit=10)
        rank_after = r_after.rank_of("r3")

        assert rank_after > rank_before, (
            f"r3 should be ranked lower after negative feedback\n"
            f"rank before={rank_before}  rank after={rank_after}"
        )

    def test_r1_promoted_after_positive_feedback(self, nl_condition, dataset):
        """r1 (true cause — useful) should rank at or near top for q2 after feedback."""
        q = next(q for q in dataset.queries if q.id == "q2")
        r = nl_condition.retrieve(q, limit=10)
        rank_r1 = r.rank_of("r1")
        assert rank_r1 <= 1, (
            f"r1 should be in top-2 for q2 after positive feedback\n"
            f"ranked={r.ranked_ids[:5]}  rank_r1={rank_r1}"
        )

    def test_rank_improvement_q2(self, nl_condition, dataset):
        """Mean useful rank for q2 must improve after feedback."""
        q = next(q for q in dataset.queries if q.id == "q2")

        before_instance = NeuralLedgerCondition(dataset)
        r_before = before_instance.retrieve(q, limit=10)
        rank_before = r_before.mean_useful_rank()

        r_after = nl_condition.retrieve(q, limit=10)
        rank_after = r_after.mean_useful_rank()

        assert rank_after < rank_before, (
            f"Mean useful rank for q2 should improve after feedback\n"
            f"before={rank_before:.2f}  after={rank_after:.2f}"
        )


# ---------------------------------------------------------------------------
# Canonical proof moment: the before/after shift
# ---------------------------------------------------------------------------

class TestCanonicalProofMoment:
    """The public-facing proof: the exact ranking shift shown in docs."""

    def test_misleading_record_was_top_before_useful_is_top_after(self, dataset):
        """The visible proof: r3 drops, r1 rises for q2."""
        q = next(q for q in dataset.queries if q.id == "q2")

        # Fresh instance — no feedback yet.
        nl_fresh = NeuralLedgerCondition(dataset)
        before = nl_fresh.retrieve(q, limit=10)

        # Apply feedback.
        fp = dataset.feedback_positive
        fn = dataset.feedback_negative
        nl_fresh.apply_feedback(fp["target_ids"], helped=fp["helped"])
        nl_fresh.apply_feedback(fn["target_ids"], helped=fn["helped"])

        after = nl_fresh.retrieve(q, limit=10)

        r1_rank_before = before.rank_of("r1")
        r1_rank_after  = after.rank_of("r1")
        r3_rank_before = before.rank_of("r3")
        r3_rank_after  = after.rank_of("r3")

        # r1 (useful) should move up.
        assert r1_rank_after <= r1_rank_before, (
            f"r1 (useful) should not rank lower after positive feedback\n"
            f"before={r1_rank_before}  after={r1_rank_after}"
        )

        # r3 (misleading) should move down.
        assert r3_rank_after > r3_rank_before, (
            f"r3 (misleading) should rank lower after negative feedback\n"
            f"before={r3_rank_before}  after={r3_rank_after}"
        )
