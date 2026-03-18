# 90 — Decision Log

## Purpose

This document records the major decisions made for **Neural Ledger**, why they were made, what they imply, and what remains open.

Its role is not to restate the full specification. Its role is to prevent drift.

Every meaningful product, architecture, proof, or sequencing decision that affects the direction of the project should be logged here.

---

## Status

- Project name: **Neural Ledger**
- Current stage: **documentation-first foundation**
- Build posture: **proof-led, scenario-first, low-friction adoption**
- Public release posture: **free, open, credibility-building**

---

## How to use this log

A decision should be added here when it:

- changes the product direction,
- constrains the architecture,
- affects developer adoption,
- influences the proof strategy,
- alters phase boundaries,
- or preserves fidelity from the original prototype.

Each decision entry should include:

- **ID**
- **Decision**
- **Why**
- **Implications**
- **Status**

Statuses:
- **Locked** — agreed and should be treated as current truth
- **Open** — still under discussion
- **Deferred** — intentionally postponed
- **Superseded** — replaced by a newer decision

---

# Locked Decisions

## D-001 — The project is called Neural Ledger
**Decision**  
The project name is **Neural Ledger**.

**Why**  
The original working name no longer applies. The new name better matches the system’s identity as a governed record of useful memory rather than a generic memory wrapper.

**Implications**
- All future product and technical documentation should use **Neural Ledger**
- Package naming can be decided later, but project-facing material should remain consistent

**Status**  
Locked

---

## D-002 — The wedge is memory judgement, not generic memory storage
**Decision**  
Neural Ledger will be positioned around **memory judgement**.

**Why**  
The differentiated idea is not “graph memory” or “agent memory” in the generic sense. The interesting thesis is that systems should learn what deserves to become memory, what is useful, what should be trusted, and what should fade.

**Implications**
- Messaging should avoid generic “memory framework” language
- Product identity should emphasise usefulness, evidence, ranking, and learning
- Future docs should keep “storage” as a means, not the core story

**Status**  
Locked

---

## D-003 — The public API must stay tiny
**Decision**  
The v1 public surface will be built around a very small number of verbs:
- `remember(...)`
- `remember_many(...)`
- `recall(...)`
- `feedback(...)`

**Why**  
Low-friction adoption matters more than conceptual completeness in v1. The product should feel easy to add to a stack without requiring developers to understand a heavy ontology.

**Implications**
- Rich internal abstractions may exist, but they should not dominate the first user experience
- Public docs, examples, and demos must centre on the tiny API
- New public primitives require a very high bar

**Status**  
Locked

---

## D-004 — Rich primitives are internal, not day-one public concepts
**Decision**  
Concepts such as events, claims, relations, proof, and policy may exist internally, but they are not part of the beginner-facing API in v1.

**Why**  
These concepts are valuable as internal machinery, but too heavy as the public front door.

**Implications**
- Internal modules may evolve around typed intermediate representations
- Public materials should not require users to understand the internal ontology
- Advanced mode can expose more structure later if warranted

**Status**  
Locked

---

## D-005 — Proof comes before infrastructure breadth
**Decision**  
The project should prove value before investing heavily in integrations, multiple backends, or graph-database breadth.

**Why**  
Without proof, infrastructure work risks polishing plumbing before the core idea is validated.

**Implications**
- The build sequence prioritises scenario proof, benchmarkability, and public credibility
- Early engineering should optimise for clarity and truth, not maximum extensibility
- Expensive backend work is justified only after the public value proposition is proven

**Status**  
Locked

---

## D-006 — v1 is in-memory first
**Decision**  
The first public version should be in-memory by default.

**Why**  
It keeps setup friction low and matches the current prototype’s shape. It also allows the project to prove the idea without introducing database complexity too early.

**Implications**
- No database should be required for the first successful use
- The quickstart must work with zero infrastructure
- Persistence is a later milestone, not part of the first proof

**Status**  
Locked

---

## D-007 — Persistence belongs in Phase 3, not Phase 1
**Decision**  
Persistence beyond process death belongs in **Phase 3**. Graph backends such as Neo4j belong later.

