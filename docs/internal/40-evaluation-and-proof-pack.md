# 40 — Evaluation and Proof Pack

## Purpose

This document defines how **Neural Ledger** proves its value.

The aim is not merely to show that the system runs. The aim is to show, in a way that is **clear, comparative, reproducible, and adoptable**, that Neural Ledger improves memory usefulness over time.

In practical terms, this means the project must answer three questions for an engineer evaluating it:

1. **Does it work?**
2. **Is it better than my current baseline?**
3. **Can I use it in my stack without pain?**

This document describes the proof strategy, evaluation artefacts, benchmark structure, and release proof pack required to make that case convincingly.

---

## Scope

This document covers:

- evaluation philosophy,
- canonical scenarios,
- baseline systems,
- benchmark metrics,
- required proof surfaces,
- required artefacts for public release,
- acceptance criteria for credibility.

This document does **not** define internal architecture, package module boundaries, or implementation details already covered elsewhere.

---

## Core Principle

**One benchmarked scenario, many proof surfaces.**

Neural Ledger should not rely on a single notebook, a single GIF, or a single README example.

Instead, one canonical scenario must be expressed consistently across multiple surfaces so that different engineers can evaluate the project in the medium they trust.

The same underlying scenario should power:

- the README proof snippet,
- the plain Python example,
- the benchmark test,
- the notebook,
- the terminal demo,
- the docs page,
- and any public media asset.

This keeps the message sharp and the evidence internally consistent.

---

## Proof Philosophy

Compelling proof for Neural Ledger must satisfy four properties.

### 1. Concrete

The proof must show a specific useful shift.

Not:

> “Memory got better.”

But:

> “After feedback, the prior token-expiry cause rose above misleading rate-limit context.”

### 2. Comparative

The proof must compare Neural Ledger to something simple and credible.

At minimum:

- keyword retrieval,
- semantic-only retrieval,
- Neural Ledger before learning,
- Neural Ledger after learning.

### 3. Reproducible

A reader must be able to run the proof themselves.

That means:

- a script,
- a test,
- a small dataset,
- and deterministic or bounded outputs.

### 4. Cheap to imagine in production

The proof must map cleanly into a real stack.

The reader should be able to say:

> “I can place this before prompt construction or after tool execution.”

That is more important than architectural spectacle.

---

## Canonical Proof Scenario

The initial release should centre on one scenario only.

### Scenario

**Coding agent — failure memory**

### Story

A coding agent previously encountered an authenticated API failure.
The true cause was an **expired token**.
Later, the agent faces a similar failure and asks for useful prior context.
A good memory system should surface the prior cause and successful remedy.
After feedback, it should rank those items more strongly than misleading near-matches.

### Why this scenario was chosen

This scenario is:

- easy to understand,
- close to real engineering pain,
- easy to benchmark,
- strong enough to show the value of memory learning,
- and easy to imagine in production use.

### Core arc

\[
\text{attempt}_1 \rightarrow \text{failure} \rightarrow \text{remember cause} \rightarrow \text{recall on attempt}_2 \rightarrow \text{feedback} \rightarrow \text{better ranking}
\]

---

## Baseline Systems

The proof must compare Neural Ledger against simple, boring baselines.

### Baseline 1 — Keyword retrieval

A straightforward lexical baseline.

Examples:

- token overlap,
- simple term scoring,
- BM25-style retrieval if easily available.

This baseline exists to show that Neural Ledger is better than simple search.

### Baseline 2 — Semantic-only retrieval

Embedding similarity only.

No path expansion. No learning. No evidence weighting.

This baseline exists to show that Neural Ledger is not merely “semantic search with nicer branding”.

### Neural Ledger conditions

The Neural Ledger system should be evaluated in at least two modes:

- **before feedback**,
- **after feedback**.

This is essential because the central claim is not only that Neural Ledger retrieves well, but that it **learns what proves useful**.

---

## Core Metrics

The benchmark should remain small and legible.

### Primary Metric — Useful hit in Top 3

\[
\text{Top3Useful} =
\begin{cases}
1 & \text{if at least one oracle-useful record appears in the top 3} \\
0 & \text{otherwise}
\end{cases}
\]

This is the most persuasive simple metric.

### Secondary Metric — Mean useful rank

\[
\text{MeanUsefulRank} = \frac{1}{|U|} \sum_{u \in U} \text{rank}(u)
\]

Where:
- \(U\) is the set of oracle-useful records,
- lower values are better.

### Third Metric — Ranking delta after feedback

\[
\Delta_{\text{rank}}(u) = \text{rank}_{before}(u) - \text{rank}_{after}(u)
\]

A positive value indicates improvement.

### Optional behavioural metric — Repeat failure avoided

Where relevant in the script/demo surface, measure whether the system avoids following a misleading remedy path on the second attempt.

This metric is especially useful for demos and storytelling, even if it is less “pure” than the ranking metrics.

---

## Required Proof Surfaces

The release proof must exist in multiple formats.

### 1. README proof snippet

Purpose:
- prove relevance quickly,
- show the product in under 20 seconds,
- give the reader a before/after glimpse.

