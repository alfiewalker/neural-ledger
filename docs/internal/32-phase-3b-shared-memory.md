# 32 — Phase 3B Spec: Governed Shared Memory for Multiple Agents

## Purpose

This document specifies **Phase 3B**, the first honest version of multi-agent memory in
Neural Ledger. It defines the model, the minimum additions to the data model and public API,
the read policy, conflict semantics, the acceptance scenario, and the explicit non-goals.

---

## Where we are after Phase 3A

After Phase 3A, Neural Ledger can:

- store memory with `remember(...)`,
- retrieve and rank it with `recall(...)`,
- learn from feedback via `feedback(...)`,
- survive process restart via `persist_path`.

Every `Memory` instance is a **single agent's view** of its own memory. It does not know
about other agents. It cannot read or write to a shared pool.

That is correct for Phase 3A. It is insufficient for "ledger."

---

## The problem to solve

A ledger is not a private notebook. It is a **governed record** of what was learned,
by whom, and with what provenance.

When two agents operate in the same domain — say, two instances of a coding assistant
working on the same codebase — the value of their experience compounds if they can share it.
But undifferentiated sharing turns into noise. Without provenance, you cannot tell whether
a memory came from a reliable source or a confused one. Without visibility control, one
agent's private working state bleeds into another's ranked results.

The question Phase 3B must answer is:

> When two agents write to the same memory substrate, what must be attached to each memory
> so that sharing remains intelligible?

The minimum answer is: **agent identity**, **provenance**, and **visibility**.

---

## Design principles

### 1. Local + shared, not a unified pool

The preferred model is:

```
local agent memory  +  shared ledger memory
```

Not every memory should immediately become globally shared.
An agent's working hypothesis, half-formed observation, or session-local preference should
stay local. Only memories deliberately promoted to shared should cross agent boundaries.

### 2. Identity before policy

Every record and every feedback event must carry an `agent_id`. Visibility and trust cannot
be reasoned about without knowing who produced the memory.

### 3. Sharing is explicit, not default

The default visibility for a new memory is `"local"`. A memory must be explicitly marked
`"shared"` to enter the shared ledger. This prevents accidental leakage of private context.

### 4. Conflict is visible, not silently collapsed

When two agents give opposite feedback on the same record, both signals are preserved.
High evidence variance signals conflict. No automatic arbitration in Phase 3B.
Conflict resolution belongs to Phase 4.

### 5. The public API stays minimal

New fields do not require new verbs. `agent_id` belongs on the `Memory` constructor.
`visibility` belongs on `remember(...)`. `scope` belongs on `recall(...)`.
The three core verbs are unchanged.

---

## The model: local + shared

Each `Memory` instance is bound to:
- a `persist_path` (shared file, possibly shared with other agents)
- a `namespace` (logical scope, used for isolation today)
- an `agent_id` (who this instance speaks for)

Records carry a `visibility` field:
- `"local"` — readable only by the agent who wrote it (default)
- `"shared"` — readable by any agent operating in the same shared scope

On recall, the `scope` parameter controls what is visible:
- `"local"` — this agent's local records only (default, safe)
- `"shared"` — shared records from all agents
- `"merged"` — local records plus shared records, ranked together with provenance-aware
  weighting

```
                     ┌───────────────────────────────────┐
                     │          SQLite file               │
                     │                                   │
    agent-a ──────→  │  local:agent-a  │  shared pool   │  ←────── agent-b
    agent-b ──────→  │  local:agent-b  │  (all agents)  │  ←────── agent-a
                     └───────────────────────────────────┘
```

---

## Minimum additions to the data model

### `InternalRecord` — new fields

| Field | Type | Default | Meaning |
|---|---|---|---|
| `agent_id` | `str \| None` | `None` | Identity of the agent that created this record |
| `provenance` | `str \| None` | `None` | Source event or run that produced this record |
| `visibility` | `str` | `"local"` | `"local"` or `"shared"` |

`agent_id=None` is valid for backwards-compatible records created before Phase 3B.
Those records remain accessible as local records of the owning namespace.

### `InternalLink` — new fields

| Field | Type | Default | Meaning |
|---|---|---|---|
| `agent_id` | `str \| None` | `None` | Identity of the agent that created this link |

Links are created by co-retrieval (internal) and strengthened by feedback. Knowing which
agent created a link supports future conflict-aware traversal.

### Feedback events

