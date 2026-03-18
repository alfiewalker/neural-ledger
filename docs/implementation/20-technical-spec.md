# 20 — Technical Spec

## Purpose

This document defines the internal architecture for **Neural Ledger** and the technical decisions required to preserve the distinctive behaviour found in the original prototype while reshaping it into a reusable package.

It exists to answer six questions clearly:

1. What must the system do internally to honour the product thesis?
2. Which prototype behaviours are preserved as first-class technical requirements?
3. What should the public API expose, and what should remain internal?
4. Why does v1 remain in-memory?
5. How do we create clean seams for later persistence, stronger policy, and graph backends without overengineering v1?
6. How do we leave an honest path for governed shared memory later without dragging multi-agent complexity into v1?

---

## Scope

This document covers:

- internal module boundaries
- data flow from ingestion to recall to learning
- storage and retrieval abstractions
- learning and telemetry mechanisms
- package structure
- extension seams for later phases, including governed shared memory
- technical constraints and non-goals for v1

This document does **not** define:

- product positioning
- public proof strategy in detail
- roadmap sequencing by milestone
- benchmark content

Those belong in `01`, `02`, `30`, and `40`.

---

## Technical thesis

**Neural Ledger is not merely a storage layer. It is a lightweight memory engine that combines retrieval, path selection, feedback-weighted learning, and observability behind a tiny public API.**

The key architectural consequence is this:

- the **front door** must remain extremely small,
- the **engine room** may remain rich,
- the **storage backend** must not define the identity of the system.

---

## v1 technical goals

v1 must achieve the following:

1. Provide a tiny, zero-setup public API.
2. Preserve the distinctive prototype mechanics that make the system more than a note store.
3. Keep the implementation inspectable and mostly symbolic.
4. Remain in-memory by default for speed, clarity, and low friction.
5. Introduce honest seams for later persistence and graph backends without dragging that complexity into the first release.

---

## Prototype behaviours that are technically preserved

The following behaviours from the original prototype are **preserved requirements**, not optional inspiration.

### 1. Semantic retrieval with graceful fallback
The system must support semantic retrieval when embeddings are available, but degrade cleanly to keyword-based retrieval when they are not.

### 2. Graph/path-based expansion
Retrieval must not stop at isolated node similarity. The engine must be able to expand from a relevant node into a path of related nodes.

### 3. Path scoring beyond similarity alone
The system must support scoring that combines more than one signal. At minimum, the preserved prototype signals are:

- semantic relevance
- path length / completeness
- node activation or freshness proxy
- per-record learned usefulness prior (see §4 below)

### 4. Feedback-driven learning
The engine must learn from feedback through two complementary channels:

**a. Per-record usefulness prior.** Each record carries a learned `usefulness` scalar
(default 1.0, range [0.05, 2.0]). Positive feedback raises it; negative feedback lowers
it. Before path expansion, candidate scores are multiplied by this prior and re-sorted.
This makes feedback visible in rankings **directly and immediately**, independent of graph
topology. It is essential: without a per-record prior, a misleading record can maintain
a high effective score by inheriting path-expansion scores from useful graph neighbours.

**b. Link weight learning.** The engine also strengthens or weakens links used during
retrieval. This shapes future path expansion. However, link learning alone is insufficient
for demotion — hence the per-record prior.

### 5. Evidence history on learned links
Edge updates must retain evidence history rather than overwrite belief blindly.

### 6. Uncertainty and confidence
The engine must support uncertainty at the edge level and confidence derived from that uncertainty.

### 7. Time-based decay / freshness
The system must support forgetting pressure through time-based decay or equivalent freshness weakening.

### 8. Circularity / loop awareness
The graph must remain inspectable for cycles and circular reasoning risk in relevant subgraphs.

### 9. Observability as a first-class concern
The engine must track memory operations, hit/miss rates, context quality, context path characteristics, learning operations, and tool-related observability.

### 10. Public simplicity over internal ontology
The system may internally distinguish richer concepts, but those distinctions must not burden the default public API.

---

## Public vs internal architecture

### Public surface
The public API remains deliberately small:

- `Memory`
- `remember(...)`
- `remember_many(...)`
- `recall(...)`
- `feedback(...)`
- `MemoryRecord`
- `MemoryHit`
- `MemoryConfig`

This is the only surface most users should need.

### Internal engine
Internally, the engine may still manage:

