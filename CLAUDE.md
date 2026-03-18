# NeuralLedger — CLAUDE.md

**Thesis:** Memory is not storage. It is judgement.
Neural Ledger is a lightweight Python memory engine that helps systems remember useful things, recall what matters, and learn from feedback.

## Public API (v1 — frozen)

```python
from neural_ledger import Memory
mem = Memory(persist_path=None, namespace="default", config=None)
mem.remember(content, *, kind="note", metadata=None, source=None, timestamp=None) -> MemoryRecord
mem.remember_many(contents, *, default_kind="note", ...) -> list[MemoryRecord]
mem.recall(query, *, limit=5, kind=None, metadata_filter=None, min_score=None, with_why=False) -> list[MemoryHit]
mem.feedback(hits_or_ids, *, helped: bool|float, reason=None, metadata=None)
```

Return types: `MemoryRecord`, `MemoryHit` (with optional `why: str`), `MemoryConfig`.
No database, API key, or config required for `Memory()`.

## Key Design Rules

- Tiny public API — rich internal engine. Never leak graph/proof/policy concepts publicly.
- `feedback()` is central, not decorative — it's what turns this into a learning engine.
- `why` explanations must be human-readable (not raw scores).
- Validate at boundaries: empty strings and `helped > 1.0` raise `ValueError`.

## Internal Architecture (6 areas)

| Module | Responsibility |
|---|---|
| `api.py` | Public `Memory` facade, validation, defaults |
| `store/` | Records + graph links (v1: in-memory, networkx ok) |
| `retrieve/` | Semantic retrieval → keyword fallback → path expansion → ranking |
| `learn/` | Feedback updates: strengthen/weaken links, evidence history, uncertainty, decay |
| `telemetry/` | Observational metrics (hits, timing, path quality) — not a policy engine |
| `internal/` | Policy, runtime, compiler — hidden from public |

## Preserved Prototype Behaviours (must not be lost)

1. Semantic retrieval + keyword fallback
2. Graph/path expansion (not just nearest-neighbour)
3. Ranking beyond similarity (path length, freshness/activation)
4. Feedback-driven link strengthening/weakening
5. Evidence history on links (not blind overwrite)
6. Uncertainty/confidence derived from evidence variance
7. Time-based decay / freshness weakening
8. Circularity/cycle detection (diagnostic)
9. Observability metrics

## Package Structure

```
neural_ledger/
  __init__.py, api.py, types.py, config.py
  internal/  (runtime, policy, compiler)
  store/     (protocols, in_memory)
  retrieve/  (semantic, keyword, paths, ranking)
  learn/     (feedback, decay, confidence)
  telemetry/ (metrics)
```

## Phase Roadmap

| Phase | Goal |
|---|---|
| **1** | Installable package, tiny in-memory API working end-to-end |
| **2** | Canonical proof: feedback improves recall vs keyword+semantic baselines |
| **3** | Persistence (SQLite first) without changing public API |
| **3B** | Governed shared memory for multiple agents (agent_id, provenance, visibility) |
| **4** | Stronger confidence/evidence/contradiction |
| **5** | Public proof pack + release |

## Canonical Proof Scenario (Phase 2)

**Coding agent — failure memory**: `attempt → failure → remember cause → recall → feedback → better ranking`

Dataset: ~10-14 records (2 truly useful, 3 misleading, 5-9 noise). Compare: keyword baseline, semantic-only, Neural Ledger before/after feedback. Primary metric: useful hit in top-3 after feedback.

## v1 Non-Goals

No persistence, no Neo4j, no public contradiction API, no forgetting API, no framework adapters, no proof-chain objects.

## Docs

`docs/internal/` — 00 (fidelity contract), 01 (why/what/how), 02 (proof strategy), 10 (feature spec), 20 (technical spec), 30 (build phases), 40 (evaluation), 90 (decision log).
