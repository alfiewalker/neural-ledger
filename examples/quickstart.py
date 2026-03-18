"""Neural Ledger — quickstart example.

Demonstrates the three core verbs: remember, recall, feedback.
Run with:
    python examples/quickstart.py
"""

from neural_ledger import Memory

# ── 1. Create a memory (zero setup required) ────────────────────────────────

mem = Memory()

# ── 2. Store some experience ─────────────────────────────────────────────────

mem.remember("User prefers terse weekly updates", kind="preference")
mem.remember(
    "GitHub API request failed with 401 because the access token had expired",
    kind="observation",
    metadata={"tool": "github", "severity": "high"},
)
mem.remember(
    "Refreshing the GitHub token and retrying fixed the 401 error",
    kind="procedure",
    metadata={"tool": "github"},
)
mem.remember("Database connection failed due to an incorrect host value", kind="observation")
mem.remember("Use exponential backoff for transient upstream failures", kind="procedure")

print("Stored 5 memories.\n")

# ── 3. Recall what matters ────────────────────────────────────────────────────

query = "How should I fix this GitHub API 401 failure?"
hits = mem.recall(query, with_why=True, limit=3)

print(f"Query: {query!r}\n")
print("── Top results before feedback ─────────────────────────────────────────")
for i, hit in enumerate(hits, 1):
    print(f"  {i}. [{hit.kind}] {hit.content}")
    print(f"     score={hit.score:.4f}  why: {hit.why}")
print()

# ── 4. Tell the system what helped ───────────────────────────────────────────

# The first two hits were genuinely useful — reinforce them.
mem.feedback(hits[:2], helped=True, reason="Identified the true cause and the fix")

print("Feedback applied (helped=True for the top 2 hits).\n")

# ── 5. Recall again — feedback should have improved or reinforced ranking ─────

hits_after = mem.recall(query, with_why=False, limit=3)

print("── Top results after feedback ──────────────────────────────────────────")
for i, hit in enumerate(hits_after, 1):
    print(f"  {i}. [{hit.kind}] {hit.content}  (score={hit.score:.4f})")
print()

# ── 6. Telemetry summary ──────────────────────────────────────────────────────

print("── Engine telemetry ────────────────────────────────────────────────────")
for key, val in mem.metrics().items():
    print(f"  {key}: {val}")
