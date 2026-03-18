# 30 — Build Phases

## Purpose

This document defines the delivery sequence for **Neural Ledger**.

The goal is not merely to ship software. The goal is to ship a memory engine whose value becomes more legible and more credible at the end of each phase.

Each phase must therefore satisfy four conditions:

1. It produces visible value.
2. It sharpens the product thesis rather than diluting it.
3. It preserves the core prototype behaviours that made the original code interesting.
4. It leaves the system in a cleaner state than before.

---

## Delivery principle

Neural Ledger should be built in the following progression:

\[
\text{prove usefulness} \rightarrow \text{prove retrieval improvement} \rightarrow \text{add persistence} \rightarrow \text{add governed shared memory} \rightarrow \text{strengthen evidence} \rightarrow \text{prepare release}
\]

This means the early phases are about **clarity and proof**, not backend breadth.

---

## Phase overview

| Phase | Name | Primary outcome | Status |
|---|---|---|---|
| 1 | Minimal package foundation | Installable package with tiny in-memory API | **Complete** |
| 2 | Canonical proof scenario | Reproducible demonstration that feedback improves recall | **Complete** |
| 3 | Persistence beyond process death | Memory survives restarts without changing the API | **Complete** |
| 3B | Shared memory for multiple agents | Multiple agents can use a governed shared ledger without collapsing into noise | **Complete** |
| 4 | Evidence and confidence strengthening | Retrieval becomes more trustworthy and more explainable | Upcoming |
| 5 | Public proof pack and release | Package is credible, legible, and ready for open release | Upcoming |

---

# Phase 1 — Minimal package foundation

## Objective

Create the smallest honest version of Neural Ledger as a usable Python package.

The purpose of this phase is to prove that the product can feel simple from the outside while hiding a richer internal engine.

## Scope

This phase includes:

- package setup and repository structure
- public `Memory` class
- public methods:
  - `remember(...)`
  - `remember_many(...)`
  - `recall(...)`
  - `feedback(...)`
- plain return types:
  - `MemoryRecord`
  - `MemoryHit`
  - `MemoryConfig`
- in-memory backend only
- minimal retrieval pipeline using current prototype behaviour where practical
- basic feedback learning wired into ranking

## Required preserved behaviours from prototype

The following behaviours must be preserved or clearly reintroduced:

- semantic retrieval
- keyword fallback
- path or neighbourhood expansion where useful
- ranking not based on similarity alone
- feedback-based strengthening or weakening
- freshness / decay hooks, even if simple at first

## Non-goals

This phase does **not** include:

- persistence beyond process lifetime
- Neo4j or other graph backends
- public contradiction APIs
- forgetting APIs
- broad framework adapters
- polished benchmark harness

## Deliverables

- installable package skeleton
- working public API
- one quickstart example
- one unit test per public method
- internal module boundaries established

## Acceptance criteria

Phase 1 is complete when:

1. A developer can install the package and use it in under five minutes.
2. The first successful usage requires no database, API key, or external service.
3. The package exposes only the tiny public API agreed in the feature spec.
4. The system already reflects the thesis that memory can learn from usefulness.

## Visible value at end of phase

A developer can write:

```python
from neural_ledger import Memory

mem = Memory()
mem.remember("User prefers terse updates")
hits = mem.recall("How should I answer?")
mem.feedback(hits, helped=True)
```

and get a real working result.

---

# Phase 2 — Canonical proof scenario

## Objective

Prove that Neural Ledger improves retrieval quality after feedback in a controlled, reproducible scenario.

This is the first phase that turns the product from an elegant idea into a credible claim.

## Scope

This phase includes:

- canonical scenario dataset
- baseline retrievers:
  - keyword
  - semantic-only
- Neural Ledger condition
- benchmark assertions
- plain Python demo script
- notebook walkthrough
- terminal-friendly run path

## Canonical scenario

The primary scenario for this phase is:

**Coding agent — failure memory**

Core arc:

\[
\text{attempt}_1 \rightarrow \text{failure} \rightarrow \text{remember cause} \rightarrow \text{recall on attempt}_2 \rightarrow \text{feedback} \rightarrow \text{better recall}
\]

