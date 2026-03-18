"""Phase 3 persistence tests.

Two test groups:

  TestRestartSurvival — the canonical Phase 3 acceptance criterion:
    create → write records → apply feedback → shut down → reopen →
    confirm records, usefulness, links, and metrics survive.

  TestParityWithInMemory — same operations on both backends produce
    the same recall results, ensuring the SQLite path is a faithful
    implementation of the in-memory behaviour.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from neural_ledger import Memory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db_path(tmp_path: Path) -> str:
    return str(tmp_path / "test_memory.db")


# ---------------------------------------------------------------------------
# TestRestartSurvival
# ---------------------------------------------------------------------------

class TestRestartSurvival:
    """Records, usefulness, links, and metrics survive process restart."""

    def test_records_survive_restart(self, tmp_path):
        db = _make_db_path(tmp_path)

        mem = Memory(persist_path=db)
        r1 = mem.remember("GitHub API 401 caused by expired token", kind="observation")
        r2 = mem.remember("Refreshing token fixed the 401 error", kind="procedure")
        del mem  # simulate process death

        mem2 = Memory(persist_path=db)
        hits = mem2.recall("GitHub API 401", limit=10)
        ids = {h.id for h in hits}

        assert r1.id in ids, "r1 must survive restart"
        assert r2.id in ids, "r2 must survive restart"

    def test_record_fields_survive_restart(self, tmp_path):
        db = _make_db_path(tmp_path)

        mem = Memory(persist_path=db)
        r = mem.remember(
            "Rate limit caused 403",
            kind="warning",
            metadata={"code": 403, "service": "github"},
            source="agent-1",
        )
        del mem

        mem2 = Memory(persist_path=db)
        hits = mem2.recall("rate limit 403", limit=5)
        assert hits, "record must be recalled after restart"
        h = next(h for h in hits if h.id == r.id)

        assert h.kind == "warning"
        assert h.metadata["code"] == 403
        assert h.metadata["service"] == "github"
        assert h.source == "agent-1"

    def test_usefulness_survives_restart(self, tmp_path):
        """Positive feedback raises usefulness; that value must survive restart."""
        db = _make_db_path(tmp_path)

        mem = Memory(persist_path=db)
        r = mem.remember("Expired token was the root cause", kind="observation")
        mem.feedback([r.id], helped=1.0)
        # Retrieve internal usefulness from the store before closing.
        usefulness_before = mem._runtime.record_store.get_record(r.id).usefulness
        del mem

        mem2 = Memory(persist_path=db)
        record_after = mem2._runtime.record_store.get_record(r.id)
        assert record_after is not None
        assert record_after.usefulness == pytest.approx(usefulness_before, abs=1e-9)

    def test_negative_feedback_usefulness_survives_restart(self, tmp_path):
        """Negative feedback lowers usefulness; persists across restart."""
        db = _make_db_path(tmp_path)

        mem = Memory(persist_path=db)
        r = mem.remember("Rate limit was the cause", kind="observation")
        mem.feedback([r.id], helped=0.0)
        usefulness_before = mem._runtime.record_store.get_record(r.id).usefulness
        assert usefulness_before < 1.0
        del mem

        mem2 = Memory(persist_path=db)
        record_after = mem2._runtime.record_store.get_record(r.id)
        assert record_after.usefulness == pytest.approx(usefulness_before, abs=1e-9)

    def test_links_survive_restart(self, tmp_path):
        """Co-retrieval links written during recall survive restart."""
        db = _make_db_path(tmp_path)

        mem = Memory(persist_path=db)
        mem.remember("Token expired caused 401", kind="observation")
        mem.remember("Refreshing token fixed 401", kind="procedure")
        # Trigger co-retrieval linking.
        mem.recall("GitHub 401", limit=5)
        link_count_before = mem._runtime.link_store.edge_count()
        assert link_count_before > 0, "links must be created by co-retrieval"
        del mem

        mem2 = Memory(persist_path=db)
        assert mem2._runtime.link_store.edge_count() == link_count_before

    def test_link_weights_after_feedback_survive_restart(self, tmp_path):
        """Link weights mutated by positive feedback survive restart."""
        db = _make_db_path(tmp_path)

        mem = Memory(persist_path=db)
        r1 = mem.remember("Token expired caused 401", kind="observation")
        r2 = mem.remember("Refreshing token fixed 401", kind="procedure")
        mem.recall("GitHub 401", limit=5)  # creates co-retrieval links
        mem.feedback([r1.id, r2.id], helped=1.0)

        link = mem._runtime.link_store.get_link(r1.id, r2.id)
        assert link is not None
        weight_before = link.weight
        del mem

        mem2 = Memory(persist_path=db)
        link_after = mem2._runtime.link_store.get_link(r1.id, r2.id)
        assert link_after is not None
        assert link_after.weight == pytest.approx(weight_before, abs=1e-9)

    def test_link_evidence_survives_restart(self, tmp_path):
        """Evidence list on a link survives restart."""
        db = _make_db_path(tmp_path)

        mem = Memory(persist_path=db)
        r1 = mem.remember("Token expired caused 401", kind="observation")
        r2 = mem.remember("Refreshing token fixed 401", kind="procedure")
        mem.recall("GitHub 401", limit=5)
        mem.feedback([r1.id, r2.id], helped=1.0)
        mem.feedback([r1.id], helped=0.0)

        link = mem._runtime.link_store.get_link(r1.id, r2.id)
        evidence_before = list(link.evidence)
        del mem

        mem2 = Memory(persist_path=db)
        link_after = mem2._runtime.link_store.get_link(r1.id, r2.id)
        assert link_after.evidence == evidence_before

    def test_full_restart_cycle(self, tmp_path):
        """End-to-end: write → feedback → restart → recall shows learned ranking."""
        db = _make_db_path(tmp_path)

        # Session 1: store memories, apply feedback.
        mem = Memory(persist_path=db)
        r_useful   = mem.remember("GitHub 401 caused by expired access token")
        r_mislead  = mem.remember("GitHub 429 caused by rate limit")
        r_noise    = mem.remember("Postgres connection timed out")

        mem.recall("GitHub API error 401", limit=5)  # creates links
        mem.feedback([r_useful.id],  helped=1.0)
        mem.feedback([r_mislead.id], helped=0.0)
        del mem

        # Session 2: fresh Memory from same db.
        mem2 = Memory(persist_path=db)
        hits = mem2.recall("GitHub API error 401", limit=5)
        assert hits, "must return hits after restart"

        ids = [h.id for h in hits]
        assert r_useful.id in ids, "useful record must be recalled"

        # Useful record should rank ahead of misleading one.
        if r_mislead.id in ids:
            rank_useful  = ids.index(r_useful.id)
            rank_mislead = ids.index(r_mislead.id)
            assert rank_useful < rank_mislead, (
                "useful record should rank higher than misleading after feedback+restart"
            )


# ---------------------------------------------------------------------------
# TestParityWithInMemory
# ---------------------------------------------------------------------------

class TestParityWithInMemory:
    """SQLite backend produces results consistent with in-memory backend."""

    def _setup_both(self, tmp_path, contents: list[str]) -> tuple[Memory, Memory]:
        db = _make_db_path(tmp_path)
        mem_im = Memory()
        mem_sq = Memory(persist_path=db)
        for c in contents:
            mem_im.remember(c)
            mem_sq.remember(c)
        return mem_im, mem_sq

    def test_recall_returns_same_count(self, tmp_path):
        contents = [
            "GitHub API 401 — expired token",
            "GitHub API rate limit 429",
            "Database connection error",
        ]
        mem_im, mem_sq = self._setup_both(tmp_path, contents)

        hits_im = mem_im.recall("GitHub 401", limit=5)
        hits_sq = mem_sq.recall("GitHub 401", limit=5)

        assert len(hits_im) == len(hits_sq), (
            f"in-memory returned {len(hits_im)} hits, SQLite returned {len(hits_sq)}"
        )

    def test_feedback_improves_ranking_on_sqlite(self, tmp_path):
        """Positive feedback raises a record's rank on the SQLite backend."""
        db = _make_db_path(tmp_path)
        mem = Memory(persist_path=db)

        r_target = mem.remember("GitHub 401 caused by expired token")
        mem.remember("GitHub 429 rate limit error")
        mem.remember("Postgres connection failed")

        hits_before = mem.recall("GitHub API error", limit=5)
        rank_before = next(
            (i for i, h in enumerate(hits_before) if h.id == r_target.id),
            len(hits_before),
        )

        mem.feedback([r_target.id], helped=1.0)
        hits_after = mem.recall("GitHub API error", limit=5)
        rank_after = next(
            (i for i, h in enumerate(hits_after) if h.id == r_target.id),
            len(hits_after),
        )

        assert rank_after <= rank_before, (
            f"positive feedback should not lower rank: before={rank_before} after={rank_after}"
        )

    def test_sqlite_recall_scores_nonzero(self, tmp_path):
        db = _make_db_path(tmp_path)
        mem = Memory(persist_path=db)
        mem.remember("GitHub token expired caused 401 error")
        hits = mem.recall("GitHub 401 token", limit=3)
        assert hits
        assert all(h.score > 0 for h in hits)

    def test_multiple_namespaces_isolated(self, tmp_path):
        """Different namespaces in the same SQLite file remain isolated."""
        db = _make_db_path(tmp_path)

        mem_a = Memory(persist_path=db, namespace="agent-a")
        mem_b = Memory(persist_path=db, namespace="agent-b")

        mem_a.remember("GitHub token expired 401")
        mem_b.remember("Postgres connection refused")

        hits_a = mem_a.recall("GitHub 401", limit=5)
        hits_b = mem_b.recall("GitHub 401", limit=5)

        ids_a = {h.id for h in hits_a}
        ids_b = {h.id for h in hits_b}

        assert ids_a.isdisjoint(ids_b), (
            "namespaces must be isolated; no record should appear in both"
        )

    def test_context_manager_closes_connection(self, tmp_path):
        """Memory used as a context manager closes cleanly."""
        db = _make_db_path(tmp_path)
        with Memory(persist_path=db) as mem:
            mem.remember("Token expired caused 401")

        # Reopen and verify data is still accessible.
        with Memory(persist_path=db) as mem2:
            hits = mem2.recall("token expired", limit=3)
            assert hits

    def test_remember_many_survives_restart(self, tmp_path):
        db = _make_db_path(tmp_path)
        mem = Memory(persist_path=db)
        records = mem.remember_many([
            "GitHub 401 expired token",
            "GitHub 429 rate limit",
            "Postgres timeout",
        ])
        ids_stored = {r.id for r in records}
        del mem

        mem2 = Memory(persist_path=db)
        hits = mem2.recall("GitHub error", limit=10)
        ids_recalled = {h.id for h in hits}
        assert ids_stored & ids_recalled, "at least one record_many item must survive"