- records / nodes
- links / edges
- retrieval candidates
- context paths
- learning evidence
- confidence and uncertainty
- telemetry summaries
- policy decisions

These remain internal so adoption stays light.

---

## Architectural principles

### Thin façade, thick engine
The package should feel small from the outside and capable on the inside.

### Zero-setup first
v1 should require no database, graph backend, or external infrastructure.

### Honest seams
Every abstraction introduced in v1 should correspond to a real separation of responsibility, not speculative architecture.

### Preserve inspectability
The core mechanisms should remain comprehensible to an engineer reading the code.

### Delay backend theatre
Persistence and external graph backends matter, but they should arrive only after the core behaviour is proven.

---

## High-level component model

Neural Ledger should be structured around six internal areas.

### 1. API façade
Owns the public objects and method calls.

Responsibilities:

- validate user input
- apply defaults
- translate public method calls into engine actions
- return simple Python objects

### 2. Store
Owns records and links.

Responsibilities:

- store memory records
- store graph links
- fetch records by id
- fetch neighbours for traversal
- manage namespace separation

v1 default implementation: **in-memory**.

### 3. Retrieve
Owns candidate search, path expansion, and ranking.

Responsibilities:

- semantic retrieval
- keyword fallback
- candidate filtering
- context path expansion
- ranking of results and paths

### 4. Learn
Owns adaptation from feedback.

Responsibilities:

- strengthen or weaken links
- append evidence history
- update uncertainty
- apply decay / freshness ageing

### 5. Telemetry
Owns measurement and observability.

Responsibilities:

- hit / miss counting
- timing
- context path metrics
- context quality metrics
- learning-operation counts
- tool performance tracking
- pattern-observability summaries

### 6. Internal policy
Owns hidden decision logic.

Responsibilities:

- ranking weight selection
- path selection preferences
- feedback update rules
- thresholds and defaults
- later expansion into richer judgement rules

This remains internal in v1.

---

## Proposed package structure

```text
neural_ledger/
  __init__.py
  api.py
  types.py
  config.py
  internal/
    runtime.py
    policy.py
    compiler.py
  store/
    __init__.py
    protocols.py
    in_memory.py
  retrieve/
    __init__.py
    semantic.py
    keyword.py
    paths.py
    ranking.py
  learn/
    __init__.py
    feedback.py
    decay.py
    confidence.py
  telemetry/
    __init__.py
    metrics.py
```

### Notes

- `api.py` should expose the user-facing `Memory` class.
- `types.py` should hold the public dataclasses.
- `config.py` should expose only the minimal public config.
- `internal/` is allowed to be richer and less polished in naming than the public surface.

---

## Core data model

v1 should use a **simple public model** and a **slightly richer internal model**.

### Public dataclasses

```python
@dataclass(slots=True)
class MemoryRecord:
    id: str
    content: str
    kind: str
    metadata: dict[str, Any]
    source: str | None
    timestamp: datetime
```

```python
@dataclass(slots=True)
class MemoryHit:
    id: str
    content: str
    score: float
    kind: str
    metadata: dict[str, Any]
    source: str | None
    timestamp: datetime
    why: str | None = None
```

### Internal record representation

Internally, a stored record should carry at least:

- id
- content
- kind
- metadata
- timestamp
- activation / freshness signal
- usefulness prior (learned from feedback; default 1.0)
- optional embedding

### Internal link representation

A link should carry at least:

- source id
- target id
- weight
- timestamp
- evidence history
- uncertainty

This preserves the prototype behaviour without exposing it directly.

---

## Storage design

### v1 decision
**v1 uses an in-memory store only.**

### Rationale

1. It keeps the first-use experience frictionless.
2. It keeps the implementation fast to iterate.
3. It allows the real behaviour to be proven before storage complexity arrives.
4. The current prototype is already naturally in-memory and graph-oriented.

### Store interfaces

The store layer should be defined by small protocols, not a large ORM or backend abstraction.

```python
class RecordStore(Protocol):
    def put_record(self, record: InternalRecord) -> None: ...
    def get_record(self, record_id: str) -> InternalRecord | None: ...
    def list_records(self, namespace: str) -> list[InternalRecord]: ...
```

```python
class LinkStore(Protocol):
    def add_link(self, source_id: str, target_id: str, weight: float, **attrs) -> None: ...
    def update_link(self, source_id: str, target_id: str, weight: float, **attrs) -> None: ...
    def get_link(self, source_id: str, target_id: str) -> dict[str, Any] | None: ...
    def neighbours(self, source_id: str) -> list[str]: ...
```

