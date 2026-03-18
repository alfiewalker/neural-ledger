# 00 — Source Truth and Fidelity Contract

## Status
Locked foundation document.

## Purpose
This document preserves the core truth of the Neural Ledger project before feature creep, implementation convenience, or polished abstraction dilute what is actually interesting.

Its job is to record:
- what has already been agreed,
- what the project is trying to become,
- what must not be lost from the original prototype,
- what is intentionally deferred,
- and what all later documents must remain consistent with.

This is not a marketing document.
This is the fidelity anchor for the project.

---

## 1. Project thesis

**Neural Ledger is a lightweight memory engine that helps systems remember useful things, recall what matters, and learn from feedback.**

The deeper thesis is sharper:

**Memory is not storage. It is judgement.**

Neural Ledger should not merely accumulate notes, facts, or vectors.
It should govern:
- what deserves to become memory,
- what should be trusted,
- what should be retrieved now,
- and what should weaken or fade.

This project is therefore not primarily about databases, graph infrastructure, or generic long-term memory.
It is about building a memory layer that improves retrieval quality over time through feedback and disciplined internal structure.

---

## 2. Core problem being solved

Most memory systems in agent and software stacks stop at one or both of these:
- store past information,
- retrieve similar information later.

That is useful but incomplete.

The harder problem is:

> Given a new experience, what should the system remember, how should it connect it, how strongly should it trust it, and how should later feedback change retrieval?

The project exists to address that gap.

Neural Ledger is solving for systems that need to:
- retain useful experience,
- retrieve the smallest useful context,
- adapt retrieval based on what actually helped,
- remain inspectable rather than magical,
- and begin simple enough for real adoption.

---

## 3. Product posture

### What Neural Ledger is
- a lightweight memory engine,
- easy to start,
- internally richer than its public surface,
- feedback-aware,
- retrieval-oriented,
- designed to learn usefulness rather than only similarity.

### What Neural Ledger is not
- a thin vector-store wrapper,
- a graph database pitch disguised as a framework,
- an ontology-first system that forces modelling on day one,
- an LLM-everywhere abstraction layer,
- a kitchen-sink “agent memory platform” in v1.

---

## 4. Public product principle

**Easy to start. Deep to grow.**

The first-use experience must be frictionless.
A developer should get value without choosing a graph backend, defining schemas, or understanding the internal ontology.

The public API is intentionally tiny:

```python
from Neural Ledger import Memory

mem = Memory()
mem.remember("User prefers terse weekly updates")
hits = mem.recall("How should I write the update?")
mem.feedback(hits, helped=True)
```

This simplicity is not accidental. It is a product constraint.

---

## 5. Locked public API direction

The public API for v1 is based on three core verbs:

- `remember(...)`
- `recall(...)`
- `feedback(...)`

With one convenience addition:

- `remember_many(...)`

The user should only need to understand this mental model:
- **remember** stores experience,
- **recall** retrieves what matters,
- **feedback** teaches the system what was useful.

Anything heavier belongs behind the curtain.

---

## 6. Core behaviours preserved from the original prototype

These behaviours are the most important technical inheritance from the original code and must not be lost during refactor, packaging, or simplification.

### 6.1 Semantic retrieval with fallback
The prototype supports semantic retrieval of memory items and falls back to simpler matching when embeddings are unavailable or insufficient.

**Preserve:** retrieval must not depend on a single brittle mechanism.

### 6.2 Graph or path-aware expansion
The prototype does not merely return isolated nearest neighbours. It can traverse or expand through relationships to build context paths.

**Preserve:** memory retrieval should be able to move beyond flat similarity when useful structure exists.

### 6.3 Ranking is not purely similarity-based
The interesting part of the prototype is that ranking is influenced by more than lexical or embedding similarity. It includes path or activation-style considerations.

**Preserve:** the engine must remain capable of ranking by a richer notion of value than “nearest vector”.

### 6.4 Feedback-driven learning
The prototype updates memory usefulness through feedback, including strengthening and weakening of relationships.

**Preserve:** feedback is central, not decorative.

### 6.5 Evidence history
The prototype tracks history behind updates rather than only holding a final weight.

**Preserve:** the system should remember enough about why its current internal state exists.

### 6.6 Uncertainty and confidence
The prototype derives confidence from evidence and variance-like signals.

**Preserve:** memory strength should not be a naked scalar without interpretability.

### 6.7 Decay and freshness
The prototype includes age-based weakening or freshness handling.

**Preserve:** memory must respect time and not behave as if all experiences are equally alive forever.

### 6.8 Circularity inspection
The prototype can detect cycles or circular reasoning patterns.

**Preserve:** the system should remain inspectable for pathological self-reinforcement.

