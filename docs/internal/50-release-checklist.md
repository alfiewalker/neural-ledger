# 50 — v0.1.0 Release Checklist

This document is the pre-release gate for the first public alpha of Neural Ledger.
Work through it top-to-bottom. Do not ship until every item is checked.

---

## 1. Identity — fill in before anything else

- [x] Set real repo URL in `pyproject.toml` `[project.urls]` — `alfiewalker/neural-ledger`
- [x] Replace placeholder URL in README badges — GitHub badge added
- [x] Replace `"Neural Ledger contributors"` in `LICENSE` — `Copyright (c) 2026 Alfie Walker`
- [ ] Confirm package name `neural-ledger` is available on PyPI:
      `curl -s https://pypi.org/pypi/neural-ledger/json | python -m json.tool | grep '"name"'`
      If taken, choose an alternative and update `pyproject.toml`, README install command,
      `neural_ledger/__init__.py` `__version__`, and all import examples.

---

## 2. Version decision

- [x] Version locked at `0.1.0a1` in `pyproject.toml` and `neural_ledger/__init__.py`

Promote to `0.1.0` after a short soak period with real users.

---

## 3. Install sanity — verify from a clean environment

```bash
python -m venv /tmp/nl_release_test
source /tmp/nl_release_test/bin/activate
pip install -e .
```

- [ ] Install completes with no errors
- [ ] `python -c "from neural_ledger import Memory; print(Memory().__class__)"`
- [ ] `python examples/quickstart.py` — output is sensible, no exceptions
- [ ] `python examples/shared_memory_two_agents.py` — agent-b recalls agent-a's shared record
- [ ] `python examples/coding_agent_failure_memory.py` — proof scenario runs to completion
- [ ] `python -m pytest` — 144 tests pass

---

## 4. README front door

- [ ] Opening code snippet demonstrates **before → feedback → improved recall** (not just API syntax)
- [ ] Installation command matches actual published package name
- [ ] Shared memory section links to `docs/examples/shared-memory.md` and the example script
- [ ] Roadmap reflects current phase status (Phases 1–3B complete, 4–5 upcoming)
- [ ] No broken relative links in the rendered README (check via GitHub preview or `grip`)

---

## 5. Docs completeness

- [ ] `docs/examples/failure-memory.md` — benchmark numbers match actual script output
- [ ] `docs/examples/shared-memory.md` — code examples run without modification
- [ ] `docs/internal/30-build-phases.md` — phase table shows Phases 1–3B as Complete
- [ ] `docs/internal/90-decision-log.md` — D-016 through D-019 present

---

## 6. Package build and inspect

```bash
pip install build twine
python -m build
twine check dist/*
```

- [ ] `build` produces `dist/neural_ledger-VERSION.tar.gz` and `dist/neural_ledger-VERSION-py3-none-any.whl`
- [ ] `twine check dist/*` passes with no errors or warnings
- [ ] Inspect the wheel: `python -m zipfile -l dist/*.whl | grep neural_ledger` — confirm
      all subpackages present (`store/`, `retrieve/`, `learn/`, `internal/`, `telemetry/`)
- [ ] Spot-check that `examples/`, `tests/`, and `docs/` are **not** bundled in the wheel

---

## 7. Test PyPI (optional but recommended for first release)

```bash
twine upload --repository testpypi dist/*
pip install --index-url https://test.pypi.org/simple/ neural-ledger
python -c "import neural_ledger; print(neural_ledger.__version__)"
```

- [ ] Package installs cleanly from TestPyPI
- [ ] Version number matches expected

---

## 8. Tag and publish

```bash
git tag v0.1.0a1          # or v0.1.0
git push origin v0.1.0a1
twine upload dist/*
```

- [ ] Git tag pushed to remote
- [ ] PyPI upload succeeds
- [ ] PyPI project page renders README correctly (check https://pypi.org/project/neural-ledger/)
- [ ] PyPI badge in README resolves to correct version

---

## 9. GitHub release (if using GitHub)

- [ ] Create release from the tag
- [ ] Paste CHANGELOG `## [0.1.0]` section as the release body
- [ ] Attach no binaries (wheel is on PyPI; source is in the repo)

---

## 10. Post-release smoke test

```bash
pip install neural-ledger          # from real PyPI, not -e .
python -c "
from neural_ledger import Memory
mem = Memory()
mem.remember('GitHub 401 caused by expired token')
hits = mem.recall('GitHub auth error')
mem.feedback(hits, helped=True)
print('post-release smoke test: OK')
"
```

- [ ] Passes cleanly from a fresh install

---

## After release

Once the tag is cut and PyPI is live, the next steps are:

1. Update `[Unreleased]` section in `CHANGELOG.md` with any post-release fixes
2. Open Phase 4 planning (evidence attribution, per-agent feedback, explainable conflict handling)
3. Do not touch the public API without a version bump discussion