# ---------------------------------------------------------------------------
# TestMetricsPersistence
# ---------------------------------------------------------------------------

class TestMetricsPersistence:
    """Telemetry counters survive restart on SQLite-backed instances."""

    def test_remember_count_survives_restart(self, tmp_path):
        db = _make_db_path(tmp_path)

        with Memory(persist_path=db) as mem:
            mem.remember("Record one")
            mem.remember("Record two")
            mem.remember("Record three")
            count_before = mem.metrics()["remember_count"]

        assert count_before == 3

        with Memory(persist_path=db) as mem2:
            assert mem2.metrics()["remember_count"] == count_before

    def test_recall_count_survives_restart(self, tmp_path):
        db = _make_db_path(tmp_path)

        with Memory(persist_path=db) as mem:
            mem.remember("GitHub 401 expired token")
            mem.recall("GitHub 401", limit=3)
            mem.recall("token error", limit=3)
            count_before = mem.metrics()["recall_count"]

        with Memory(persist_path=db) as mem2:
            assert mem2.metrics()["recall_count"] == count_before

    def test_feedback_counts_survive_restart(self, tmp_path):
        db = _make_db_path(tmp_path)

        with Memory(persist_path=db) as mem:
            r = mem.remember("GitHub 401 expired token")
            mem.feedback([r.id], helped=1.0)
            mem.feedback([r.id], helped=0.0)
            m_before = mem.metrics()

        with Memory(persist_path=db) as mem2:
            m_after = mem2.metrics()
            assert m_after["feedback_total"]    == m_before["feedback_total"]
            assert m_after["feedback_positive"] == m_before["feedback_positive"]
            assert m_after["feedback_negative"] == m_before["feedback_negative"]

    def test_metrics_accumulate_across_sessions(self, tmp_path):
        """Counters from session 1 and session 2 stack correctly."""
        db = _make_db_path(tmp_path)

        with Memory(persist_path=db) as mem:
            mem.remember("Record A")
            mem.remember("Record B")

        with Memory(persist_path=db) as mem2:
            mem2.remember("Record C")
            total = mem2.metrics()["remember_count"]

        assert total == 3

    def test_in_memory_metrics_not_persisted(self, tmp_path):
        """In-memory instances never write to a file; metrics always start fresh."""
        mem1 = Memory()
        mem1.remember("something")
        assert mem1.metrics()["remember_count"] == 1

        mem2 = Memory()
        assert mem2.metrics()["remember_count"] == 0