Feedback in Phase 3B must carry `agent_id`. The current `apply_feedback` function does not
receive agent context. Phase 3B should add it so the evidence history can track who gave
which signal. The evidence list format may need to evolve from `list[float]` to
`list[tuple[str | None, float]]` (agent_id, value), or a separate evidence-event model.

This is the most significant internal change in Phase 3B. The current `list[float]`
evidence history is sufficient for single-agent use but loses attribution in multi-agent use.

---

## Public API changes

### `Memory` constructor

```python
mem = Memory(
    persist_path: str | None = None,
    namespace: str = "default",
    agent_id: str | None = None,    # NEW — who this Memory instance speaks for
    config: MemoryConfig | None = None,
)
```

`agent_id` is optional. When `None`, the instance behaves as Phase 3A — single-agent,
all visibility rules default to `"local"`.

### `remember(...)`

```python
record = mem.remember(
    content: str,
    *,
    kind: str = "note",
    metadata: dict | None = None,
    source: str | None = None,
    timestamp: datetime | None = None,
    visibility: str = "local",     # NEW — "local" | "shared"
    provenance: str | None = None, # NEW — run id, tool name, or event label
)
```

### `recall(...)`

```python
hits = mem.recall(
    query: str,
    *,
    limit: int = 5,
    kind: str | list[str] | None = None,
    metadata_filter: dict | None = None,
    min_score: float | None = None,
    with_why: bool = False,
    scope: str = "local",          # NEW — "local" | "shared" | "merged"
)
```

### `MemoryRecord` — new public fields

```python
@dataclass(slots=True)
class MemoryRecord:
    id: str
    content: str
    kind: str
    metadata: dict
    source: str | None
    timestamp: datetime
    agent_id: str | None = None    # NEW
    provenance: str | None = None  # NEW
    visibility: str = "local"      # NEW
```

### `MemoryHit` — new public fields

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
    agent_id: str | None = None    # NEW — who contributed this memory
    provenance: str | None = None  # NEW
```

### What does NOT change

- `feedback(...)` signature is unchanged publicly. `agent_id` is known from the Memory
  instance and applied internally.
- `remember_many(...)` forwards `visibility` and `provenance` per item from dicts.
- `MemoryConfig` unchanged.

---

## Read policy

The recall pipeline applies visibility filtering after candidate generation and before
path expansion.

| `scope` value | Records included |
|---|---|
| `"local"` (default) | Only records where `visibility = "local"` AND `agent_id = this agent` |
| `"shared"` | Only records where `visibility = "shared"` (all agents) |
| `"merged"` | Local records + shared records, with provenance-aware ranking |

### Merged ranking

In `"merged"` mode, the ranking formula gains a provenance component:

- Records from the current agent get a small local-origin bonus.
- Shared records get no bonus but carry full usefulness signal from all agents' feedback.
- This means shared records that many agents found useful will rank well even for a new agent.

The exact weighting belongs in `InternalPolicy`. For Phase 3B, a simple approach:
local-origin bonus of +0.1 applied as a score multiplier (e.g., `usefulness * 1.1` for
local records in merged mode).

---

## Feedback and conflict semantics

### Attribution

Feedback from a Memory instance is attributed to that instance's `agent_id`. When
`agent_id=None`, attribution is unknown and feedback is treated as unattributed.

### Aggregation

When multiple agents have given feedback on the same shared record:
- All evidence is stored in the link's evidence history.
- The usefulness prior reflects the aggregate signal (mean over all feedback, regardless
  of agent).
- Uncertainty is computed from the full evidence variance. High variance = conflict.

### Conflict visibility

Phase 3B does **not** automatically resolve conflict. The `why` explanation should
mention conflict when uncertainty is high:

> "Used by multiple agents with conflicting feedback — treat with caution."

Automatic conflict resolution, arbitration, and trust-weighted feedback belong to Phase 4.

### Example: two-agent conflict

```
Agent A:  feedback(r1, helped=1.0)   → usefulness += 0.1 → 1.1
Agent B:  feedback(r1, helped=0.0)   → usefulness -= 0.1 → 1.0
                                        uncertainty rises from 0.5 → ~0.7
```

The record remains retrievable. Its usefulness is back to neutral. Its uncertainty is
elevated, signalling disagreement. Neither agent's signal is silently dropped.

---

## The acceptance scenario

### Scenario: two coding agents, shared failure memory

**Arc:**

```
agent-a encounters 401 failure
  → agent-a stores root cause as shared
  → agent-b, working same codebase, faces same error
  → agent-b recalls from shared pool
  → agent-b's feedback reinforces the shared record
  → both agents now benefit from accumulated evidence
