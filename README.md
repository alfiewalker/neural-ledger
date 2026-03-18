# Neural Ledger

[![PyPI](https://img.shields.io/pypi/v/neural-ledger)](https://pypi.org/project/neural-ledger/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/github-alfiewalker%2Fneural--ledger-lightgrey?logo=github)](https://github.com/alfiewalker/neural-ledger)

**Memory is not just storage. It is judgement on what to store.**

Neural Ledger is a lightweight memory engine for software and agents. It helps systems **remember useful things**, **recall what matters**, and **learn from feedback**.

```python
from neural_ledger import Memory

mem = Memory()
mem.remember("GitHub API 401 — the access token expired", kind="observation")
mem.remember("Fix: regenerate the expired GitHub personal access token", kind="procedure")
mem.remember("Check rate limit headers before retrying requests", kind="note")

hits = mem.recall("How do I fix a GitHub API 401 error?", with_why=True, limit=3)
for hit in hits:
    print(f"[{hit.kind}] {hit.content}")
    print(f"  score={hit.score:.4f}  why: {hit.why}")

# Tell the engine which memory actually helped
mem.feedback([hits[0]], helped=True)
mem.feedback(hits[1:], helped=False)

# Repeated feedback accumulates. Over time, useful records rise;
# misleading ones score lower. See docs/examples/failure-memory.md
# for a controlled benchmark demonstrating the learning effect.
```

Three verbs. Everything else stays behind the curtain.

## Why Neural Ledger

Most memory systems stop at retrieval. They find candidates by similarity and return them. They do not get better.

Neural Ledger is built around a different idea: **feedback is a first-class signal, not a logging call**. Every `feedback()` call updates a per-record usefulness prior and a graph of co-retrieval links. Those signals directly shape future rankings.

The result is a memory engine that improves with use — one that can learn, over repeated interactions, which memories are worth surfacing and which are noise.

Three verbs cover everything:

- `remember(...)` — store experience
- `recall(...)` — retrieve the most relevant context
- `feedback(...)` — teach the system what actually helped

Everything else stays behind the curtain.

## Installation

```bash
pip install neural-ledger
```

## Quickstart

### 1. Create a memory

```python
from neural_ledger import Memory

mem = Memory()
```

By default, Neural Ledger runs fully in memory. No database, API key, or graph backend is required.

### 2. Store experience

```python
mem.remember("User prefers terse weekly updates")
mem.remember(
    "GitHub API failed because the token expired",
    kind="observation",
    metadata={"tool": "github", "severity": "high"},
)
```

### 3. Recall what matters

```python
hits = mem.recall("How should I write the update?", with_why=True)
```

### 4. Teach the system what helped

```python
mem.feedback(hits, helped=True)
```

Over time, Neural Ledger can use feedback to improve ranking and retrieval quality.

## API

### `Memory`

```python
Memory(
    persist_path: str | None = None,  # None = in-memory; path = SQLite
    namespace: str = "default",
    agent_id: str | None = None,      # identity for governed shared memory
    config: MemoryConfig | None = None,
)
```

### `remember(...)`

Store a new memory.

```python
record = mem.remember(
    content: str,
    *,
    kind: str = "note",
    metadata: dict | None = None,
    source: str | None = None,
    timestamp: datetime | None = None,
    visibility: str = "local",        # 'local' or 'shared'
    provenance: str | None = None,    # run ID, tool name, etc.
)
```

### `remember_many(...)`

Store multiple memories at once.

```python
records = mem.remember_many(
    [
        "User prefers terse weekly updates",
        {"content": "Token expiry caused the API failure", "visibility": "shared"},
    ],
    default_visibility="local",
)
```

### `recall(...)`

Retrieve the most relevant memories for a query.

```python
hits = mem.recall(
    query: str,
    *,
    limit: int = 5,
    kind: str | list[str] | None = None,
    metadata_filter: dict | None = None,
    min_score: float | None = None,
    with_why: bool = False,
    scope: str = "local",             # 'local', 'shared', or 'merged'
)
```

### `feedback(...)`

Tell Neural Ledger whether retrieved memories helped.

```python
mem.feedback(
    hits_or_ids,
    *,
    helped: bool | float,
    reason: str | None = None,
    metadata: dict | None = None,
)
```

`helped` accepts either:

- `True` / `False` for simple usage
- a float in `[0, 1]` for finer control

## Return types

### `MemoryRecord`

```python
@dataclass(slots=True)
class MemoryRecord:
    id: str
    content: str
    kind: str
    metadata: dict
    source: str | None
    timestamp: datetime
    agent_id: str | None = None
    provenance: str | None = None
    visibility: str = "local"
```

### `MemoryHit`

```python
@dataclass(slots=True)
class MemoryHit:
    id: str
    content: str
    score: float
    kind: str
    metadata: dict
    source: str | None
    timestamp: datetime
    why: str | None = None
    agent_id: str | None = None
    provenance: str | None = None
```

## Design principles

### Easy to start. Deep to grow.

The first successful use should take under five minutes. Advanced machinery can come later.

### Learn from usefulness, not just similarity.

Similarity finds candidates. Feedback teaches the system what actually helps.

### Retrieve context, not clutter.

Neural Ledger should return the smallest useful set, not a heap of vaguely related notes.

### Keep the front door tiny.

The public API should stay simple even if the engine becomes sophisticated.

## Architecture

The public API is three verbs. Behind them is a layered retrieval and learning engine.

```
┌──────────────────────────────────────────────────────┐
│               Memory  (public API)                   │
│        remember()  ·  recall()  ·  feedback()        │
└──────────────────────┬───────────────────────────────┘
                       │
            ┌──────────▼──────────┐
            │       Runtime       │
            │ namespace · policy  │
            └────┬──────────┬─────┘
                 │          │
    ┌────────────▼──┐  ┌────▼──────────────────────┐
    │  RecordStore  │  │     Retrieval pipeline     │
    │  (dict/SQLite)│  │  Semantic (optional)       │
    └───────────────┘  │  → Keyword fallback        │
                       │  → Path expansion (BFS)    │
    ┌───────────────┐  │  → Rank by seed · link ·   │
    │   LinkStore   │  │    freshness · usefulness  │
    │  (nx/SQLite)  │  └────────────────────────────┘
    └───────────────┘
                       ┌────────────────────────────┐
                       │     Learning engine        │
                       │  usefulness prior          │
                       │  link weight + evidence    │
                       │  uncertainty · decay       │
                       └────────────────────────────┘
```

**Key properties:**

- Semantic retrieval with automatic keyword fallback when embeddings are unavailable
- Graph path expansion: retrieval follows co-retrieval links, not just nearest neighbours
- Per-record usefulness prior: feedback directly scales future retrieval scores
- Evidence history on links: conflicting signals raise uncertainty rather than overwriting
- Time-based decay: recent interactions are fresher; activation fades without reinforcement
- Full SQLite persistence: records, link weights, usefulness, and metrics survive restarts
- Governed shared memory: multiple agents share a ledger with explicit visibility and provenance

These are engine-room concerns. The public API stays at three verbs.

## What Neural Ledger is not

Neural Ledger is not:

- a thin vector-store wrapper,
- a graph database pitch deck,
- an ontology-first framework,
- an LLM-everywhere abstraction layer.

The point is not to make memory more complicated. The point is to make memory more useful.

## Persistence

Memory survives process restarts when you pass a `persist_path`:

```python
# First run — store something.
with Memory(persist_path="memory.db") as mem:
    mem.remember("GitHub 401 caused by expired token", kind="observation")

# Later run — it is still there.
with Memory(persist_path="memory.db") as mem:
    hits = mem.recall("GitHub 401")
    print(hits[0].content)  # "GitHub 401 caused by expired token"
```

Records, learned usefulness, link weights, and engine metrics all survive the restart.

## Shared memory across agents

Multiple agents can share a governed memory ledger. Records default to `local`; sharing is always explicit.

```python
# Agent A stores a shared finding.
with Memory(persist_path="team.db", agent_id="agent-a") as agent_a:
    agent_a.remember(
        "GitHub API 401 caused by expired token — refresh resolves it",
        visibility="shared",
        provenance="run-042",
    )

# Agent B recalls it — with full provenance.
with Memory(persist_path="team.db", agent_id="agent-b") as agent_b:
    hits = agent_b.recall("GitHub 401 fix", scope="merged")
    print(hits[0].content)    # agent-a's finding
    print(hits[0].agent_id)   # "agent-a"
    print(hits[0].provenance) # "run-042"

    agent_b.feedback(hits, helped=True)  # reinforces the shared record
```

See [docs/examples/shared-memory.md](docs/examples/shared-memory.md) and `examples/shared_memory_two_agents.py` for the full scenario.

## Current scope

Neural Ledger is intentionally small.

Included:

- in-memory and SQLite-persistent usage
- records, retrieval, and feedback
- feedback-learned usefulness and link weights
- governed shared memory with `agent_id`, `visibility`, and `provenance`
- lightweight configuration

Not yet included:

- per-agent evidence attribution (Phase 4)
- explicit forgetting API
- heavy backend integrations
- full proof-chain objects
- broad framework adapters

## Roadmap

### Completed

- **Phase 1** — Tiny public API, in-memory backend, feedback-aware retrieval
- **Phase 2** — Canonical proof: feedback improves recall over keyword and semantic baselines
- **Phase 3** — SQLite persistence: records, usefulness, link weights, and metrics survive restarts
- **Phase 3B** — Governed shared memory: multiple agents on one ledger with explicit visibility, provenance-preserving recall, and accumulated feedback

### Upcoming

- **Phase 4** — Evidence and confidence strengthening: per-agent attribution, explainable conflict handling, trust-weighted ranking
- **Phase 5** — Public proof pack and release: polished README, benchmark summary, terminal demo

## Example: personal preference memory

```python
from neural_ledger import Memory

mem = Memory()

mem.remember("The user prefers concise answers on work topics", kind="preference")
mem.remember("The user likes deep examples when learning maths", kind="preference")

hits = mem.recall("How should I answer this question about a status update?", with_why=True)

for hit in hits:
    print(f"{hit.content} ({hit.score:.2f})")
    print(hit.why)

mem.feedback(hits, helped=True, reason="The preference was relevant")
```

## Contributing

Neural Ledger is being built in the open.

The current focus is:

- a beautiful beginner experience,
- honest internals,
- strong evaluation,
- and a clear theory of memory as judgement.

Issues, ideas, benchmarks, and well-argued criticism are welcome.

## License

MIT

## One line to remember

**Build the memory layer that decides what deserves to become memory.**