## Metrics

The benchmark must include at least:

- useful hit in top 3
- mean useful rank
- rank improvement after feedback

## Non-goals

This phase does **not** include:

- full persistence layer
- public policy API
- advanced backend abstraction work
- broad benchmark families across many domains

## Deliverables

- scenario spec
- benchmark dataset
- reproducible benchmark script or test
- example script
- notebook
- concise benchmark table for docs

## Acceptance criteria

Phase 2 is complete when:

1. Neural Ledger clearly outperforms keyword retrieval on the canonical scenario.
2. Neural Ledger matches or exceeds semantic-only retrieval before feedback.
3. Neural Ledger clearly improves ranking after feedback.
4. The proof can be run as a script, not only as a notebook.

## Visible value at end of phase

A skeptical engineer can run one command and see that feedback changes what the system retrieves.

---

# Phase 3 — Persistence beyond process death

## Objective

Allow memory to survive restarts without changing the public API.

This is the phase where Neural Ledger moves beyond purely in-memory operation.

## Scope

This phase includes:

- storage abstraction introduced cleanly
- default persistence backend added
- migration from volatile-only store to persistent record storage
- stable namespace handling
- load / save behaviour that preserves public simplicity

## Recommended backend sequence

The order should be:

1. local SQLite or similarly boring persistence
2. optional Postgres-backed store
3. graph backend only later if warranted

## Why this phase exists

This phase proves:

- memory can survive process death,
- the public API remains stable,
- storage is an implementation detail rather than the product identity.

## Non-goals

This phase does **not** include:

- Neo4j as a flagship feature
- backend proliferation
- making developers choose infrastructure on day one
- public graph management tools

## Deliverables

- persistent `RecordStore`
- basic persistent `LinkStore` if needed
- config options for persistence path / connection
- tests for restart survival
- migration notes in docs

## Acceptance criteria

Phase 3 is complete when:

1. A memory stored in one process can be recalled in a later process.
2. The public API remains unchanged.
3. Setup remains light enough for a developer to start locally with little friction.
4. The persistent backend does not dominate the product story.

## Visible value at end of phase

A developer can store memory locally, restart the process, and still recall the same records through the unchanged public API.

---

# Phase 3B — Shared memory for multiple agents

## Objective

Allow multiple agents to read from and write to a shared memory substrate with provenance, visibility, and conflict safety.

This phase extends Neural Ledger from single-agent memory into governed collective memory without turning the product into a loose “hive mind” abstraction.

## Scope

This phase includes:

- `agent_id` on writes
- provenance attached to shared records and links
- visibility or namespace rules for local vs shared memory
- read policy for local-only, shared-only, or merged recall
- conflict-aware handling when agents disagree
- tests proving that one agent can benefit from another agent’s useful prior memory

## Design stance

The preferred model is:

\[
\text{local agent memory} + \text{shared ledger memory}
\]

Not every memory should immediately become globally shared.

## Non-goals

This phase does **not** include:

- a public “hive mind” API
- free-for-all shared writes with no provenance
- multi-agent orchestration as the main product story
- complex permissions systems beyond what is needed for safe shared recall

## Deliverables

- internal support for `agent_id`, provenance, and visibility
- shared-memory read/write path
- at least one multi-agent proof scenario
- documentation on local vs shared memory semantics
- tests for conflict safety and provenance-preserving recall

## Acceptance criteria

Phase 3B is complete when:

1. Two or more agents can write to a shared memory substrate without losing provenance.
2. An agent can recall useful shared memory produced by another agent.
3. The system can distinguish local memory from shared memory during retrieval.
4. Conflicting shared memories remain inspectable rather than silently collapsed.

## Visible value at end of phase

A developer can run two agents against the same governed memory substrate and see one agent benefit from another’s prior learning without turning the ledger into untraceable noise.

---

# Phase 4 — Evidence and confidence strengthening

## Objective

Strengthen the system’s ability to judge what should be trusted, not merely what should be recalled.