```

**Proof moment:**

```python
# Agent A's session
with Memory(persist_path="shared.db", agent_id="agent-a") as a:
    a.remember(
        "GitHub API 401 caused by expired access token",
        kind="observation",
        visibility="shared",
        provenance="run-123",
    )
    a.feedback([record.id], helped=1.0)

# Agent B's session — independent, no knowledge of Agent A's specific failure
with Memory(persist_path="shared.db", agent_id="agent-b") as b:
    hits = b.recall("GitHub API 401", scope="merged")
    # Agent A's record should appear in the top results
    assert any("expired access token" in h.content for h in hits)
    assert any(h.agent_id == "agent-a" for h in hits)
```

**What this proves:**
- Agent B benefits from Agent A's prior learning without having seen the failure itself.
- Provenance is preserved — Agent B knows the memory came from Agent A.
- Feedback accumulates: when Agent B also marks it helpful, the shared record's usefulness rises.
- The shared pool is not noise — it carries the aggregate usefulness signal from both agents.

---

## Non-goals for Phase 3B

The following are explicitly **outside** Phase 3B scope:

- **Multi-process concurrent writers.** Phase 3B operates within Phase 3A's single-writer
  SQLite constraint. Concurrent writes from separate processes are not supported.
- **Distributed coordination or replication.** One SQLite file, one machine.
- **Complex access control.** No role-based permissions, no ACLs, no restricted visibility
  beyond local/shared.
- **Trust hierarchies between agents.** All agent feedback is weighted equally.
- **Federated or remote shared memory.** Remote stores and API-backed ledgers are deferred.
- **Automatic conflict resolution.** High-uncertainty records surface the conflict but no
  arbitration policy runs in Phase 3B.
- **Public contradiction API.** Contradiction detection remains internal.

---

## Open questions to resolve before building

### Q1 — Evidence attribution format

The current evidence list is `list[float]`. Should it become `list[tuple[str | None, float]]`
to preserve agent attribution, or should a separate `FeedbackEvent` structure be introduced?

The `FeedbackEvent` path is cleaner but more invasive. The tuple path is minimal but harder
to query. This must be decided before Phase 3B coding begins.

**Recommendation:** Defer evidence attribution to Phase 4. In Phase 3B, record `agent_id`
on the `InternalLink` only (who created the link), not on individual evidence entries.
Attribution at the feedback-event level belongs to the evidence-strengthening work in Phase 4.

### Q2 — Backwards compatibility

Existing records written without `agent_id` or `visibility` must remain accessible.
The default on read should be `agent_id=None`, `visibility="local"`, treating them as
legacy local records. Migration is not required.

### Q3 — Shared namespace scope *(locked)*

**Decision:** Per-namespace. `visibility="shared"` means visible to any agent within the
same namespace. Cross-namespace sharing is disallowed in Phase 3B.

**Why:** Global sharing would leak into storage queries, recall filtering, tests, and
later multi-tenant semantics in ways that are expensive to reverse. Namespace-bounded
sharing keeps the invariant simple: a namespace is a trust boundary. What happens inside
a namespace stays inside it. Global sharing is a deliberate future extension, not a default.

### Q4 — Merged recall ranking

The exact weighting for local-origin bonus in merged recall is unspecified above.
This should be part of `InternalPolicy` and tunable, not hardcoded.

---

## Acceptance criteria

Phase 3B is complete when:

1. Two agents sharing a `persist_path` can each recall shared memories from the other.
2. Local memories are invisible across agent boundaries without explicit `scope="shared"` or
   `scope="merged"`.
3. Feedback from Agent B on a shared record affects its usefulness for Agent A on subsequent
   recall.
4. `agent_id` and `provenance` are present on returned `MemoryHit` objects for shared records.
5. Conflicting feedback from two agents raises uncertainty rather than silently picking a winner.
6. All Phase 3A acceptance tests continue to pass — existing behaviour is unchanged.
7. A proof scenario equivalent to the canonical two-agent test above passes as a benchmark test.

---

## The line this phase crosses

Phase 3A proved:

> memory that survives process death on a single node

Phase 3B proves:

> memory that is intelligible across agents — governed, attributed, and ranked

That is what makes "Neural Ledger" more than a persistent cache.
