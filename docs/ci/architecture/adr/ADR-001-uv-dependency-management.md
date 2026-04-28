# ADR-001: `uv` for Dependency & Environment Management

**Status:** Accepted
**Date:** 2026-04-14
**Deciders:** System Architecture
**Related:** ADR-002, ADR-005

---

## Context

The evaluation subsystem (`eval/`) is a new Python package that will be:

1. **Run in CI** (GitHub Actions) on every PR affecting `skills/`, `plugins/`, or `eval/`.
2. **Run locally** by developers before pushing.
3. **Scheduled** weekly as a longitudinal canary.
4. **Dependent on scientific Python stack** (polars, scipy, numpy) and `robotframework>=7.0`
   for the grader.

Startup time matters: the CI job spins up the env from scratch, and the weekly canary runs
overnight against dozens of cells. The existing project uses `pip + pytest` for the plugin
tests, which is fine for a handful of stdlib-only tests but does not scale to a scientific
stack with locked versions and reproducible builds.

Options considered:

1. `pip` + `requirements.txt`
2. `pip-tools`
3. `poetry`
4. `pdm`
5. `uv`

Criteria:

- **Reproducibility** — CI must install the exact same versions as local dev.
- **Speed** — CI cold-install time is a recurring cost.
- **Lockfile quality** — hash-verified, platform-aware.
- **Python version management** — we need Python 3.12 without relying on the runner's
  preinstalled version.
- **Footprint** — minimal extra tooling; must coexist with the existing `pip`-based plugin
  tests without conflict.
- **Stability** — not a moving target that will require rework in 6 months.

---

## Decision

**Adopt `uv` (Astral) as the sole dependency and environment manager for the
`eval/` subsystem.**

Specifically:

- `eval/pyproject.toml` is the single source of truth for dependencies.
- `eval/uv.lock` is committed and hash-verified.
- `eval/.python-version` pins the interpreter (3.12) for `uv python install`.
- All CI and local commands are invoked via `uv run <cmd>` — no activation needed.
- The entry point is `uv run rf-eval …`.
- The existing `pip`-managed `tests/` at the repo root (for plugin validation) is **not
  migrated**. `uv` is scoped to `eval/` to avoid disrupting the sync-skills pipeline.

---

## Consequences

### Positive

- **10–100× faster installs** than `pip` (Rust-based resolver + parallel downloads). Cold
  CI install drops from ~40 s to ~3 s for the eval dependency set.
- **Deterministic builds** via `uv.lock` with cryptographic hashes. No surprise upgrades.
- **Built-in Python interpreter management** (`uv python install 3.12`) — no dependency on
  the runner's preinstalled Python or on `actions/setup-python` quirks.
- **Single tool** — `uv` replaces `pip`, `pip-tools`, `pipx`, `venv`, `virtualenv`, and
  `pyenv`. Lower maintenance burden.
- **PEP 621 compliant** — `pyproject.toml` is portable; if `uv` is abandoned we can switch
  to `pip install -e .` with minimal edits.
- **Workspace support** — if the eval grows into multiple sibling packages later (e.g.,
  `eval-telemetry`, `eval-grader`), `uv` supports workspaces natively.

### Negative

- **Astral is a relatively young company.** Mitigated by: `uv` is open-source (Apache 2 /
  MIT), the lockfile is a standard format that other tools can adopt, and `pyproject.toml`
  is portable.
- **Developers must install `uv` locally.** Mitigated by: one-line install
  (`curl -LsSf https://astral.sh/uv/install.sh | sh`), and CI installs it via the official
  action. README will document both paths.
- **Two Python package managers in the repo** (`pip` for root tests, `uv` for `eval/`).
  Mitigated by: they live in separate directories with separate virtualenvs; no shared
  state. The README will explicitly document which tool owns which tree.

### Neutral

- Lockfile size — `uv.lock` for the eval dependency set is ~30–80 KB, comparable to
  `poetry.lock`.

---

## Alternatives Considered

### `pip` + `requirements.txt`
- **Pros:** Universally available; zero new tooling.
- **Cons:** No lockfile by default; `pip freeze` produces un-hashed, non-portable output;
  slow resolver on a scientific stack; no Python version management.
- **Why rejected:** Reproducibility gaps unacceptable for a harness whose output is a
  release gate.

### `pip-tools` (`pip-compile` + `pip-sync`)
- **Pros:** Real lockfile with hashes; works with `pip`.
- **Cons:** Two-step workflow; slow; no Python version management; abandoned-adjacent
  (maintained but minimal development).
- **Why rejected:** `uv` supersedes it on every axis and is maintained by a well-funded team.

### `poetry`
- **Pros:** Mature; wide adoption; good DX.
- **Cons:** Slow resolver (documented pain on scipy/numpy); opinionated about build
  backend; historically breaks on edge-case dependency specifiers; separate virtualenv
  activation flow.
- **Why rejected:** Speed (10–50× slower than `uv` on our stack) and ongoing friction with
  scientific dependencies.

### `pdm`
- **Pros:** PEP 621 native; fast; supports lockfile with hashes.
- **Cons:** Smaller ecosystem; fewer CI recipes; less momentum than `uv`.
- **Why rejected:** `uv` has comparable features, is faster, and has overtaken `pdm` in
  mindshare through 2025–2026.

### `hatch`
- **Pros:** Official PyPA tool; good for build/test isolation.
- **Cons:** Not a primary dependency manager; typically used alongside `pip` or `uv`.
- **Why rejected:** Solves a different problem.

---

## Implementation Notes (for Coder agents, not for this ADR to execute)

- `eval/pyproject.toml` declares `[project.scripts] rf-eval = "..."` — `uv run rf-eval`
  works out of the box.
- CI uses `astral-sh/setup-uv@v3` followed by `uv sync --frozen`.
- Dev workflow: `cd eval && uv sync` once, then `uv run rf-eval plan …`.
- Upgrades: `uv lock --upgrade-package <name>`; commit the new `uv.lock`.
- Do **not** commit `eval/.venv/`.

---

## References

- `uv` docs: https://docs.astral.sh/uv/
- PEP 621 (pyproject.toml metadata): https://peps.python.org/pep-0621/
- Parent project's existing `pip`-based plugin tests: `tests/` at repo root
