"""Neural Ledger — coding agent failure memory example.

Demonstrates the canonical proof scenario:

    attempt → failure → remember cause → recall → feedback → better ranking

The scenario: a coding agent previously hit a GitHub API 401 error caused by
an expired access token. Later, facing a similar error, it should recall the
true cause — ranked above misleading near-matches like rate-limit failures.
Positive feedback then reinforces that recall for future encounters.

Run with:
    python examples/coding_agent_failure_memory.py
"""

from __future__ import annotations

import json
from pathlib import Path

from neural_ledger import Memory

# ── Load the scenario dataset ────────────────────────────────────────────────

DATASET = Path(__file__).parent.parent / "proof" / "datasets" / "coding_agent_failure_memory.json"
data = json.loads(DATASET.read_text())

# ── Build memory from scenario records ──────────────────────────────────────

mem = Memory()
record_map: dict[str, str] = {}  # scenario_id → memory record id

for r in data["records"]:
    record = mem.remember(r["content"], kind=r["kind"], metadata=r.get("metadata", {}))
    record_map[r["id"]] = record.id

rev_map = {v: k for k, v in record_map.items()}

print(f"Stored {len(data['records'])} memories.\n")

# ── Helper ───────────────────────────────────────────────────────────────────

def show_results(hits, label: str, oracle_ids: list[str]) -> None:
    print(f"  {label}")
    for i, h in enumerate(hits[:5]):
        sid = rev_map.get(h.id, "?")
        marker = " ◀ useful" if sid in oracle_ids else ""
        print(f"    {i+1}. [{sid}] {h.content[:70]}{marker}")
        print(f"       score={h.score:.4f}")
    print()


def rank_of(hits, scenario_id: str) -> int:
    for i, h in enumerate(hits):
        if rev_map.get(h.id) == scenario_id:
            return i
    return len(hits)


# ── Phase A: recall before feedback ─────────────────────────────────────────

for q in data["queries"]:
    print(f"{'─'*68}")
    print(f"Query [{q['id']}]: {q['text']}")
    print(f"Oracle-useful: {q['oracle_useful']}\n")

    hits = mem.recall(q["text"], limit=5, with_why=True)
    show_results(hits, "Before feedback:", q["oracle_useful"])

# ── Phase B: apply feedback ──────────────────────────────────────────────────

print(f"{'─'*68}")
print("Applying feedback …")

fp = data["feedback_positive"]
fn = data["feedback_negative"]

pos_ids = [record_map[sid] for sid in fp["target_ids"] if sid in record_map]
neg_ids = [record_map[sid] for sid in fn["target_ids"] if sid in record_map]

mem.feedback(pos_ids, helped=fp["helped"],  reason=fp["reason"])
mem.feedback(neg_ids, helped=fn["helped"],  reason=fn["reason"])

print(f"  Positive feedback ({fp['helped']}) → {fp['target_ids']}: {fp['reason']}")
print(f"  Negative feedback ({fn['helped']}) → {fn['target_ids']}: {fn['reason']}")
print()

# ── Phase C: recall after feedback ──────────────────────────────────────────

print(f"{'─'*68}")
print("Results after feedback:\n")

for q in data["queries"]:
    print(f"Query [{q['id']}]: {q['text']}")
    hits_before = mem.recall(q["text"], limit=5)  # fresh recall — no additional feedback
    hits_after  = mem.recall(q["text"], limit=5)
    show_results(hits_after, "After feedback:", q["oracle_useful"])

    # Rank delta table
    print(f"  Rank changes for oracle-useful records:")
    for sid in q["oracle_useful"]:
        # We need before-feedback ranks from Phase A re-run on fresh memory.
        # Here we show current ranking as "after" only (Phase A printed above).
        rank_now = rank_of(hits_after, sid)
        print(f"    {sid}: now at rank {rank_now + 1}")
    print()

# ── Canonical proof moment ───────────────────────────────────────────────────

print(f"{'─'*68}")
print("Canonical proof moment (q2):\n")

q2 = next(q for q in data["queries"] if q["id"] == "q2")

mem_proof = Memory()
id_map_proof: dict[str, str] = {}
for r in data["records"]:
    rec = mem_proof.remember(r["content"], kind=r["kind"])
    id_map_proof[r["id"]] = rec.id
rev_proof = {v: k for k, v in id_map_proof.items()}

def show_proof(hits, label):
    print(f"  {label}")
    for i, h in enumerate(hits[:5]):
        sid = rev_proof.get(h.id, "?")
        marker = " ◀ useful" if sid in q2["oracle_useful"] else ""
        print(f"    {i+1}. [{sid}] {h.content[:70]}{marker}")

before_hits = mem_proof.recall(q2["text"], limit=5)
show_proof(before_hits, "Before feedback:")
print()

mem_proof.feedback(
    [id_map_proof[sid] for sid in fp["target_ids"] if sid in id_map_proof],
    helped=1.0, reason=fp["reason"]
)
mem_proof.feedback(
    [id_map_proof[sid] for sid in fn["target_ids"] if sid in id_map_proof],
    helped=0.0, reason=fn["reason"]
)

after_hits = mem_proof.recall(q2["text"], limit=5)
show_proof(after_hits, "After feedback:")
print()

# Rank deltas
print("  Rank deltas:")
for sid in ["r1", "r2", "r3"]:
    r_before = next((i for i, h in enumerate(before_hits) if rev_proof.get(h.id) == sid), len(before_hits))
    r_after  = next((i for i, h in enumerate(after_hits)  if rev_proof.get(h.id) == sid), len(after_hits))
    delta = r_before - r_after
    direction = "▲ up" if delta > 0 else ("▼ down" if delta < 0 else "— unchanged")
    label = "(useful)" if sid in q2["oracle_useful"] else "(misleading)"
    print(f"    {sid} {label}: rank {r_before+1} → {r_after+1}  ({direction} {abs(delta)})")

print()
print("─" * 68)
print("Telemetry:")
for k, v in mem_proof.metrics().items():
    print(f"  {k}: {v}")
