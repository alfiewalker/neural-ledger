# 02 — Scenarios and Proof Strategy

## Purpose

This document defines how **Neural Ledger** will prove its value.

It exists to prevent the project from drifting into elegant theory without compelling evidence. The aim is not merely to describe the product, but to specify the scenarios, baselines, metrics, and proof surfaces that will make engineers say:

> I can use Neural Ledger in my stack.

This document is therefore the bridge between thesis and credibility.

---

## Audience

This document is for:

- the founder and core builders,
- contributors who need to understand what must be demonstrated,
- future users evaluating whether the system is practically useful,
- anyone building demos, examples, docs, benchmarks, or release material.

---

## Non-goals

This document does not define:

- the full public API,
- the internal architecture in detail,
- the storage backend plan,
- the full build roadmap.

Those belong in later documents.

---

## Why proof matters here

Neural Ledger is not a standard memory package.

Its thesis is sharper: memory should not merely store and retrieve. It should learn what is useful, under which conditions, and improve recall over time through feedback.

That is a stronger claim than “supports memory”. It requires proof.

Scenarios alone are not enough. Benchmarks alone are not enough. A persuasive proof stack must answer three silent questions every engineer has:

1. **Does it work?**
2. **Is it better than my current baseline?**
3. **Can I add it without pain?**

So Neural Ledger will prove itself through three layers:

- **Visceral proof** — a vivid scenario that makes the value obvious,
- **Comparative proof** — a reproducible benchmark against boring baselines,
- **Adoption proof** — examples and integrations that make stack fit obvious.

---

## Proof principle

### One benchmarked scenario, many proof surfaces

Neural Ledger should not build five unrelated demos.

It should build **one canonical scenario** first, then render it across several media:

- README snippet,
- plain Python script,
- benchmark test,
- notebook,
- terminal demo,
- docs page,
- short terminal recording or GIF.

The scenario is the source of truth. The media are merely surfaces.

This keeps the message coherent and prevents fragmented storytelling.

---

## Canonical scenario

## Coding agent — failure memory

### Core arc

\[
\text{attempt}_1 \rightarrow \text{failure} \rightarrow \text{remember cause} \rightarrow \text{recall on attempt}_2 \rightarrow \text{feedback} \rightarrow \text{better ranking}
\]

### Real-world story

A coding agent previously hit an API failure.
The true cause was an **expired token**.
Later, the agent encounters a similar authenticated GitHub API error and asks for context.
A good memory system should surface the prior cause quickly, then improve further after feedback.

### Why this scenario was chosen

This scenario is the first proof because it is:

- immediately legible,
- easy to benchmark,
- close to engineering pain,
- easy to imagine in production,
- well aligned with the current prototype’s interesting behaviour.

It shows not just storage, but **usefulness-aware recall**.

---

## Claim to prove

**After feedback, Neural Ledger ranks the prior useful failure memory higher than keyword-only and semantic-only baselines.**

That is the first hard claim.

Not “it stores memories”.
Not “it supports graphs”.
Not “it can be extended”.

The claim is about improved recall quality after experience and feedback.

---

## Scenario dataset design

The scenario dataset should stay deliberately small and honest.

### Dataset shape

The dataset should contain roughly **10 to 14 records**:

- **2 truly useful records**,
- **3 somewhat related but misleading records**,
- **5 to 9 noise records**.

This is important.
If the useful record is too obvious, the benchmark is childish.
If the dataset is too large, the proof becomes slow and unfocused.

### Example records