# ---------------------------------------------------------------------------
# TestDurabilityAndLifecycle
# ---------------------------------------------------------------------------

class TestDurabilityAndLifecycle:
    """Durability and lifecycle edge cases for Phase 3A.

    Phase 3A is single-node, single-writer, local durable persistence.
    These tests document the supported behaviour and the boundaries
    of what is and is not guaranteed.
    """

    def test_data_durable_without_explicit_close(self, tmp_path):
        """Records are readable after restart even when close() was not called.

        Every write commits to SQLite immediately.  close() is a courtesy
        flush; durability does not depend on it.
        """
        db = _make_db_path(tmp_path)
        mem = Memory(persist_path=db)
        r = mem.remember("GitHub 401 expired token")
        # Deliberately NOT calling mem.close() — simulate abrupt process exit.
        del mem

        mem2 = Memory(persist_path=db)
        hits = mem2.recall("GitHub 401", limit=5)
        assert any(h.id == r.id for h in hits), (
            "record must be readable after restart even without explicit close()"
        )
        mem2.close()

    def test_second_instance_on_same_file_reads_prior_writes(self, tmp_path):
        """A second Memory instance opened after writes are committed sees those records."""
        db = _make_db_path(tmp_path)

        mem1 = Memory(persist_path=db)
        r = mem1.remember("Record written by first instance")

        # Open a second instance — it reads from SQLite on init.
        mem2 = Memory(persist_path=db)
        hits = mem2.recall("written by first", limit=5)
        assert any(h.id == r.id for h in hits), (
            "second instance must see records committed by first instance"
        )
        mem1.close()
        mem2.close()

    def test_close_then_reopen_is_safe(self, tmp_path):
        """Explicit close() followed by a fresh open leaves data intact."""
        db = _make_db_path(tmp_path)

        with Memory(persist_path=db) as mem:
            r = mem.remember("Close and reopen test")

        with Memory(persist_path=db) as mem2:
            hits = mem2.recall("close reopen", limit=3)
            assert any(h.id == r.id for h in hits)

    def test_multiple_sessions_accumulate_correctly(self, tmp_path):
        """Records and metrics stack across three independent sessions."""
        db = _make_db_path(tmp_path)

        with Memory(persist_path=db) as m:
            m.remember("Session 1 record A")
            m.remember("Session 1 record B")

        with Memory(persist_path=db) as m:
            m.remember("Session 2 record C")
            m.recall("session record", limit=5)

        with Memory(persist_path=db) as m:
            hits = m.recall("session record", limit=10)
            met = m.metrics()

        # All three records should be findable.
        assert len(hits) >= 3, f"expected ≥3 records, got {len(hits)}"
        # Cumulative counters should reflect all three sessions.
        assert met["remember_count"] == 3
        assert met["recall_count"] >= 2  # at least session 2 + session 3

    def test_feedback_usefulness_and_links_atomic_enough(self, tmp_path):
        """After feedback + restart, both usefulness AND link evidence are consistent.

        Note: feedback is not a single database transaction in Phase 3A.
        Usefulness and link writes are committed separately.  This test
        verifies the observable outcome (both survive) not strict atomicity.
        """
        db = _make_db_path(tmp_path)

        with Memory(persist_path=db) as mem:
            r1 = mem.remember("Expired token caused 401")
            r2 = mem.remember("Refreshing token fixed 401")
            mem.recall("GitHub 401", limit=5)  # creates co-retrieval links
            mem.feedback([r1.id, r2.id], helped=1.0)

            usefulness_before = mem._runtime.record_store.get_record(r1.id).usefulness
            link = mem._runtime.link_store.get_link(r1.id, r2.id)
            evidence_before = list(link.evidence) if link else []

        with Memory(persist_path=db) as mem2:
            u_after = mem2._runtime.record_store.get_record(r1.id).usefulness
            link_after = mem2._runtime.link_store.get_link(r1.id, r2.id)
            evidence_after = list(link_after.evidence) if link_after else []

        assert u_after == pytest.approx(usefulness_before, abs=1e-9), (
            "usefulness must survive alongside link evidence"
        )
        assert evidence_after == evidence_before, (
            "link evidence must survive alongside usefulness"
        )