### In-memory implementation

v1 may continue to use a directed graph structure internally for the default implementation. A `networkx`-backed implementation is acceptable for v1 if kept behind the store boundary.

---

## Retrieval design

Retrieval in Neural Ledger is a multi-stage process.

### Stage 1 — candidate generation
Generate initial candidates from the query.

Order of operation:

1. semantic retrieval if embedding support is available
2. keyword fallback otherwise

### Stage 2 — candidate filtering
Filter weak candidates according to a relevance threshold.

### Stage 3 — context path expansion
For each viable candidate, expand a path through the graph by following promising outgoing links without revisiting nodes.

### Stage 4 — path scoring
Score each path using a weighted combination of signals.

The preserved prototype signals are:

- relevance score from candidate retrieval
- path length / completeness signal
- average activation / freshness signal across the path

### Stage 5 — result selection
Select the best path or best set of hits and convert them into `MemoryHit` objects.

### v1 design note
The public API returns hits, not raw paths. Path information remains internal unless exposed through `why` or later advanced APIs.

---

## Learning design

Learning is what differentiates the engine from a static retriever.

### Input
Learning is driven by `feedback(...)`.

Accepted signal:

- boolean feedback
- continuous feedback in the interval `[0, 1]`

Internally this may be converted into a signed or weighted update value.

### Learning targets
There are two complementary learning targets in v1.

**1. Per-record usefulness prior.**
Updated directly from feedback. Scales the record's initial candidate score before
path expansion. This is the primary mechanism ensuring feedback changes rankings
immediately, without requiring graph structure to change first.

**2. Retrieval path or link set.**
The links that connected records in the result set are strengthened or weakened.
This shapes future path expansion but cannot alone suppress a misleading record
whose keyword or semantic score is intrinsically high.

### Preserved update behaviour
When positive feedback is received:

- raise the record's usefulness prior
- strengthen the links used
- append positive evidence
- reduce uncertainty only if the evidence becomes more consistent over time

When negative feedback is received:

- lower the record's usefulness prior
- weaken misleading links or reduce their future influence
- append negative evidence
- allow uncertainty to rise when evidence conflicts

### Conflict handling
The prototype includes conflict-aware weighting when new feedback disagrees with the current edge direction or sign. v1 should preserve the spirit of this behaviour even if the exact numeric rule changes during refactor.

### Evidence history
Evidence history should remain bounded in size.

### Why this matters
Blind overwrite destroys the memory of disagreement. Evidence history is one of the most distinctive behaviours in the current prototype and must remain.

---

## Confidence and uncertainty design

Confidence must not be a decorative field.

### Edge uncertainty
Uncertainty should be computed from the variance or inconsistency of evidence seen on a link.

### Node confidence
Node-level confidence may be derived from the average uncertainty of adjacent links.

### v1 use
In v1, uncertainty and confidence should primarily be:

- stored
- inspectable
- available for ranking or diagnostics

They do not need to dominate public behaviour yet, but they must be preserved technically.

---

## Decay and forgetting pressure

v1 should support a simple ageing mechanism.

### Required behaviour
Over time, link strength should weaken unless reinforced.

### Constraints

- decay must never destroy a link below a minimum threshold unless an explicit deletion policy is added later
- timestamps must be updated on interaction or reinforcement
- decay should be deterministic and easy to reason about

### Why this remains simple in v1
A full public forgetting API is deferred. v1 only needs technical support for freshness weakening.

---

## Circularity and graph safety

The graph must be inspectable for cycles and circular reasoning risk.

### Required behaviour

- detect whether cycles exist
- find a first cycle when requested
- analyse query-relevant subgraphs for circularity

### v1 use
This is primarily a diagnostic and trust mechanism in v1.

It is not yet part of the default public `recall(...)` output, but the capability must remain available internally and for later proof material.

---

## Telemetry design

Telemetry is a first-class subsystem.

### Required metrics
At minimum, Neural Ledger must track:

- total memory operations
- memory hits and misses
- semantic vs exact / fallback usage
- operation timings
- context path lengths
- context quality scores
- learning operations
- pattern-recognition hits
- tool performance summaries

### Design principle
Telemetry should remain **observational** in v1.

This means:

