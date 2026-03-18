"""Phase 3B — governed shared memory tests.

Structure mirrors the spec acceptance criteria:

  TestVisibilityIsolation    — local records are not visible across agent boundaries
  TestSharedRecall           — shared records are visible to all agents in the namespace
  TestMergedScope            — merged recall combines local + shared correctly
  TestProvenanceAndAgentId   — agent_id and provenance survive on returned objects
  TestFeedbackAcrossAgents   — feedback from agent B affects shared record usefulness
  TestConflictingFeedback    — opposing feedback raises uncertainty, does not pick a winner
  TestTwoAgentAcceptance     — the canonical proof moment from the spec
  TestBackwardsCompatibility — Phase 3A behaviour unchanged when agent_id is absent
"""

from __future__ import annotations

import pytest

from neural_ledger import Memory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _shared_db(tmp_path):
    return str(tmp_path / "shared.db")


# ---------------------------------------------------------------------------
# TestVisibilityIsolation
# ---------------------------------------------------------------------------

class TestVisibilityIsolation:
    """Local records are invisible across agent boundaries."""

    def test_local_record_not_visible_to_other_agent(self, tmp_path):
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a") as a:
            a.remember("agent-a private observation", visibility="local")

        with Memory(persist_path=db, agent_id="agent-b") as b:
            hits = b.recall("private observation", limit=5)
            assert not any(h.agent_id == "agent-a" for h in hits), (
                "agent-b must not see agent-a's local records"
            )

    def test_local_record_visible_to_owning_agent(self, tmp_path):
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a") as a:
            r = a.remember("agent-a local note", visibility="local")

        with Memory(persist_path=db, agent_id="agent-a") as a2:
            hits = a2.recall("local note", limit=5)
            assert any(h.id == r.id for h in hits), (
                "agent-a must see its own local records"
            )

    def test_default_visibility_is_local(self, tmp_path):
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a") as a:
            r = a.remember("default visibility record")  # no visibility kwarg

        with Memory(persist_path=db, agent_id="agent-b") as b:
            hits = b.recall("default visibility", limit=5)
            assert not any(h.id == r.id for h in hits), (
                "records default to local — not visible to other agents"
            )

    def test_invalid_visibility_raises(self):
        mem = Memory()
        with pytest.raises(ValueError, match="visibility"):
            mem.remember("test", visibility="public")

    def test_invalid_scope_raises(self):
        mem = Memory()
        mem.remember("test")
        with pytest.raises(ValueError, match="scope"):
            mem.recall("test", scope="everywhere")


# ---------------------------------------------------------------------------
# TestSharedRecall
# ---------------------------------------------------------------------------

