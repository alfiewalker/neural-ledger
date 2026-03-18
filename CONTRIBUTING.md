# Contributing to Neural Ledger

Neural Ledger is being built in the open. Contributions, issues, benchmarks, and well-argued criticism are welcome.

## Development setup

```bash
git clone https://github.com/alfiewalker/neural-ledger
cd neural-ledger
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

For semantic retrieval support (optional — the engine falls back to keyword retrieval without it):

```bash
pip install -e ".[dev,semantic]"
```

## Running the tests

```bash
python -m pytest
```

The full suite covers unit tests, integration tests (persistence, shared memory), and benchmark assertions. All 144 tests should pass.

## Running the examples

```bash
python examples/quickstart.py
python examples/shared_memory_two_agents.py
python examples/coding_agent_failure_memory.py
```

## Project layout

```
neural_ledger/
  api.py          public Memory façade
  types.py        public return types (MemoryRecord, MemoryHit, MemoryConfig)
  internal/       Runtime, Policy, Compiler — never exposed publicly
  store/          RecordStore and LinkStore (in-memory and SQLite)
  retrieve/       semantic → keyword fallback → path expansion → ranking
  learn/          feedback, decay, confidence
  telemetry/      Metrics

tests/            unit and integration tests
benchmarks/       canonical proof scenario
examples/         runnable scripts
docs/
  implementation/ specs, decision log, build phases
  examples/       long-form scenario docs
```

## Design constraints

A few rules that govern this project:

1. **The public API is frozen at v1.** `remember`, `recall`, `feedback` and their signatures must not change without a major version bump. New optional parameters are fine.
2. **No leaking internals.** Graph, policy, and proof-chain concepts must not appear in the public API or return types.
3. **Feedback is not decorative.** Every change to retrieval ranking must be traceable back to feedback signals.
4. **Preserve the interesting mechanics.** Semantic retrieval, keyword fallback, path expansion, usefulness prior, evidence history, decay, and uncertainty must all survive refactoring.

See `docs/internal/00-source-truth-and-fidelity.md` for the complete fidelity contract.

## What is worth contributing

- New benchmark scenarios that stress-test the feedback loop
- Improved `why` explanations that are more human-readable
- Performance improvements to the retrieval pipeline (without changing the public API)
- Bug reports with reproducible test cases
- Documentation improvements

## What is not in scope right now

- Neo4j or other graph backends
- Broad framework adapters (LangChain, LlamaIndex, etc.)
- Public contradiction API
- Explicit forgetting API

These are tracked as future phases.

## Commit style

Short imperative subject line, no period. Body optional. Example:

```
Add decay half-life to MemoryConfig

Allows callers to tune how quickly activation falls off.
Default preserves existing behaviour.
```

## Questions

Open an issue or start a discussion. The decision log (`docs/internal/90-decision-log.md`) records why key architectural choices were made — worth reading before proposing structural changes.