- the system may expose telemetry summaries,
- but telemetry should not yet become an uncontrolled second policy engine.

### Reason
The current prototype is strong on observability but not yet fully mature as a behaviour-governing policy layer. v1 should keep that honesty.

---

## Config design

### Public config
The public config must remain deliberately small.

```python
@dataclass(slots=True)
class MemoryConfig:
    default_limit: int = 5
    explain_recall: bool = False
    auto_learn_from_feedback: bool = True
    min_score: float = 0.0
```

### Internal config
Internal subsystems may retain richer config objects for:

- retrieval weights
- relevance thresholds
- decay behaviour
- uncertainty defaults
- telemetry thresholds

These should not leak into the beginner experience.

---

## Execution flows

### 1. Remember flow

`remember(content, ...)`

1. validate input
2. create public record
3. compile into internal record
4. optionally compute embedding
5. store record
6. optionally create initial links or activation defaults
7. return `MemoryRecord`

### 2. Recall flow

`recall(query, ...)`

1. validate input
2. generate initial candidates
3. apply fallback if semantic retrieval is unavailable
4. expand promising context paths
5. score candidate paths / hits
6. convert best results into `MemoryHit`
7. optionally include human-readable `why`
8. emit telemetry
9. return hits

### 3. Feedback flow

`feedback(hits_or_ids, helped, ...)`

1. normalise input into internal ids / traces
2. update per-record usefulness prior for each affected record
3. map feedback to the links or paths that produced the result
4. append evidence
5. update link strengths
6. recompute uncertainty
7. update timestamps
8. record learning telemetry

---

## Persistence guarantees and non-goals (Phase 3A)

### What is now supported

- **In-memory by default.** `Memory()` requires no file or configuration.
- **SQLite persistence via `persist_path`.** `Memory(persist_path="memory.db")` stores all
  records, links (including weights, evidence, uncertainty), usefulness priors, and telemetry
  counters durably to a local SQLite file.
- **Restart survival.** A `Memory` instance reopened on the same `persist_path` restores the
  full state: records, usefulness, links, and metrics.
- **Durability without explicit close.** Every write commits to SQLite immediately
  (`INSERT OR REPLACE` with per-write `COMMIT`). `close()` is a courtesy flush; durability
  does not depend on it being called.
- **Context manager support.** `with Memory(persist_path=...) as mem:` is the recommended
  pattern for explicit lifecycle management.
- **Namespace isolation in a shared file.** Multiple `Memory` instances on the same SQLite
  file with different namespaces remain fully isolated.

### SQLite pragmas in use

| Pragma | Value | Reason |
|---|---|---|
| `journal_mode` | `WAL` | Readers do not block writers; crash-safe at WAL checkpoints |
| `synchronous` | `NORMAL` | With WAL, crash-safe without the overhead of FULL |
| `busy_timeout` | `5000` ms | Retry on SQLITE_BUSY up to 5 s rather than failing immediately |

### Known limitations (Phase 3A scope)

- **Single writer.** SQLite allows one concurrent writer. Multiple processes writing
  to the same file simultaneously may see `SQLITE_BUSY` errors beyond the retry window.
  This is single-node, local durable persistence by design.
- **No concurrent in-process instances.** Two `Memory` instances pointing to the same
  `persist_path` in the same process share a file but maintain separate in-memory caches.
  Writes from one instance are visible to a newly opened second instance (loaded from SQLite
  on init) but not to an already-open second instance whose cache predates the write.
- **No atomic feedback transactions.** The feedback operation updates records, links, and
  metrics in separate SQLite commits. A crash mid-feedback could leave usefulness updated
  but link evidence not, or vice versa. This is a known Phase 3A limitation. Strict
  transactional feedback belongs to a future hardening phase.
- **No schema migration.** Changing the schema across Neural Ledger versions requires
  manual migration or a clean database. Schema evolution tooling is deferred.

### What is not promised

- Multi-process writers sharing a single database file
- Distributed coordination or replication
- High-concurrency production guarantees
- Backend migration or schema versioning
- Graph database backends (deferred to Phase 5+)

---

## Technical non-goals for v1

The following are explicitly **not** part of the v1 technical scope:

- persistence beyond process death
- Neo4j backend
- public proof-chain objects
- public contradiction arbitration API
- large framework adapters
- user-defined edge taxonomies
- distributed memory services
- asynchronous background consolidation layers
- multi-agent shared memory behaviour in the public API