class TestSharedRecall:
    """Shared records are visible to all agents in the same namespace."""

    def test_shared_record_visible_to_other_agent(self, tmp_path):
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a") as a:
            r = a.remember(
                "GitHub 401 caused by expired token",
                visibility="shared",
                provenance="run-101",
            )

        with Memory(persist_path=db, agent_id="agent-b") as b:
            hits = b.recall("GitHub 401", scope="shared", limit=5)
            assert any(h.id == r.id for h in hits), (
                "agent-b must see agent-a's shared record"
            )

    def test_shared_scope_in_memory(self):
        """scope='shared' correctly filters visibility on in-memory stores."""
        mem = Memory(agent_id="agent-a")
        r_local  = mem.remember("local in-memory content", visibility="local")
        r_shared = mem.remember("shared in-memory content", visibility="shared")

        hits = mem.recall("in-memory content", scope="shared", limit=5)
        ids = {h.id for h in hits}
        assert r_shared.id in ids, "scope=shared must include shared records (in-memory)"
        assert r_local.id not in ids, "scope=shared must exclude local records (in-memory)"

    def test_shared_record_carries_agent_id(self, tmp_path):
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a") as a:
            r = a.remember("GitHub 401 expired token", visibility="shared")

        with Memory(persist_path=db, agent_id="agent-b") as b:
            hits = b.recall("GitHub 401", scope="shared", limit=5)
            hit = next((h for h in hits if h.id == r.id), None)
            assert hit is not None
            assert hit.agent_id == "agent-a"

    def test_shared_record_carries_provenance(self, tmp_path):
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a") as a:
            r = a.remember(
                "GitHub 401 expired token",
                visibility="shared",
                provenance="incident-42",
            )

        with Memory(persist_path=db, agent_id="agent-b") as b:
            hits = b.recall("GitHub 401", scope="shared", limit=5)
            hit = next((h for h in hits if h.id == r.id), None)
            assert hit is not None
            assert hit.provenance == "incident-42"

    def test_scope_shared_excludes_local_records(self, tmp_path):
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a") as a:
            r_local  = a.remember("local only record", visibility="local")
            r_shared = a.remember("shared content record", visibility="shared")

        with Memory(persist_path=db, agent_id="agent-b") as b:
            hits = b.recall("shared content record", scope="shared", limit=5)
            ids = {h.id for h in hits}
            assert r_shared.id in ids, "scope=shared must include shared records"
            assert r_local.id not in ids, "scope=shared must not include local records"

    def test_local_scope_excludes_other_agents_shared_records(self, tmp_path):
        """scope='local' must not expose shared records from other agents."""
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a") as a:
            r_shared = a.remember("agent-a shared knowledge", visibility="shared")

        with Memory(persist_path=db, agent_id="agent-b") as b:
            hits = b.recall("shared knowledge", scope="local", limit=5)
            assert not any(h.id == r_shared.id for h in hits), (
                "scope=local must not bleed shared records from other agents"
            )

    def test_namespace_isolation_respected(self, tmp_path):
        """Shared records in namespace-A are not visible in namespace-B."""
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a", namespace="ns-a") as a:
            a.remember("shared in ns-a", visibility="shared")

        with Memory(persist_path=db, agent_id="agent-b", namespace="ns-b") as b:
            hits = b.recall("shared", scope="shared", limit=5)
            assert not any(h.agent_id == "agent-a" for h in hits), (
                "namespace boundary must be respected for shared records"
            )


# ---------------------------------------------------------------------------
# TestMergedScope
# ---------------------------------------------------------------------------

class TestMergedScope:
    """Merged recall includes both local and shared records."""

    def test_merged_includes_own_local_and_shared(self, tmp_path):
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a") as a:
            r_local  = a.remember("agent-a local note", visibility="local")
            r_shared = a.remember("agent-a shared fact", visibility="shared")

        with Memory(persist_path=db, agent_id="agent-a") as a2:
            hits = a2.recall("agent", scope="merged", limit=10)
            ids = {h.id for h in hits}
            assert r_local.id in ids,  "merged must include own local records"
            assert r_shared.id in ids, "merged must include own shared records"

    def test_merged_scope_in_memory(self):
        """scope='merged' works with in-memory stores (no SQLite required)."""
        mem = Memory(agent_id="agent-a")
        r_local  = mem.remember("local in-memory note", visibility="local")
        r_shared = mem.remember("shared in-memory fact", visibility="shared")

        hits = mem.recall("memory note fact", scope="merged", limit=10)
        ids = {h.id for h in hits}
        assert r_local.id in ids,  "merged must include own local records (in-memory)"
        assert r_shared.id in ids, "merged must include own shared records (in-memory)"

    def test_merged_includes_other_agents_shared_not_local(self, tmp_path):
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a") as a:
            r_local  = a.remember("agent-a private note", visibility="local")
            r_shared = a.remember("agent-a shared fact", visibility="shared")

        with Memory(persist_path=db, agent_id="agent-b") as b:
            hits = b.recall("note fact agent", scope="merged", limit=10)
            ids = {h.id for h in hits}
            assert r_shared.id in ids,    "merged must include other agents' shared records"
            assert r_local.id not in ids, "merged must not include other agents' local records"


# ---------------------------------------------------------------------------
# TestProvenanceAndAgentId
# ---------------------------------------------------------------------------