Requirements:
- tiny code snippet,
- short scenario reference,
- one simple benchmark or outcome shift.

### 2. Plain Python script

Purpose:
- prove simplicity,
- serve engineers who do not use notebooks,
- provide a copy-paste runnable demo.

Required file shape:

```text
examples/
  coding_agent_failure_memory.py
```

The script should print:
- top results before feedback,
- the feedback event,
- top results after feedback,
- and rank changes for the key records.

### 3. Notebook

Purpose:
- explain the story more richly,
- visualise ranking shifts,
- help exploratory users understand the learning arc.

The notebook is optional as a medium for some engineers, but not optional as a development aid.

### 4. Benchmark test

Purpose:
- prove credibility,
- provide repeatable verification,
- support CI.

Required file shape:

```text
benchmarks/
  test_failure_memory.py
```

The test should assert at minimum:
- useful items rise after feedback,
- Neural Ledger meets or beats the semantic-only baseline after feedback.

### 5. Terminal demo / CLI surface

Purpose:
- provide a medium engineers trust,
- work well in GitHub and social posts,
- create a vivid proof moment.

This may be a direct Python command or a small CLI wrapper.

### 6. Docs page

Purpose:
- explain when the pattern is useful,
- show where it fits in a real stack,
- make the production insertion points obvious.

This page should answer:
- where Neural Ledger sits,
- when feedback enters,
- what kind of systems benefit.

### 7. Short media asset

Purpose:
- distribution,
- social proof,
- visual stickiness.

This should be a short terminal capture or clean animated clip, not a glossy cinematic video.

---

## Proof Artefact Structure

The following structure is recommended:

```text
proof/
  scenarios/
    coding_agent_failure_memory.yaml
  datasets/
    coding_agent_failure_memory.json
examples/
  coding_agent_failure_memory.py
notebooks/
  01_failure_memory.ipynb
benchmarks/
  test_failure_memory.py
docs/
  failure-memory.md
media/
  failure-memory-demo.gif
```

This makes the proof pack easy to navigate and keeps the scenario as the single source of truth.

---

## Canonical Proof Moment

The public proof should revolve around one memorable shift.

### Before feedback

1. GitHub API rate limit caused a temporary 403  
2. Check environment variables before retrying  
3. GitHub API request failed with 401 because the access token had expired

### After feedback

1. GitHub API request failed with 401 because the access token had expired  
2. Refreshing the GitHub token and retrying fixed the 401 error  
3. Check environment variables before retrying

This is the proof moment.

It is legible, human, and directly tied to engineering reality.

---

## Release-Quality Benchmark Expectations

Neural Ledger should not claim victory merely because it retrieves the right item once.

For the initial canonical scenario, release-quality proof should show that:

1. at least one oracle-useful record appears in the **Top 3** after feedback,
2. the **mean useful rank improves** after feedback,
3. Neural Ledger beats the **keyword** baseline,
4. Neural Ledger matches or exceeds the **semantic-only** baseline before feedback,
5. Neural Ledger clearly exceeds the **semantic-only** baseline after feedback,
6. the effect is visible across more than one query variant.

---

## Production Fit Proof

Beyond benchmark proof, Neural Ledger must show how it fits into a real system.

The proof pack should include at least three small integration sketches.

### Integration sketch 1 — plain Python / prompt builder

Neural Ledger sits before prompt construction:
- retrieve useful context,
- inject it into the prompt,
- collect feedback after the response.

### Integration sketch 2 — agent loop / tool execution

Neural Ledger sits around tool use:
- remember failure cause,
- recall useful prior context before the next attempt,
- record outcome.

### Integration sketch 3 — backend service

Neural Ledger sits inside a service endpoint:
- remember user or tool events,
- recall context for a downstream operation,
- apply feedback signals from outcome data.

These sketches do not need to be large integrations. Their purpose is to make placement obvious.

---

## What Does Not Count as Proof

The following do **not** count as sufficient proof by themselves:

- a philosophical essay,
- a single notebook,
- a pretty graph screenshot,
- broad claims about memory quality without baselines,
- infrastructure flexibility alone,
- backend plugin support alone.

Those may support the project, but they do not prove that Neural Ledger improves memory usefulness.

---

## Acceptance Criteria

This document is satisfied when the project can produce the following for the canonical scenario:

1. a runnable plain Python example,
2. a runnable benchmark test,
3. a README snippet,
4. a notebook,
5. a short terminal demo or media clip,
6. a docs page explaining where Neural Ledger fits,
7. benchmark results that show a visible post-feedback improvement,
8. consistency across all surfaces.

---

## Locked Decisions

- Neural Ledger will prove itself through **one benchmarked scenario rendered across many surfaces**.
- The first canonical scenario is **coding agent — failure memory**.
- Proof must be **comparative**, not merely demonstrative.
- The benchmark must compare against **keyword** and **semantic-only** baselines.
- The public proof must include at least one **non-notebook** runnable surface.
- The proof must show **improvement after feedback**, not merely static retrieval quality.
