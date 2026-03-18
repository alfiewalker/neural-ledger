# Changelog

All notable changes to Neural Ledger are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.1.0a1] — TBD

First public release of Neural Ledger.

### Summary

Neural Ledger is a lightweight memory engine that learns which memories are useful.
It is built around three verbs — `remember`, `recall`, `feedback` — and a layered
internal engine that makes feedback meaningful rather than decorative.

This release covers four phases of development:

| Phase | Capability |
|---|---|
| 1 | Installable package with tiny public API |
| 2 | Canonical proof: feedback improves recall over keyword and semantic baselines |
| 3 | SQLite persistence: memory survives restarts |
| 3B | Governed shared memory: multiple agents on one ledger |

### Added

**Core API**
- `Memory` class with `remember()`, `recall()`, `feedback()`, `remember_many()`
- `MemoryRecord`, `MemoryHit`, `MemoryConfig` public types
- `Memory.metrics()` for engine observability
- `Memory.close()` and context manager (`with Memory(...) as mem`)

**Retrieval pipeline**
- Keyword retrieval (BM25-style term overlap; no external deps required)
- Optional semantic retrieval via `sentence-transformers` (auto-detected; falls back to keyword)
- Graph path expansion: recall follows co-retrieval links, not just nearest neighbours
- Ranking combines seed score, link weights, freshness/activation, and per-record usefulness

**Learning engine**
- Per-record usefulness prior — feedback scales future retrieval scores directly
- Co-retrieval link creation: records that appear together get linked
- Evidence history on links: each feedback event appended, not overwritten
- Uncertainty derived from evidence variance (conflicting signals raise uncertainty)
- Time-based decay: activation fades without reinforcement

**Persistence (Phase 3)**
- SQLite backend: `Memory(persist_path="memory.db")`
- Records, link weights, usefulness, and engine metrics survive process restarts
- Write-through cache: all mutations flushed to SQLite immediately
- Schema migration support via `_MIGRATIONS` — existing databases can be upgraded
- WAL journal mode and busy-timeout for safe local usage

**Governed shared memory (Phase 3B)**
- `agent_id` parameter on `Memory` constructor — identifies the writing agent
- `visibility` parameter on `remember()` — `"local"` (default) or `"shared"`
- `scope` parameter on `recall()` — `"local"`, `"shared"`, or `"merged"`
- `provenance` parameter on `remember()` — run ID, tool name, or any identifier
- `agent_id` and `provenance` preserved on `MemoryRecord` and `MemoryHit`
- Shared scope is namespace-bounded (D-019)
- Feedback from any agent updates the shared record's usefulness
- `remember_many()` accepts `default_visibility` and forwards `visibility`/`provenance` from dict items

**Validation**
- `ValueError` on empty `content`, `kind`, or out-of-range `helped`
- `ValueError` on invalid `visibility` or `scope` values

**Examples**
- `examples/quickstart.py` — three-verb basic usage
- `examples/coding_agent_failure_memory.py` — full proof scenario
- `examples/shared_memory_two_agents.py` — Phase 3B two-agent canonical scenario

**Docs**
- `docs/examples/failure-memory.md` — Phase 2 proof walkthrough with benchmark numbers
- `docs/examples/shared-memory.md` — Phase 3B shared memory model and API
- `docs/internal/` — full spec, decision log, and build phases

### Known limitations

- Single-writer: concurrent writes from multiple processes to the same SQLite file are unsafe
- Feedback is not attributed per-agent in evidence history (Phase 4)
- No explicit forgetting or eviction API
- No public contradiction resolution API
- `sentence-transformers` is optional — install with `pip install "neural-ledger[semantic]"`

### Upgrade notes

This is the first public release. No upgrade path required.

---

## [Unreleased]

_Nothing pending._