# ---------------------------------------------------------------------------
# TestSchemaRobustness
# ---------------------------------------------------------------------------

class TestSchemaRobustness:
    """Schema creation is independent and idempotent across both stores."""

    def test_link_store_can_be_created_on_existing_db(self, tmp_path):
        """SQLiteLinkStore initialised after SQLiteRecordStore finds schema already set up."""
        from neural_ledger.store.sqlite import SQLiteRecordStore, SQLiteLinkStore

        db = _make_db_path(tmp_path)
        rs = SQLiteRecordStore(db)
        ls = SQLiteLinkStore(db)   # must not raise OperationalError

        rs.close()
        ls.close()

    def test_link_store_ensures_schema_independently(self, tmp_path):
        """SQLiteLinkStore created on a blank file sets up schema without SQLiteRecordStore."""
        from neural_ledger.store.sqlite import SQLiteLinkStore

        db = _make_db_path(tmp_path)
        ls = SQLiteLinkStore(db)   # must not raise OperationalError
        ls.close()

    def test_schema_is_idempotent(self, tmp_path):
        """Opening the same database twice does not corrupt schema."""
        db = _make_db_path(tmp_path)

        with Memory(persist_path=db) as mem:
            r = mem.remember("First session record")

        with Memory(persist_path=db) as mem2:
            mem2.remember("Second session record")
            hits = mem2.recall("session record", limit=5)
            assert len(hits) >= 1