```yaml
scenario_id: coding_agent_failure_memory_v1

records:
  - id: r1
    kind: observation
    content: "GitHub API request failed with 401 because the access token had expired."
    tags: [github, api, auth, failure]
    useful_for: [q1, q2]

  - id: r2
    kind: procedure
    content: "Refreshing the GitHub token and retrying fixed the 401 error."
    tags: [github, api, auth, fix]
    useful_for: [q1, q2]

  - id: r3
    kind: observation
    content: "GitHub API rate limit caused a temporary 403 response."
    tags: [github, api, rate_limit, failure]
    useful_for: []

  - id: r4
    kind: observation
    content: "Slack webhook failed because the signing secret was missing."
    tags: [slack, webhook, auth, failure]
    useful_for: []

  - id: r5
    kind: note
    content: "Use terse bullet points in status updates."
    tags: [writing, preference]
    useful_for: []

  - id: r6
    kind: observation
    content: "Database connection failed due to an incorrect host value."
    tags: [database, config, failure]
    useful_for: []

  - id: r7
    kind: procedure
    content: "Check whether the environment variables are loaded before retrying an API call."
    tags: [api, env, troubleshooting]
    useful_for: [q2]

  - id: r8
    kind: observation
    content: "GitHub pull request fetch worked after widening repository permissions."
    tags: [github, permissions, success]
    useful_for: []

  - id: r9
    kind: note
    content: "Retry with exponential backoff for transient upstream failures."
    tags: [retry, resilience]
    useful_for: []

  - id: r10
    kind: observation
    content: "The CI pipeline failed because the package lockfile was out of date."
    tags: [ci, build, dependency]
    useful_for: []
```

---

## Queries

Use two queries.

### Query 1 — specific

```yaml
id: q1
text: "How should I fix this GitHub API 401 failure?"
oracle_useful: [r1, r2]
```

### Query 2 — broader

```yaml
id: q2
text: "What past context is most useful for a failing authenticated GitHub API call?"
oracle_useful: [r1, r2, r7]
```

Why two queries?
Because one exact-match query is too easy. The second tests whether the system generalises beyond surface wording.

---

## Benchmark phases

### Phase A — before feedback

Run all retrievers on `q1` and `q2`.

Compare:

- keyword baseline,
- semantic-only baseline,
- Neural Ledger with learning disabled.

This shows whether the retrieval core is already competent.

### Phase B — feedback event

Apply positive feedback to the truly useful hits:

```yaml
feedback:
  target_ids: [r1, r2]
  helped: 1.0
  reason: "These captured the true cause and the successful fix."
```

Optionally apply negative feedback to a misleading near-match:

```yaml
feedback_negative:
  target_ids: [r3]
  helped: 0.0
  reason: "Rate limiting looked similar but was not the cause."
```

### Phase C — after feedback

Run the same queries again.

Now compare:

- semantic-only baseline,
- Neural Ledger after feedback.

This is the core public proof.

---

## Baselines

Neural Ledger should not compare itself to fantasies. It should beat boring, legible baselines.

### Baseline 1 — keyword

Simple token overlap or BM25-style ranking.

Purpose:
- proves Neural Ledger is not merely better than nothing,
- provides a baseline any engineer understands.

### Baseline 2 — semantic-only

Embedding similarity only.
No path expansion.
No graph traversal.
No feedback learning.

Purpose:
- isolates whether the Neural Ledger advantage comes from usefulness-aware behaviour,
- prevents the project from claiming victories that are really just embedding wins.

### Neural Ledger condition

Semantic retrieval plus path/context expansion plus feedback learning.

This is the meaningful comparison.

---

## Metrics

Keep the benchmark metrics few, sharp, and interpretable.

### Primary metric — useful hit in top 3

\[
\text{Top3Useful} =
\begin{cases}
1 & \text{if any oracle-useful record appears in top 3} \\
0 & \text{otherwise}
\end{cases}
\]

This is the most persuasive simple metric.

### Secondary metric — mean useful rank

\[
\text{MeanUsefulRank} = \frac{1}{|U|} \sum_{u \in U} \text{rank}(u)
\]

Lower is better.

### Third metric — ranking delta after feedback

\[
\Delta_{\text{rank}}(u) = \text{rank}_{\text{before}}(u) - \text{rank}_{\text{after}}(u)
\]

Positive means improvement.

### Optional behavioural metric — repeat failure avoided

In the demo flow, count whether the agent repeats the wrong fix before the correct one.

