"""Neural Ledger — two-agent shared memory example.

Demonstrates the Phase 3B model:
  - Agent A encounters a GitHub 401 failure and stores the root cause as shared.
  - Agent B works the same codebase independently, faces the same error, and
    recalls the root cause from the shared pool — complete with attribution.
  - Agent B's positive feedback reinforces the shared record for future agents.

Run with:
    python examples/shared_memory_two_agents.py
"""

import tempfile
import os

from neural_ledger import Memory

# Use a temp file so the example is self-contained and cleans up after itself.
db_file = tempfile.mktemp(suffix=".db", prefix="neural_ledger_demo_")

print("═" * 60)
print("Neural Ledger — two-agent shared memory demo")
print("═" * 60)
print()

# ── Agent A session ──────────────────────────────────────────────────────────
#
# Agent A is working on a deployment pipeline.  It hits a GitHub 401 and
# diagnoses the root cause.  It stores the finding as a shared observation
# so that other agents in the same namespace can benefit from it.

print("[ Agent A session ]")
print()

with Memory(persist_path=db_file, agent_id="agent-a", namespace="ci-pipeline") as agent_a:

    # Agent A also stores some private working notes — these stay local.
    agent_a.remember(
        "Retried request three times before diagnosing the root cause",
        kind="note",
        visibility="local",   # private to agent-a
    )

    # The root cause is stored as shared — worth broadcasting to other agents.
    r = agent_a.remember(
        "GitHub API returned 401 because the access token had expired. "
        "Refreshing the token via the token-refresh endpoint resolved it.",
        kind="observation",
        visibility="shared",
        provenance="run-042",
        metadata={"tool": "github_api", "error_code": "401"},
    )

    print(f"  Stored shared finding (id={r.id[:8]}…)")
    print(f"  visibility : {r.visibility}")
    print(f"  agent_id   : {r.agent_id}")
    print(f"  provenance : {r.provenance}")
    print()

    # Agent A's own recall confirms it can see its own record.
    agent_a.feedback([r.id], helped=True, reason="Confirmed root cause")
    print("  Positive feedback applied by agent-a.")

print()

# ── Agent B session ──────────────────────────────────────────────────────────
#
# Agent B is an independent agent in the same namespace.  It hits the same
# GitHub 401 error and queries the shared pool without knowing about agent-a's
# prior session.

print("[ Agent B session ]")
print()

with Memory(persist_path=db_file, agent_id="agent-b", namespace="ci-pipeline") as agent_b:

    # Agent B queries the merged pool (own local + shared from all agents).
    query = "How do I fix a GitHub API 401 authentication error?"
    hits = agent_b.recall(query, scope="merged", with_why=True, limit=3)

    print(f"  Query: {query!r}")
    print(f"  Results ({len(hits)} hit{'s' if len(hits) != 1 else ''}):\n")

    for i, hit in enumerate(hits, 1):
        print(f"  {i}. {hit.content[:80]}{'…' if len(hit.content) > 80 else ''}")
        print(f"     score={hit.score:.4f}  from agent={hit.agent_id}  "
              f"provenance={hit.provenance}")
        print(f"     why: {hit.why}")
        print()

    # Verify agent-b cannot see agent-a's private notes.
    local_hits = agent_b.recall("retried request diagnose", scope="local", limit=3)
    private_leaked = any("retried request" in h.content for h in local_hits)
    print(f"  Agent-a's private notes visible to agent-b? {private_leaked}  ✓" if not private_leaked
          else "  WARNING: private note leaked to agent-b!")
    print()

    # Agent B finds the shared record useful and reinforces it.
    if hits:
        shared_hit = hits[0]
        agent_b.feedback([shared_hit.id], helped=True, reason="Solved the 401 error")
        usefulness = agent_b._runtime.record_store.get_record(shared_hit.id).usefulness
        print(f"  Feedback applied by agent-b.  Usefulness after two agents: {usefulness:.3f}")
        print(f"  (started at 1.000; two positive feedbacks raised it to {usefulness:.3f})")

print()

# ── Cleanup ──────────────────────────────────────────────────────────────────

try:
    os.unlink(db_file)
except OSError:
    pass

print("═" * 60)
print("Key takeaways:")
print("  • agent_id and provenance are preserved end-to-end.")
print("  • sharing is explicit: local notes never cross agent boundaries.")
print("  • feedback from multiple agents accumulates on the shared record.")
print("  • scope='merged' gives each agent both its own and shared memory.")
print("═" * 60)
