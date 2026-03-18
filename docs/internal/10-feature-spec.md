# 10 — Feature Spec

## Status
Draft v1  
Project: **Neural Ledger**

---

## Purpose

This document defines the **product-facing feature contract** for Neural Ledger v1.

It answers:

- what the first public product should do,
- what the public API must feel like,
- what behaviour is expected by default,
- what examples must work,
- and what is intentionally out of scope.

This is a feature document, not an internal architecture document.

---

## Audience

This document is for:

- the founder,
- engineers implementing the public package surface,
- contributors writing docs and examples,
- evaluators deciding whether the v1 product is coherent.

---

## Non-goals

This document does **not** define:

- module layout,
- storage backend internals,
- graph implementation details,
- embedding model choices,
- benchmark harness internals,
- future persistence strategy,
- advanced policy engine design.

Those belong in later documents.

---

## Product goal

Neural Ledger v1 should let a developer do three things with almost no setup:

1. **remember** a useful experience,
2. **recall** relevant context later,
3. **teach** the system what helped.

That is the entire product story for v1.

The feature bar is not “comprehensive memory”.
The feature bar is:

> a tiny public interface over a richer engine that improves retrieval quality through feedback.

---

## Design law

**Easy to start. Deep to grow.**

The first successful use should take under five minutes.

A developer should not need to choose:

- a graph backend,
- a persistence layer,
- a claim schema,
- a proof model,
- or a set of relation types.

If those become necessary before the first success, the public surface is too heavy.

---

## Core user promise

A developer should be able to say:

> “I added a few lines of code, and now my system remembers useful things, recalls what matters, and learns from what helped.”

That promise should be visible in the product itself.

---

## Public API surface

Neural Ledger v1 is built around **three core verbs** and **one convenience method**.

### Core verbs

- `remember(...)`
- `recall(...)`
- `feedback(...)`

### Convenience

- `remember_many(...)`

### Primary class

- `Memory`

This should be the only class most users ever need.

---

## Mental model

The public mental model must stay this small:

- **remember** stores experience,
- **recall** retrieves what matters,
- **feedback** teaches the system what was useful.

Anything more complex belongs behind the curtain.

---

## Public API contract

## `Memory`

### Constructor

```python
from neural_ledger import Memory

mem = Memory(
    persist_path: str | None = None,
    namespace: str = "default",
    config: MemoryConfig | None = None,
)
```

### Expected behaviour

- `persist_path=None` means the instance runs fully in memory.
- `namespace="default"` gives lightweight logical separation.
- `config=None` uses sensible defaults.
- Construction must require **no database, no API key, and no graph configuration**.

### Product expectation

A brand new user should be able to instantiate `Memory()` and immediately use the package.

---

## `remember(...)`

### Purpose

Store a piece of experience.

### Signature

```python
record = mem.remember(
    content: str,
    *,
    kind: str = "note",
    metadata: dict | None = None,
    source: str | None = None,
    timestamp: datetime | None = None,
)
```

### Behaviour

This method should:

1. validate the input,
2. create a memory record,
3. assign an ID,
4. store the raw content,
5. return a plain record object.

It may also enrich internally, but that must remain invisible to the caller.

### Rules

- `content` must be a non-empty string.
- `kind` is optional and light-touch.
- `metadata` is optional.
- the method should not require a schema.

### Suggested kinds

The product may suggest, but not strictly enforce, simple values such as:

- `"note"`
- `"observation"`
- `"preference"`
- `"fact"`
- `"procedure"`

The goal is gentle structure, not ontology burden.

### Example

```python
mem.remember("User prefers terse weekly updates")
mem.remember(
    "GitHub API failed because the token expired",
    kind="observation",
    metadata={"tool": "github", "severity": "high"},
)
```

---

## `remember_many(...)`

### Purpose

Store several memories at once without adding conceptual weight.

### Signature

```python
records = mem.remember_many(
    contents: list[str] | list[dict],
    *,
    default_kind: str = "note",
    default_metadata: dict | None = None,
    source: str | None = None,
)
```

### Accepted input shapes

#### Simple strings

```python
mem.remember_many([
    "User prefers terse weekly updates",
    "Token expiry caused the API failure",
])
```

#### Structured dictionaries

```python
mem.remember_many([
    {"content": "User prefers terse weekly updates", "kind": "preference"},
    {"content": "Token expiry caused the API failure", "kind": "observation"},
])
```

### Behaviour

This method should behave like repeated `remember(...)` calls, but with batch convenience.

---

## `recall(...)`

### Purpose

Retrieve the most relevant memories for a query.

### Signature

```python
hits = mem.recall(
    query: str,
    *,
    limit: int = 5,
    kind: str | list[str] | None = None,
    metadata_filter: dict | None = None,
    min_score: float | None = None,
    with_why: bool = False,
)
```

### Behaviour

This method should:

1. accept a query,
2. search memory,
3. rank results,
4. return the best hits,
5. optionally explain why each hit appeared.

The default result set should feel useful, not noisy.

### Rules

- `query` must be a non-empty string.
- `limit` should default to a small useful number.
- `kind` filtering is optional.
- `metadata_filter` is optional.
- `with_why=False` keeps default output lightweight.

### `why` behaviour

When `with_why=True`, explanations must be human-readable.

Good examples:

- “Matched the query semantically and was reinforced by past positive feedback.”
- “Recent preference memory related to writing style.”

Bad examples:

- “cosine=0.81 activation=0.34 edge_prior=0.27”