class TestProvenanceAndAgentId:
    """agent_id and provenance are set correctly on records and hits."""

    def test_remember_record_carries_agent_id(self, tmp_path):
        mem = Memory(persist_path=_shared_db(tmp_path), agent_id="agent-x")
        r = mem.remember("test content")
        assert r.agent_id == "agent-x"
        mem.close()

    def test_remember_record_carries_provenance(self, tmp_path):
        mem = Memory(persist_path=_shared_db(tmp_path), agent_id="agent-x")
        r = mem.remember("test content", provenance="run-999")
        assert r.provenance == "run-999"
        mem.close()

    def test_remember_record_carries_visibility(self, tmp_path):
        mem = Memory(persist_path=_shared_db(tmp_path), agent_id="agent-x")
        r = mem.remember("test content", visibility="shared")
        assert r.visibility == "shared"
        mem.close()

    def test_hit_carries_agent_id_and_provenance(self, tmp_path):
        db = _shared_db(tmp_path)
        with Memory(persist_path=db, agent_id="agent-a") as a:
            a.remember("shared knowledge", visibility="shared", provenance="run-7")

        with Memory(persist_path=db, agent_id="agent-b") as b:
            hits = b.recall("knowledge", scope="shared", limit=3)
            assert hits
            h = hits[0]
            assert h.agent_id == "agent-a"
            assert h.provenance == "run-7"

    def test_remember_many_forwards_visibility_from_dict(self, tmp_path):
        """remember_many must forward 'visibility' from dict items."""
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a") as a:
            records = a.remember_many([
                {"content": "shared entry", "visibility": "shared"},
                {"content": "local entry"},  # defaults to local
            ])

        assert records[0].visibility == "shared"
        assert records[1].visibility == "local"

        # Cross-agent visibility must match.
        with Memory(persist_path=db, agent_id="agent-b") as b:
            hits = b.recall("shared entry local entry", scope="shared", limit=5)
            ids = {h.id for h in hits}
            assert records[0].id in ids, "shared entry must be visible to agent-b"
            assert records[1].id not in ids, "local entry must not be visible to agent-b"

    def test_remember_many_default_visibility(self, tmp_path):
        """remember_many default_visibility applies to all string items."""
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a") as a:
            records = a.remember_many(
                ["shared one", "shared two"],
                default_visibility="shared",
            )

        assert all(r.visibility == "shared" for r in records)

        with Memory(persist_path=db, agent_id="agent-b") as b:
            hits = b.recall("shared one two", scope="shared", limit=5)
            ids = {h.id for h in hits}
            assert records[0].id in ids or records[1].id in ids, (
                "default_visibility=shared items must be visible to agent-b"
            )

    def test_agent_id_survives_restart(self, tmp_path):
        db = _shared_db(tmp_path)
        with Memory(persist_path=db, agent_id="agent-a") as a:
            r = a.remember("persistent shared fact", visibility="shared")

        with Memory(persist_path=db, agent_id="agent-b") as b:
            hits = b.recall("persistent fact", scope="shared", limit=3)
            hit = next((h for h in hits if h.id == r.id), None)
            assert hit is not None
            assert hit.agent_id == "agent-a"


# ---------------------------------------------------------------------------
# TestFeedbackAcrossAgents
# ---------------------------------------------------------------------------

class TestFeedbackAcrossAgents:
    """Feedback from one agent on a shared record affects future recall."""

    def test_positive_feedback_from_second_agent_raises_usefulness(self, tmp_path):
        db = _shared_db(tmp_path)

        # Agent A writes a shared record.
        with Memory(persist_path=db, agent_id="agent-a") as a:
            r = a.remember("GitHub 401 expired token", visibility="shared")

        # Agent B recalls it and gives positive feedback.
        with Memory(persist_path=db, agent_id="agent-b") as b:
            hits_before = b.recall("GitHub 401", scope="shared", limit=5)
            assert any(h.id == r.id for h in hits_before)
            b.feedback([r.id], helped=1.0)
            usefulness_after = b._runtime.record_store.get_record(r.id).usefulness

        assert usefulness_after > 1.0, (
            "positive feedback from agent-b must raise the shared record's usefulness"
        )

    def test_shared_feedback_usefulness_survives_restart(self, tmp_path):
        """Raised usefulness from agent feedback must survive process restart."""
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a") as a:
            r = a.remember("GitHub 401 expired token", visibility="shared")
            a.feedback([r.id], helped=1.0)
            usefulness_before = a._runtime.record_store.get_record(r.id).usefulness

        # Reopen — usefulness must be restored from SQLite.
        with Memory(persist_path=db, agent_id="agent-a") as a2:
            usefulness_after = a2._runtime.record_store.get_record(r.id).usefulness

        assert usefulness_after == pytest.approx(usefulness_before), (
            "usefulness raised by feedback must survive process restart"
        )
        assert usefulness_after > 1.0, "positive feedback must still be reflected after restart"

    def test_negative_feedback_from_second_agent_lowers_usefulness(self, tmp_path):
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a") as a:
            r = a.remember("GitHub rate limit caused 403", visibility="shared")

        with Memory(persist_path=db, agent_id="agent-b") as b:
            b.recall("GitHub error", scope="shared", limit=5)
            b.feedback([r.id], helped=0.0)
            usefulness_after = b._runtime.record_store.get_record(r.id).usefulness

        assert usefulness_after < 1.0


