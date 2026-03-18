# Shared Memory — Multiple Agents on a Governed Ledger

Neural Ledger Phase 3B introduces **governed shared memory**: multiple agents can write to and read from a common ledger without losing provenance, without collapsing their private notes, and without turning the ledger into untraceable noise.

## The mental model

Each agent has two pools:

```
namespace: "ci-pipeline"
┌──────────────────────────────────────────────────┐
│  agent-a local  │  agent-b local  │  (private)   │
├──────────────────────────────────────────────────┤
│             shared pool                          │
│    (explicit opt-in, visible to all agents)      │
└──────────────────────────────────────────────────┘
```

- **Local** records are private to the writing agent.
- **Shared** records are visible to all agents in the same namespace.
- **Sharing is always explicit** — records default to `local`.

## Canonical scenario: coding-agent failure memory

Agent A hits a GitHub 401 failure, diagnoses the root cause, and stores it as shared. Agent B, working independently on the same codebase, faces the same error and recalls Agent A's finding.

### Agent A stores the root cause

```python
with Memory(persist_path="team.db", agent_id="agent-a", namespace="ci-pipeline") as agent_a:

    # Private working note — stays with agent-a only.
    agent_a.remember(
        "Retried three times before diagnosing the root cause",
        visibility="local",
    )

    # Root cause worth sharing across agents.
    agent_a.remember(
        "GitHub API 401 caused by expired access token. "
        "Refreshing via the token-refresh endpoint resolved it.",
        kind="observation",
        visibility="shared",
        provenance="run-042",
        metadata={"tool": "github_api", "error_code": "401"},
    )

    agent_a.feedback([r.id], helped=True, reason="Confirmed root cause")
```

### Agent B recalls from the shared pool

```python
with Memory(persist_path="team.db", agent_id="agent-b", namespace="ci-pipeline") as agent_b:

    hits = agent_b.recall(
        "How do I fix a GitHub API 401 authentication error?",
        scope="merged",   # own local + all shared
        with_why=True,
        limit=3,
    )

    for hit in hits:
        print(hit.content)
        print(f"from: {hit.agent_id}  provenance: {hit.provenance}")
        print(hit.why)

    # Agent B reinforces the shared record.
    agent_b.feedback([hits[0].id], helped=True)
```

**Output:**

```
GitHub API 401 caused by expired access token. Refreshing via the
token-refresh endpoint resolved it.
from: agent-a  provenance: run-042
Retrieved by keyword match. This memory is recent and active.
```

After two positive feedback events (from A and B), the record's usefulness rises above 1.0, making it rank more prominently in future recalls by any agent in the namespace.

## API additions

### `Memory` constructor

```python
Memory(
    persist_path: str | None = None,
    namespace: str = "default",
    agent_id: str | None = None,   # NEW — identifies this agent
    config: MemoryConfig | None = None,
)
```

### `remember(...)`

```python
mem.remember(
    content,
    *,
    kind="note",
    visibility="local",      # NEW — 'local' or 'shared'
    provenance=None,         # NEW — run ID, tool name, etc.
    metadata=None,
    source=None,
    timestamp=None,
)
```

### `recall(...)`

```python
mem.recall(
    query,
    *,
    scope="local",           # NEW — 'local', 'shared', or 'merged'
    limit=5,
    kind=None,
    metadata_filter=None,
    min_score=None,
    with_why=False,
)
```

### Return types

Both `MemoryRecord` (from `remember`) and `MemoryHit` (from `recall`) now carry:

```python
agent_id: str | None    # which agent wrote this record
provenance: str | None  # run or tool that produced it
visibility: str         # 'local' or 'shared' (MemoryRecord only)
```

## Scope semantics

| scope | What is visible |
|---|---|
| `"local"` (default) | This agent's own records + legacy unattributed records |
| `"shared"` | All records explicitly marked `visibility="shared"` in this namespace |
| `"merged"` | Union of local and shared |

Shared scope is always **namespace-bounded**. Shared records from `namespace="ci-pipeline"` are not visible to agents in `namespace="staging"`.

## Feedback across agents

Any agent can give feedback on any record it can read. Feedback updates the record's **usefulness prior** — the score multiplier that influences future rankings for all agents:

```python
# Agent B gives negative feedback on a misleading shared record.
agent_b.feedback([hit.id], helped=False)
```

Conflicting feedback from multiple agents raises the record's **link uncertainty** — making the system more cautious about co-retrieving it with other records. The record remains retrievable; it just ranks lower.

## `remember_many` with visibility

```python
agent_a.remember_many(
    [
        {"content": "GitHub 401 caused by expired token", "visibility": "shared"},
        {"content": "My local hypothesis about rate limits"},   # defaults to local
    ]
)

# Or set a default for all items in the batch:
agent_a.remember_many(
    ["shared fact one", "shared fact two"],
    default_visibility="shared",
)
```

## Design laws

1. **Sharing is explicit, not ambient.** Records default to `local`. You must opt in to sharing.
2. **Provenance is preserved.** `agent_id` and `provenance` travel with the record through every recall.
3. **Feedback does not become shared policy silently.** Feedback updates the record's usefulness and the link graph, but does not yet carry per-agent attribution. That is Phase 4.
4. **Namespace is the sharing boundary.** Shared memory is scoped to a namespace, not global.

## Running the example

```bash
python examples/shared_memory_two_agents.py
```