Raw debug signals belong in internal tooling, not the beginner experience.

### Example

```python
hits = mem.recall("How should I write the update?", with_why=True)
```

---

## `feedback(...)`

### Purpose

Tell Neural Ledger whether retrieved memories helped.

### Signature

```python
mem.feedback(
    hits_or_ids,
    *,
    helped: bool | float,
    reason: str | None = None,
    metadata: dict | None = None,
)
```

### Accepted input shapes

The method should be forgiving.
It may accept:

- `list[MemoryHit]`
- `list[str]`
- a single `MemoryHit`
- a single record ID string

### Behaviour

This method should update internal usefulness signals.

Semantically:

- `helped=True` strengthens usefulness,
- `helped=False` weakens usefulness or marks the hit as unhelpful,
- `helped=float` allows finer control on a scale from 0 to 1.

### Product importance

This is the feature that turns Neural Ledger from a store into a learning memory engine.

### Examples

```python
mem.feedback(hits, helped=True)
mem.feedback(hits, helped=False, reason="Too generic")
mem.feedback(hits, helped=0.8, reason="Captured the right preference")
```

---

## Public return types

Neural Ledger v1 should return **plain Python objects**.

The caller should not have to think in graphs, proofs, claims, or policies.

## `MemoryRecord`

```python
@dataclass(slots=True)
class MemoryRecord:
    id: str
    content: str
    kind: str
    metadata: dict
    source: str | None
    timestamp: datetime
```

## `MemoryHit`

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
```

## `MemoryConfig`

The public configuration surface should stay small.

```python
@dataclass(slots=True)
class MemoryConfig:
    default_limit: int = 5
    explain_recall: bool = False
    auto_learn_from_feedback: bool = True
    min_score: float = 0.0
```

This is enough for v1.
More configuration can come later if genuinely necessary.

---

## Default behaviour expectations

### Zero-setup first run

A developer should be able to do this with no extra setup:

```python
from neural_ledger import Memory

mem = Memory()
mem.remember("User prefers terse updates")
hits = mem.recall("How should I answer?")
mem.feedback(hits, helped=True)
```

### Lightweight by default

The default product experience should be:

- in-memory,
- low-friction,
- human-readable,
- small result sets,
- plain Python return types.

### Richer internals remain hidden

Behind the scenes, the engine may use:

- semantic retrieval,
- graph links,
- path expansion,
- feedback-weighted learning,
- confidence signals,
- decay and freshness,
- observability.

But none of those should be required to understand the product on day one.

---

## Usage examples that must work

## Example 1 — preference memory

```python
from neural_ledger import Memory

mem = Memory()

mem.remember("The user prefers concise answers on work topics", kind="preference")
mem.remember("The user likes deep examples when learning maths", kind="preference")

hits = mem.recall("How should I answer this status update question?", with_why=True)

for hit in hits:
    print(hit.content)
    print(hit.why)

mem.feedback(hits, helped=True, reason="The preference was relevant")
```

## Example 2 — coding-agent failure memory

```python
from neural_ledger import Memory

mem = Memory()

mem.remember("GitHub API request failed with 401 because the access token had expired", kind="observation")
mem.remember("Refreshing the GitHub token and retrying fixed the 401 error", kind="procedure")

hits = mem.recall("How should I fix this GitHub API 401 failure?", with_why=True)
mem.feedback(hits, helped=True, reason="This identified the true cause and fix")
```

## Example 3 — batch ingestion

```python
from neural_ledger import Memory

mem = Memory()

mem.remember_many([
    "Database connection failed due to an incorrect host value",
    "Check whether environment variables are loaded before retrying an API call",
])
```

These examples should feel natural and unsurprising.

---

## Error behaviour

The public surface should reject nonsense but accept convenience.

### Required validation examples

```python
mem.remember("")
# ValueError: content must be a non-empty string
```

```python
mem.recall("")
# ValueError: query must be a non-empty string
```

```python
mem.feedback(hits, helped=1.5)
# ValueError: helped must be a bool or a float between 0 and 1
```

### Product principle

- reject invalid inputs clearly,
- avoid needless ceremony,
- keep error messages human.

---

## Out of scope for v1

The following are intentionally excluded from the public v1 feature set:

- public contradiction policies,
- explicit forgetting API,
- backend plugins,
- graph database selection,
- public proof-chain objects,
- custom edge taxonomies,
- ontology design,
- broad framework adapters as the main product story,
- advanced policy tuning knobs.

These may exist internally or come later, but they must not clutter the v1 front door.

---

## Success criteria for the feature surface

The feature spec is successful if Neural Ledger v1 satisfies all of the following:

1. A developer can install and use it in under five minutes.
2. The public API can be explained in one sentence per verb.
3. The first examples require no backend selection.
4. The return types are plain and readable.
5. Feedback is clearly central rather than decorative.
6. The product feels simpler than the engine beneath it.

---

## Locked decisions

The following decisions are locked unless a later document explicitly revises them:

- The public class is `Memory`.
- The core verbs are `remember`, `recall`, and `feedback`.
- `remember_many` is included as convenience.
- In-memory is the default v1 experience.
- The public API stays minimal even if internals grow richer.
- Feedback is a first-class product feature.
- Graph, proof, policy, and contradiction concepts remain internal in v1.

---

## Closing line

**Neural Ledger v1 must feel almost embarrassingly simple at the surface, while quietly carrying the beginnings of a richer memory judgement engine underneath.**