**Why**  
The project should first prove the tiny API and the retrieval-improvement claim before adding storage complexity. There is a meaningful distinction between “feedback improves recall”, “memory survives restart”, and “memory supports interchangeable infrastructure.”

**Implications**
- Phase 2 remains the canonical proof phase
- Phase 3 focuses on simple persistence abstractions and a boring backend
- Phase 3B or later may introduce governed shared memory
- True graph backends remain later still

**Status**  
Locked

---

## D-008 — Neo4j is deferred
**Decision**  
Neo4j is explicitly deferred from the early phases.

**Why**  
Making Neo4j central too early risks turning the project into a graph-database story rather than a memory-judgement story.

**Implications**
- Initial technical specs should define storage seams without committing early to Neo4j
- Any future Neo4j support should follow proven internal abstractions
- Docs should not oversell graph backends in v1, v2, or v3 messaging

**Status**  
Deferred

---

## D-009 — The original prototype’s interesting behaviours must be preserved
**Decision**  
The following behaviours from the original prototype are part of the project’s fidelity contract and must not be casually lost:

- semantic retrieval,
- keyword fallback,
- graph or path expansion,
- ranking beyond pure similarity,
- feedback-driven strengthening and weakening,
- evidence history,
- uncertainty and confidence,
- decay and freshness,
- circularity or cycle checks,
- observability and metrics.

**Why**  
These are the parts that made the prototype intellectually interesting. Losing them would reduce the project to a generic memory wrapper.

**Implications**
- Refactors must preserve these behaviours or clearly justify changes
- Technical documentation should map old prototype behaviours to new module boundaries
- Public simplicity must not erase internal richness

**Status**  
Locked

---

## D-010 — Public simplicity, internal richness
**Decision**  
Neural Ledger should follow the pattern:
- thin public interface,
- thick engine.

**Why**  
That is the correct balance between developer adoption and architectural ambition.

**Implications**
- The public API remains simple
- Internal modules may become more sophisticated over time
- Documentation should distinguish between public surface and internal engine concepts

**Status**  
Locked

---

## D-011 — The canonical proof comes from one scenario first
**Decision**  
Neural Ledger should begin with one canonical proof scenario rather than many scattered examples.

**Why**  
A single benchmarked scenario is sharper, easier to maintain, and easier to render across multiple proof surfaces.

**Implications**
- README, script, benchmark, notebook, docs page, and terminal demo should all derive from the same underlying scenario
- Scenario data becomes a source of truth
- Additional scenarios come later

**Status**  
Locked

---

## D-012 — The first proof scenario is coding-agent failure memory
**Decision**  
The first canonical scenario is **coding agent — failure memory**.

**Why**  
It is legible, benchmarkable, close to real engineering pain, and easy for other engineers to imagine in their own stack.

**Implications**
- The first benchmark work should focus here
- The first public proof surfaces should all derive from this scenario
- Other scenarios should not distract from the initial claim

**Status**  
Locked

---

## D-013 — One canonical proof scenario, many proof surfaces
**Decision**  
Neural Ledger should present its first proof through one canonical scenario rendered across multiple surfaces: README, plain Python script, benchmark test, notebook, docs page, and terminal demo.

**Why**  
Different engineers trust different media. A notebook alone is not enough, but duplicating many unrelated demos would dilute the message.

**Implications**
- Proof assets should derive from one source scenario and dataset
- The script and test are mandatory, not optional add-ons
- The README should show the sharpest before/after moment from that same scenario

**Status**  
Locked

---

## D-014 — Shared memory is a Phase 3B extension
**Decision**  
Governed shared memory for multiple agents belongs in **Phase 3B** as an extension after single-agent value and persistence are proven.

**Why**  
Multiple agents can share memory technically, but useful collective memory requires provenance, visibility, and conflict handling. Without those, shared memory becomes noise rather than intelligence.

**Implications**
- Shared memory is not part of the v1, v2, or base v3 public story
- The architecture should preserve a seam for `agent_id`, provenance, and visibility
- The preferred model is local agent memory plus shared ledger memory, not one undifferentiated pool

**Status**  
Locked

---

## D-015 — Avoid “hive mind” as a build-phase label
**Decision**  
The project may discuss “hive mind” informally, but implementation documents should use the phrase **shared memory for multiple agents** or **governed collective memory**.