### 6.9 Observability and metrics
The metrics layer tracks retrieval quality, path quality, tool performance, and pattern-level signals.

**Preserve:** observability is a first-class engineering concern.

### 6.10 Public simplicity over internal exposure
The prototype contains richer internal concepts than should appear in the v1 public surface.

**Preserve:** keep the front door small even if the engine is sophisticated.

---

## 7. Internal richness that may exist without being public

The internal engine may use concepts such as:
- events,
- claims,
- relations,
- proofs,
- outcomes,
- policy,
- confidence,
- decay,
- path scoring,
- contradiction handling.

These are valid internal representations.
They are **not** required as public onboarding concepts in v1.

The governing rule is:

> Rich internals are welcome. Heavy public abstraction is not.

---

## 8. The key wedge

The differentiation is **not** “graph memory”.
That framing is too generic and already crowded.

The wedge is:

**Neural Ledger learns what past experience is useful under which conditions.**

This means the system should evolve from:
- retrieving similar items,

to:
- retrieving the most useful context,
- shaped by relevance, usefulness, confidence, recency, and conflict.

That wedge must remain visible in all later docs.

---

## 9. Proof philosophy

Scenarios alone are not enough.
Anecdotes alone are not enough.
Architecture alone is not enough.

The project will be proved through three layers:

### 9.1 Visceral proof
A short, vivid scenario that shows the retrieval shift.

### 9.2 Comparative proof
Controlled comparison against simple baselines.

### 9.3 Adoption proof
A drop-in experience that makes engineers think:

> I can use this in my stack.

This leads to the rule:

**One benchmarked scenario, many proof surfaces.**

The same scenario should be rendered through:
- README,
- Python script,
- benchmark test,
- notebook,
- terminal demo,
- documentation page.

---

## 10. Canonical early proof scenario

The canonical first scenario is locked as:

**Coding agent — failure memory**

Core arc:

```text
attempt -> failure -> remember cause -> later similar query -> feedback -> better ranking
```

Why this scenario is first:
- easy to understand,
- easy to benchmark,
- close to engineering pain,
- suitable for scripts, tests, notebooks, and terminal demos.

This scenario is the first proof vehicle for the project.

---

## 11. Phase boundaries already agreed

### Phase 1 / v1
- in-memory only,
- tiny public API,
- no heavy infrastructure,
- prove usefulness first.

### Phase 2 / v2
- move beyond in-memory with simple persistence,
- likely SQLite first,
- possibly Postgres later,
- keep public API stable.

### Phase 3 / v3
- optional true graph backends,
- such as Neo4j,
- only after internal seams are honest.

This phase order is deliberate:

```text
prove usefulness -> add persistence -> add infrastructure flexibility
```

---

## 12. Locked non-goals for v1

The following are explicitly **not** part of the first version:
- Neo4j as a primary story,
- public contradiction policy configuration,
- public proof-chain objects,
- forgetting API,
- broad agent-framework integrations,
- ontology-heavy modelling,
- excessive config surfaces,
- many backends before one beautiful beginner flow.

---

## 13. Risks this document is meant to prevent

This document exists to stop the project drifting into one of these traps:

### 13.1 Generic memory-framework drift
Where the project becomes a vague “agent memory” package with no sharp thesis.

### 13.2 Infrastructure theatre
Where graph backends and plugins overshadow the actual innovation.

### 13.3 Public overengineering
Where internal concepts leak into the beginner experience and kill adoption.

### 13.4 Benchmark-free rhetoric
Where the idea sounds clever but is not proved against simple baselines.

### 13.5 Prototype amnesia
Where the most interesting behaviours from the original code are lost during cleanup.

---

## 14. Document consistency rules

All later documents must remain consistent with the following constraints:

1. The public API stays tiny.
2. The wedge is memory judgement, not graph storage.
3. Feedback is central.
4. The original prototype’s interesting behaviours remain preserved internally.
5. Proof precedes infrastructure expansion.
6. v1 is in-memory first.
7. Scenarios drive evaluation.
8. Simplicity for adoption is a hard requirement.

If a future document conflicts with these, this document wins unless the decision log explicitly supersedes it.

---

## 15. Locked decisions

The following decisions are locked at this stage:

- The project thesis is **memory as judgement**.
- The public API is centred on `remember`, `recall`, and `feedback`.
- Internal richness may exceed public complexity.
- The first proof scenario is **coding agent — failure memory**.
- v1 remains **in-memory**.
- Persistence begins in **Phase 2**.
- Optional graph backends begin in **Phase 3**.
- The project must preserve the original prototype’s feedback-aware, path-aware, uncertainty-aware behaviours.
- Proof must be delivered across multiple media, not notebooks alone.

---

## 16. One line to carry forward

**Build the memory layer that decides what deserves to become memory.**