# ---------------------------------------------------------------------------
# TestConflictingFeedback
# ---------------------------------------------------------------------------

class TestConflictingFeedback:
    """Opposing feedback from two agents raises uncertainty; neither wins silently."""

    def test_conflicting_feedback_raises_link_uncertainty(self, tmp_path):
        db = _shared_db(tmp_path)

        # Agent A creates two shared records, recalls them (creating co-retrieval
        # links r1→r2 and r2→r1), then gives positive feedback on r1.
        # apply_feedback updates *inbound* links to r1 — that is the r2→r1 link.
        with Memory(persist_path=db, agent_id="agent-a") as a:
            r1 = a.remember("GitHub 401 token expired", visibility="shared")
            r2 = a.remember("GitHub 429 rate limit", visibility="shared")
            a.recall("GitHub error", scope="shared", limit=5)  # creates r1↔r2 links
            a.feedback([r1.id], helped=1.0)  # adds evidence [1.0] to r2→r1 inbound link

        # After agent-a's positive feedback: r2→r1 has evidence=[1.0], uncertainty=0.0.
        with Memory(persist_path=db, agent_id="agent-b") as b:
            inbound_before = b._runtime.link_store.get_link(r2.id, r1.id)
            assert inbound_before is not None, (
                "co-retrieval link r2→r1 must exist after agent-a's recall+feedback"
            )
            uncertainty_before = inbound_before.uncertainty

            # Agent B gives conflicting negative feedback on r1.
            b.feedback([r1.id], helped=0.0)  # adds evidence [0.0] to r2→r1 link

            inbound_after = b._runtime.link_store.get_link(r2.id, r1.id)
            assert inbound_after is not None

        # Evidence is now [1.0, 0.0] — maximum conflict → uncertainty must rise.
        assert inbound_after.uncertainty > uncertainty_before, (
            "conflicting feedback (1.0 then 0.0) must raise link uncertainty"
        )

    def test_conflicting_usefulness_stays_near_neutral(self, tmp_path):
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a") as a:
            r = a.remember("GitHub 401 token expired", visibility="shared")
            a.feedback([r.id], helped=1.0)  # agent-a: helpful

        with Memory(persist_path=db, agent_id="agent-b") as b:
            b.feedback([r.id], helped=0.0)  # agent-b: unhelpful
            final_usefulness = b._runtime.record_store.get_record(r.id).usefulness

        # After +0.1 and -0.1, usefulness should be back near 1.0.
        assert 0.8 <= final_usefulness <= 1.2, (
            f"conflicting feedback should leave usefulness near neutral, got {final_usefulness}"
        )


# ---------------------------------------------------------------------------
# TestTwoAgentAcceptance — the canonical proof moment from the spec
# ---------------------------------------------------------------------------