**Why**  
“Hive mind” is vivid but too loose for a technical milestone. It risks implying behaviour the system does not yet guarantee.

**Implications**
- Build and technical docs should use precise language
- Marketing language can stay more expressive later if the implementation earns it

**Status**  
Locked

---

## D-018 — Phase 3B shared memory model: local + shared, not a unified pool

**Decision**
Phase 3B introduces governed shared memory under the model:

```
local agent memory  +  shared ledger memory
```

The design is: sharing is explicit, not default. Every record has `visibility="local"`
by default. A record becomes shared only when the author explicitly sets
`visibility="shared"`. Recall defaults to `scope="local"`. Shared records are only
visible when the caller explicitly requests `scope="shared"` or `scope="merged"`.

The minimum additions are: `agent_id` on `Memory` constructor and `InternalRecord`;
`provenance` on `InternalRecord`; `visibility` on `InternalRecord`; `scope` on `recall()`.

**Why**
An undifferentiated shared pool defeats the purpose. If all memories from all agents are
visible by default, an agent cannot distinguish its own learned preferences from another
agent's working hypotheses. Noise accumulates faster than signal.

The "explicit sharing" model keeps the default experience identical to single-agent Phase 3A.
Multi-agent sharing is an opt-in capability, not a mandatory complexity.

The "local + shared" separation also maps cleanly to the existing namespace mechanism:
`visibility="shared"` means readable by all agents in the same namespace, not globally.
This avoids the need for a new access-control layer in Phase 3B.

**Implications**
- `Memory(agent_id=...)` is added to the constructor but remains optional
- Backward compatibility: records without agent_id are treated as legacy local records
- Phase 3B stays within Phase 3A's single-writer SQLite constraint
- Evidence attribution per agent (who gave which feedback) is deferred to Phase 4
- Shared scope is namespace-bounded (Q3 locked — see D-019)
- Full spec at `docs/implementation/32-phase-3b-shared-memory.md`

**Status**
Locked

---

## D-019 — Shared memory scope is namespace-bounded; global sharing is deferred

**Decision**
`visibility="shared"` makes a record visible to all agents within the **same namespace**.
It does not make the record visible across namespace boundaries.
Cross-namespace or global sharing is explicitly deferred.

**Why**
Namespace is the existing trust boundary in Neural Ledger. Making "shared" respect that
boundary keeps the invariant simple and legible: a namespace contains exactly what its
agents put into it. If shared records could cross namespaces, every recall would need
cross-namespace query logic, and the trust model would require a new access-control layer.

Deferring global sharing costs nothing now — namespaces can later be federated or given
explicit sharing permissions as a distinct Phase 5+ capability.

**Implications**
- Recall filtering for `scope="shared"` filters on `namespace AND visibility = "shared"`
- No new access-control primitives needed in Phase 3B
- Multi-tenant isolation is preserved: different tenants using different namespaces
  cannot see each other's shared records

**Status**
Locked

---

## D-017 — Phase 3 persistence is single-node, local durable persistence

**Decision**
Phase 3A persistence is explicitly scoped as:

> Single-node, single-writer, local durable persistence via SQLite.

The public API is unchanged: `Memory(persist_path="memory.db")` activates persistence.
The following are supported: restart survival of records, links (weight, evidence,
uncertainty), usefulness priors, and telemetry counters. Context manager lifecycle.
Namespace isolation within a shared file.

The following are explicitly **not** part of Phase 3A:
- Multi-process writers
- Concurrent in-process instances sharing a live cache
- Atomic feedback transactions (record, link, and metrics writes are committed separately)
- Schema migration tooling
- Graph database backends

**Why**
The distinction matters for trust. "Memory persists" is a claim that engineers will
evaluate against their production requirements. If we do not state what we mean by
"persist", the claim misleads. Phase 3A means: a local SQLite file, one writer, restart
survives, no distributed guarantees.

SQLite is the right first backend because: zero setup, zero dependencies, reliable at
single-process scope, well-understood failure modes. The `busy_timeout` pragma gives
tolerable behaviour if a second process briefly holds a write lock, without claiming
concurrent write safety.

