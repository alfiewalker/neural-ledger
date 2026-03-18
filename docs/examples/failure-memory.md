# Failure Memory — Coding Agent Example

A coding agent previously hit a GitHub API 401 error caused by an expired access token.
Later, facing the same symptom, it needs to recall the **true cause** — not a superficially
similar record about rate-limit failures that shares the same domain vocabulary.

This is the canonical proof scenario for Neural Ledger:
> The system learns from feedback which past experience is actually useful,
> and ranks it higher on future encounters.

---

## The problem with keyword retrieval

A keyword search for `"GitHub API 401 authentication failure"` returns records scored on
token overlap. A record about *rate-limit failures* (`r3`) shares the words `GitHub`, `API`,
and `failure` with the query. It scores just as high as the *true cause* record (`r1`), even
though it describes a completely different error (HTTP 429 vs 401).

**Keyword retrieval cannot distinguish these records.** It has no notion of whether a record
was previously useful in a similar situation.

---

## Behaviour before any feedback

Before feedback, all three systems perform similarly. No system has a meaningful advantage —
they all rely on keyword and semantic similarity, which does not capture whether a record was
actually useful.

For query q2 (`"GitHub API returning 401 after token rotation"`):

| Rank | Keyword | Neural Ledger (before) |
|------|---------|------------------------|
| 1    | r3 (misleading) | r3 (misleading) |
| 2    | r7 (useful) | r7 (useful) |
| 3    | r1 (useful) | r1 (useful) |
| 4    | r2 (useful) | r2 (useful) |

Mean useful rank: **2.00** — identical. No advantage before learning.

---

## How Neural Ledger changes it

When the agent uses the retrieved context and reports back what helped:

```python
mem.feedback([record_map["r1"], record_map["r2"]], helped=1.0,
             reason="Expired token root cause — solved the problem")

mem.feedback([record_map["r3"]], helped=0.0,
             reason="Rate-limit cause — different error code, did not help")
```

The feedback engine does two things:

**1. Updates the per-record usefulness prior.**
Each record carries an internal `usefulness` field (default 1.0). Positive feedback
raises it; negative feedback lowers it. On the next recall, candidate scores are
multiplied by this prior before path expansion and re-ranking. `r3`'s keyword score
stays high — but its effective score is suppressed by a learned `usefulness < 1.0`,
regardless of how many keywords it shares with the query.

**2. Strengthens co-retrieval links.**
Records returned together in the same result set are linked in an internal graph.
Positive feedback on `r1` strengthens those links; negative feedback on `r3` weakens
them. Future path expansion traverses stronger links.

These are two distinct learning channels:
- *record usefulness* — "Has this item itself been helpful before?"
- *link usefulness* — "Has traversing through this connection been helpful before?"

Link learning alone is insufficient: a misleading record can receive high path-expansion
scores by "borrowing" quality from its useful neighbours. The per-record prior suppresses
it directly, before path expansion, so the graph topology cannot rescue it.

---

## After feedback

| Rank | Neural Ledger (after feedback) |
|------|-------------------------------|
| 1    | **r1** (useful — true cause) ▲ was rank 3 |
| 2    | r7 (useful) — unchanged |
| 3    | r3 (misleading) ▼ was rank 1 |
| 4    | r8 (noise) |
| 5    | r2 (useful) |

Mean useful rank (q2): **1.67** — improvement from 2.00.
Keyword baseline remains at **2.00** (no memory of what helped).

### The canonical proof moment

The visible shift for q2:

| Record | Label | Rank before | Rank after | Change |
|--------|-------|-------------|------------|--------|
| r1 | useful (true cause) | 3 | **1** | ▲ 2 |
| r7 | useful | 2 | 2 | — |
| r3 | misleading (rate-limit) | 1 | **3** | ▼ 2 |

**r1 rose. r3 fell. Overall useful ranking improved.** That is the proof.

Note that r2 (also useful) moves slightly down in rank — individual record movements are
not perfectly monotone, because they are affected by the scores of all other candidates.
The aggregate signal (mean useful rank) is the reliable metric.

---

## Where this fits in an agent loop

```
┌─────────────────────────────────────────────────────┐
│                   Agent Loop                        │
│                                                     │
│  1. Encounter error (GitHub 401)                    │
│  2. mem.recall("GitHub API 401 …", limit=5)         │
│     → returns ranked past experiences               │
│  3. Agent uses context to diagnose / fix            │
│  4. mem.feedback([r1_id, r2_id], helped=1.0)        │
│     mem.feedback([r3_id], helped=0.0)               │
│     → system learns for next time                   │
│  5. Next similar error → r1 returned at rank 1      │
└─────────────────────────────────────────────────────┘
```

The feedback step (4) is the key addition over plain retrieval. It takes no model
calls — it is a lightweight in-process update.

---

## Running the example

**Script:**
```bash
python examples/coding_agent_failure_memory.py
```

**Notebook:**
Open `notebooks/01_failure_memory.ipynb` and run all cells. The notebook walks through
each phase interactively with commentary.

**Benchmark:**
```bash
pytest benchmarks/test_failure_memory.py -v
```

All 12 benchmark assertions pass, including the canonical proof moment:
- `r3` (misleading) must rank lower after negative feedback
- `r1` (useful — true cause) must reach rank 1 or 2 for q2 after positive feedback
- Mean useful rank for q2 must improve after feedback

---

## Key takeaway

Keyword and semantic retrieval treat every query independently — they cannot learn that
one record was helpful and another was not. Neural Ledger accumulates that signal via
`feedback()` and applies it on future `recall()` calls through two complementary channels:
a per-record usefulness prior (direct score suppression or amplification) and learned link
weights (graph traversal preference). The prior is essential — without it, misleading
records can maintain high rankings by sharing graph neighbourhood with useful ones.