class TestTwoAgentAcceptance:
    """The canonical Phase 3B acceptance scenario.

    Agent A encounters a GitHub 401 failure, stores the root cause as shared.
    Agent B, working the same codebase independently, faces the same error and
    recalls the root cause from the shared pool — complete with attribution.
    Agent B's positive feedback reinforces the shared record.
    """

    def test_agent_b_recalls_agent_a_shared_memory(self, tmp_path):
        db = _shared_db(tmp_path)

        # Agent A's session — diagnoses the failure, shares the root cause.
        with Memory(persist_path=db, agent_id="agent-a") as a:
            r = a.remember(
                "GitHub API 401 caused by expired access token",
                kind="observation",
                visibility="shared",
                provenance="run-123",
            )
            a.feedback([r.id], helped=1.0, reason="Identified the true root cause")

        # Agent B's session — independent, no knowledge of Agent A's specific failure.
        with Memory(persist_path=db, agent_id="agent-b") as b:
            hits = b.recall("GitHub API 401", scope="merged", limit=5)

            assert hits, "agent-b must get results from the shared pool"
            assert any("expired access token" in h.content for h in hits), (
                "agent-b must find agent-a's root-cause record"
            )
            assert any(h.agent_id == "agent-a" for h in hits), (
                "provenance must be visible: agent-b sees the record came from agent-a"
            )
            assert any(h.provenance == "run-123" for h in hits), (
                "run provenance must be preserved in the hit"
            )

            # Agent B also finds the record useful and reinforces it.
            shared_hit = next(
                h for h in hits if "expired access token" in h.content
            )
            b.feedback([shared_hit.id], helped=1.0)
            usefulness = b._runtime.record_store.get_record(shared_hit.id).usefulness

        # After two positive feedback events (A + B), usefulness should be above 1.0.
        assert usefulness > 1.0, (
            f"accumulated positive feedback from two agents should raise usefulness "
            f"above 1.0, got {usefulness}"
        )

    def test_agent_b_does_not_see_agent_a_local_memory(self, tmp_path):
        db = _shared_db(tmp_path)

        with Memory(persist_path=db, agent_id="agent-a") as a:
            r_private = a.remember(
                "agent-a private working hypothesis",
                visibility="local",
            )
            r_shared = a.remember(
                "GitHub 401 expired token — shared finding",
                visibility="shared",
            )

        with Memory(persist_path=db, agent_id="agent-b") as b:
            hits_merged = b.recall("agent hypothesis GitHub", scope="merged", limit=10)
            ids = {h.id for h in hits_merged}

            assert r_private.id not in ids, (
                "local records must never cross agent boundaries"
            )
            assert r_shared.id in ids, (
                "shared records must be visible in merged scope"
            )


# ---------------------------------------------------------------------------
# TestBackwardsCompatibility
# ---------------------------------------------------------------------------

class TestBackwardsCompatibility:
    """Phase 3A behaviour is unchanged when agent_id is absent."""

    def test_memory_without_agent_id_works_unchanged(self):
        mem = Memory()
        r = mem.remember("test record")
        assert r.agent_id is None
        assert r.visibility == "local"
        hits = mem.recall("test record", limit=3)
        assert hits

    def test_local_scope_default_includes_unattributed_records(self):
        """scope='local' includes records with agent_id=None (legacy behaviour)."""
        mem = Memory()
        r = mem.remember("unattributed record")
        hits = mem.recall("unattributed", scope="local", limit=3)
        assert any(h.id == r.id for h in hits)

    def test_existing_tests_unaffected_by_phase3b_fields(self):
        """MemoryRecord and MemoryHit have defaults for new fields — no breaking change."""
        from neural_ledger.types import MemoryHit, MemoryRecord
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        r = MemoryRecord(
            id="x", content="c", kind="note", metadata={}, source=None, timestamp=now
        )
        assert r.agent_id is None
        assert r.visibility == "local"

        h = MemoryHit(
            id="x", content="c", score=0.5, kind="note",
            metadata={}, source=None, timestamp=now
        )
        assert h.agent_id is None
        assert h.provenance is None

    def test_no_agent_id_two_instances_see_each_others_local_records(self, tmp_path):
        """Without agent_id, all local records are unattributed and mutually visible."""
        db = _shared_db(tmp_path)
        with Memory(persist_path=db) as m1:
            r = m1.remember("legacy record")

        with Memory(persist_path=db) as m2:
            hits = m2.recall("legacy record", scope="local", limit=3)
            assert any(h.id == r.id for h in hits), (
                "unattributed records are visible to any unattributed instance "
                "(backward-compatible behaviour)"
            )