These may come later, but none should distort v1.

---

## Phase boundaries from a technical perspective

### v1
- public API exists
- in-memory store only
- retrieval works with semantic + fallback behaviour
- path expansion and ranking preserved
- feedback learning works
- telemetry works

### v2
- canonical proof scenario exists
- benchmark harness exists
- retrieval improvement after feedback is demonstrated credibly

### v3
- persistence layer introduced
- likely SQLite first, then optional Postgres
- core interfaces proven stable enough to survive process death

### v3B
- governed shared-memory seam added
- records and links can carry `agent_id`, provenance, and visibility
- local memory and shared ledger memory can coexist
- read policy distinguishes local-only, shared-only, and merged recall paths

### v4
- stronger evidence and confidence mechanisms
- richer policy engine
- stronger contradiction and forgetting mechanisms

### v5
- public proof pack complete
- release packaging, docs, and credibility surfaces complete

This boundary matters because “memory survives process death”, “multiple agents can share governed memory”, and “memory has interchangeable infrastructure” are different milestones.

---

## Shared-memory extension seam (Phase 3B and later)

Neural Ledger should be able to grow from single-agent memory into governed collective memory **without** turning the public API into a multi-agent framework.

### Design stance
Shared memory is valuable, but an undifferentiated pool is dangerous. The preferred model is:

\[
\text{local agent memory} + \text{shared ledger memory}
\]

This means an agent can preserve local context while selectively reading from and writing to a shared substrate.

### Minimum additional fields for shared memory
The internal record model should be able to grow to include:

- `agent_id` — who produced the memory
- `provenance` — what event, source, or run produced it
- `visibility` — local, shared, or restricted
- `scope` — which workflow or task family the memory belongs to
- `feedback_history` — how later use affected trust

The internal link model should be able to grow to include:

- authoring agent or originating run
- provenance of the relation
- conflict markers when agents disagree
- visibility rules consistent with linked records

### Required architectural seam
The store and retrieval layers should be designed so that future recall can apply a read policy such as:

- local only
- shared only
- local first, then shared
- merged with provenance-aware ranking

This seam should exist in the internal design even though v1 keeps it dormant.

### Why it is deferred
Shared memory without provenance, visibility, and conflict handling quickly becomes epistemic noise. That is why it belongs **after** single-agent value and persistence are proven.

---

## Technical risks

### 1. Premature abstraction
Risk: inventing too many interfaces before the behaviour stabilises.

Response: keep store and retriever interfaces narrow.

### 2. Public API leakage from internals
Risk: exposing graph terms too early.

Response: keep the public API centred on `remember`, `recall`, and `feedback`.

### 3. Losing prototype distinctiveness during cleanup
Risk: refactor turns the engine into generic vector retrieval.

Response: preserve path expansion, evidence history, uncertainty, and decay as explicit requirements.

### 4. Metrics mutating into hidden policy
Risk: telemetry starts changing behaviour implicitly before policy is designed.

Response: keep telemetry observational in v1.

### 5. Backend-driven identity drift
Risk: the project becomes “graph backend integration” instead of “memory judgement engine”.

Response: defer heavy persistence and graph backend work until later phases.

---

## Implementation guidance

### Constructor hygiene
Avoid instantiated mutable config objects as default arguments. Use `None` and construct internally.

### Return-object discipline
Return plain Python dataclasses from the public API.

### Error discipline
Reject invalid empty strings and impossible parameter values early.

### Explainability discipline
`why` explanations should be human-readable, not raw scoring internals.

### Test discipline
Test the behaviour that matters:

- fallback when semantic retrieval is unavailable
- path retrieval without loops
- rank improvement after feedback
- uncertainty update when evidence conflicts
- decay reducing weight over time
- cycle report correctness
- telemetry accounting correctness

---

## Locked decisions

1. **Neural Ledger v1 is in-memory only.**
2. **The public API remains tiny and hides the graph machinery.**
3. **Semantic retrieval with fallback, path expansion, per-record usefulness prior, feedback learning, evidence history, uncertainty, decay, circularity checks, and telemetry are preserved prototype behaviours.**
4. **Telemetry remains observational in v1.**
5. **Persistence arrives before interchangeable graph backends.**
6. **Governed shared memory is a Phase 3B extension, not a v1 concern.**
7. **The architecture is designed around honest seams, not speculative infrastructure.**