This is excellent for scripts and demos, though slightly less pure as a benchmark metric.

---

## Success criteria

The canonical scenario is successful if all of the following hold:

1. Neural Ledger places at least one oracle-useful record in the **top 3** for both queries after feedback.
2. The **mean useful rank improves** after feedback.
3. Neural Ledger beats the **keyword** baseline on both queries.
4. Neural Ledger beats or matches **semantic-only** before feedback, then clearly beats it after feedback.
5. In the script or demo, the second attempt avoids the misleading “rate limit” path.

---

## Proof surfaces

The same scenario should appear in multiple forms.
Each surface has a different job.

### 1. README proof

Purpose: prove relevance in under 20 seconds.

Should include:
- a 12-line code example,
- a before-and-after retrieval snippet,
- one benchmark result.

### 2. Plain Python script

Purpose: prove simplicity for engineers who dislike notebooks.

Example:

```text
examples/coding_agent_failure_memory.py
```

Run with:

```bash
python examples/coding_agent_failure_memory.py
```

The script should print:
- top 5 before feedback,
- feedback applied,
- top 5 after feedback,
- rank changes for key useful records.

### 3. Notebook

Purpose: prove explainability and provide a guided walkthrough.

The notebook is valuable, but it must never be the only proof surface.

### 4. Benchmark test

Purpose: prove credibility.

Example:

```text
benchmarks/test_failure_memory.py
```

Run with:

```bash
pytest benchmarks -q
```

This is important because tests feel real to engineers in a way notebooks often do not.

### 5. Terminal demo or GIF

Purpose: prove vividness.

A short terminal recording should show:
- initial miss or weak ranking,
- feedback event,
- improved recall.

This is useful for GitHub, docs, and social surfaces.

### 6. Docs page

Purpose: prove stack fit.

A short page should answer:
- what problem this solves,
- the baseline behaviour,
- how Neural Ledger changes it,
- where it fits in an agent loop or backend flow.

---

## Proof artefact structure

```text
docs/
  02-scenarios-and-proof-strategy.md
proof/
  scenarios/
    coding_agent_failure_memory.yaml
  datasets/
    coding_agent_failure_memory.json
examples/
  coding_agent_failure_memory.py
benchmarks/
  test_failure_memory.py
docs/examples/
  failure-memory.md
media/
  failure-memory-demo.gif
notebooks/
  01_failure_memory.ipynb
```

The scenario definition is the source of truth.
Everything else derives from it.

---

## Adoption proof

To make engineers think “I can use this in my stack”, Neural Ledger must also show:

### Tiny setup

```python
from neural_ledger import Memory

mem = Memory()
mem.remember("User prefers terse updates")
hits = mem.recall("How should I answer?")
mem.feedback(hits, helped=True)
```

### Familiar outputs

Return plain Python objects.
Avoid ontology burden.
Avoid framework theatre.

### Clear insertion points

Show where Neural Ledger fits:
- before prompt construction,
- after tool execution,
- after user feedback,
- inside an agent loop,
- inside a backend service.

People adopt what they can place mentally.

---

## What this document locks

This document locks the following decisions:

1. The first public proof will be **coding agent — failure memory**.
2. Neural Ledger will prove itself through **one canonical scenario rendered across many proof surfaces**.
3. The baseline comparison set is:
   - keyword,
   - semantic-only,
   - Neural Ledger.
4. The primary benchmark story is **improved recall after feedback**.
5. A notebook is useful, but it is **not** sufficient on its own.
6. A plain Python script and a benchmark test are mandatory proof surfaces.

---

## Deferred scenarios

These are promising, but not first:

- support or assistant agent preference memory,
- research agent source-quality memory,
- procedural memory for repeated workflows,
- contradiction-aware memory,
- selective forgetting scenarios.

These may become later benchmark packs once the canonical scenario is in place.

---

## Closing line

**Neural Ledger should not prove that it can remember. It should prove that it can learn which memory is useful.**