Atomic feedback transactions are the most significant outstanding correctness gap: a
crash mid-feedback could leave usefulness updated but link evidence uncommitted. This is
acceptable in Phase 3A because the failure mode is a partial update (not corruption or
data loss) and the system will self-correct over subsequent interactions. Full
transactional feedback is appropriate for a future hardening phase.

**Implications**
- Docs and spec must state these boundaries plainly
- The public API does not change when multi-process or transactional feedback is added later
- Phase 3B (shared memory for multiple agents) will require addressing the single-writer
  limitation, likely through a server-side store or advisory locking

**Status**
Locked

---

## D-016 — Feedback requires a per-record usefulness prior, not only link learning

**Decision**
Each internal record carries a learned `usefulness` scalar (default 1.0, range [0.05, 2.0]).
Feedback updates this field directly, and it scales the record's candidate score before
path expansion. This is a first-class internal ranking signal, not a detail.

**Why**
During Phase 2 canonical proof development, it was discovered that link-weight learning
alone is insufficient to demote a misleading record. The root cause: after co-retrieval
linking connects the misleading record to useful neighbours, BFS path expansion can
traverse those links and award the misleading record a high path-bonus score, even after
its inbound links are weakened by negative feedback.

The fix is a direct per-record prior applied before path expansion. This suppresses the
misleading record's effective score regardless of graph topology. Without it, the benchmark
showed mean useful rank *worsening* after feedback (2.00 → 2.33). With it, the rank
improves as expected (2.00 → 1.67) and all canonical proof assertions pass.

This separated the learning into two channels:
- **record usefulness** — "Has this item itself been helpful before?"
- **link usefulness** — "Has traversing through this connection been helpful before?"

Both are preserved. Neither alone is sufficient.

**Implications**
- `InternalRecord` must carry a `usefulness: float` field
- `feedback.py` must update it alongside link weights
- `runtime._recall_inner` must scale candidate scores by usefulness before path expansion
- Technical spec and decision log must document this as a core internal mechanism
- External docs must not claim all useful records were uniformly promoted — only the net
  mean useful rank metric and the primary demotion/promotion story are reliable claims

**Status**
Locked

---

# Open Decisions

## O-001 — Package name on PyPI
**Question**  
Should the installable package use `neural-ledger`, `neural_ledger`, or another name?

**Why open**  
The project name is settled, but the final package name should account for package registry availability, branding, and clarity.

**Status**  
Open

---

## O-002 — First persistence backend after in-memory
**Question**  
Should the first persistence backend be SQLite, Postgres, or both?

**Why open**  
The principle is settled — persistence begins in Phase 3 — but the exact first backend is still open.

**Status**  
Open

---

## O-003 — Public exposure of advanced mode
**Question**  
When should advanced policy or typed primitives become public, if at all?

**Why open**  
The internal model may grow richer, but the public surface should remain disciplined. The timing and shape of expert mode are unresolved.

**Status**  
Open

---

# Deferred Decisions

## X-001 — Public forgetting API
**Decision area**  
A public `forget(...)` or equivalent API.

**Why deferred**  
Forgetting sounds simple but hides difficult semantic choices: delete, archive, weaken, retract, or preserve provenance.

**Status**  
Deferred

---

## X-002 — Public contradiction policy
**Decision area**  
Whether and how contradiction handling becomes part of the public API.

**Why deferred**  
Contradiction matters, but exposing it too early could burden adoption before the core product is proven.

**Status**  
Deferred

---

## X-003 — Broad framework integrations
**Decision area**  
Specific integrations with agent frameworks or orchestration ecosystems.

**Why deferred**  
The project should first prove value on its own terms before adapting to many ecosystems.

**Status**  
Deferred

---

# Change Protocol

If a locked decision changes:

1. add a new decision entry,
2. mark the old one as **Superseded**,
3. explain why the change was made,
4. identify which docs must be updated.

This prevents silent drift.

---

# Final Note

This log exists to defend the project from two common failures:

1. drifting into generic memory-framework language,
2. losing the prototype’s intellectually interesting mechanics during simplification.

Neural Ledger should remain easy to adopt, but it should not forget what made it worth building in the first place.