This phase deepens the product’s core wedge: memory judgement.

## Scope

This phase includes:

- stronger confidence and uncertainty modelling
- clearer `why` explanations
- more explicit handling of conflicting evidence
- improved ranking behaviour that uses trust signals more deliberately
- better diagnostics around stale or weak memory

## Non-goals

This phase does **not** include:

- making every internal policy publicly configurable
- turning the product into a research framework
- heavy infrastructure expansion unrelated to trust or evidence

## Deliverables

- strengthened confidence logic
- improved uncertainty handling
- explainability improvements
- tests for conflict-heavy cases
- documentation of trust-related behaviour

## Acceptance criteria

Phase 4 is complete when:

1. Retrieval quality is more explainable than in earlier phases.
2. Conflicting evidence behaves predictably and inspectably.
3. Trust signals improve ranking in at least one benchmarked case.
4. The package still feels simple from the outside.

## Visible value at end of phase

Users can see not only *what* was recalled, but *why it earned trust*.

---

# Phase 5 — Public proof pack and release

## Objective

Prepare Neural Ledger for credible public release.

This phase is about adoption, clarity, and trust.

## Scope

This phase includes:

- polished README
- benchmark summary
- example scripts
- docs pages
- one notebook
- one terminal-friendly demo
- release packaging and versioning
- contribution guidance

## Required proof surfaces

The release must present the same core scenario across multiple media:

- README snippet
- plain Python example
- benchmark or test
- notebook
- terminal demo or GIF
- docs page

## Non-goals

This phase does **not** include:

- trying to solve every memory problem
- broad adapter matrix
- speculative enterprise features
- backend sprawl presented as product depth

## Deliverables

- first public release candidate
- proof pack
- installation instructions
- release notes
- contributor-friendly repo layout

## Acceptance criteria

Phase 5 is complete when:

1. The package can be installed and tried quickly.
2. The proof pack is compelling across more than one medium.
3. The public message is coherent and not overclaimed.
4. The project clearly communicates its wedge: learning what past experience is useful.

## Visible value at end of phase

An engineer can land on the repository and think:

**“I can use Neural Ledger in my stack.”**

---

# Cross-phase rules

The following rules apply throughout all phases.

## Rule 1 — Preserve the wedge

The product is not a generic memory framework. It is a memory engine centred on **judgement, usefulness, and feedback**.

## Rule 2 — Keep the front door tiny

The public API must remain simple even if the engine grows richer.

## Rule 3 — Proof before infrastructure theatre

New infrastructure should be added only after it supports a proven product claim.

## Rule 4 — Scenarios govern design

The benchmark scenarios are not side material. They are part of the product contract.

## Rule 5 — Preserve interesting prototype mechanics

The following must not be lost through refactoring:

- semantic retrieval
- keyword fallback
- graph/path expansion
- per-record usefulness prior (updated by feedback; scales candidate scores before path expansion)
- feedback learning
- evidence history
- confidence / uncertainty
- decay / freshness
- circularity checks
- observability

---

# Risks and mitigation

## Risk 1 — Drift into generic memory language

**Mitigation:** keep the doctrine and source-truth documents close to the implementation.

## Risk 2 — Overengineering the public API

**Mitigation:** require every public concept to justify itself in under five minutes of user value.

## Risk 3 — Infrastructure before proof

**Mitigation:** do not move beyond in-memory until the product claim has been demonstrated.

## Risk 4 — Losing fidelity from the prototype

**Mitigation:** use Doc 00 as a standing contract and review refactors against it.

---

# Locked decisions

1. Neural Ledger will begin as an in-memory package with a tiny public API.
2. Persistence beyond process death begins in **Phase 3**, not earlier.
3. Governed shared memory for multiple agents begins in **Phase 3B**, after persistence is proven.
4. Neo4j or other graph backends are deferred until later and are not part of the early public story.
5. The canonical scenario for proof is the **coding-agent failure-memory** scenario.
6. Every phase must end in visible value, not internal activity alone.
7. The interesting mechanics from the original prototype are considered part of the product identity and must be preserved deliberately.
