# Fixtures

"System Under Test" (SUT) repositories used by the evaluation harness. Each
fixture is a small, self-contained Robot Framework project that an agent task
operates on.

## Reset policy

Fixtures are the single source of truth. The runner **copies each fixture
fresh** (`cp -r` or `git worktree add`) into a per-run scratch directory before
invoking Claude Code. Never run a task twice against the same directory — state
from the previous run will leak into the next.

Fixture directories under `eval/fixtures/` should be kept clean (no
`output.xml`, `log.html`, `report.html`, `.venv/`, etc. — see per-fixture
`.gitignore`).

## Available fixtures

| Name | Purpose | Dependencies | Extra setup |
|---|---|---|---|
| `sut-minimal` | Plain-text Robot Framework project. Shared keywords in a resource file. Used by narrow tasks that don't need a browser or network. | `robotframework>=7.0` | None. |
| `sut-browser` | Browser-library project with a local HTML login page. Used by realistic tasks that need real web interaction. | `robotframework>=7.0`, `robotframework-browser>=18.0` | `rfbrowser init` after installing deps (downloads Playwright browsers). |

## Prerequisites

### All fixtures

```bash
# Create a venv per fixture run (the runner does this automatically)
python -m venv .venv
source .venv/bin/activate
pip install -e .  # uses the fixture's pyproject.toml
```

### `sut-browser` only

After installing `robotframework-browser`, initialize Playwright:

```bash
rfbrowser init
```

This downloads the Playwright browser binaries (~400 MB on first run,
cached thereafter). The runner pre-warms this in its setup step so individual
task runs aren't penalized.

## Adding a new fixture

1. Create `eval/fixtures/sut-<name>/` with:
   - `pyproject.toml` declaring RF + any library deps.
   - `tests/example.robot` — a trivial passing test that proves the
     environment is usable.
   - `README.md` — one paragraph explaining the fixture's purpose.
   - `.gitignore` — at minimum: `output.xml log.html report.html .venv/`.
2. Verify `robot tests/example.robot` passes from a clean `.venv`.
3. Reference the fixture by directory name in task YAMLs (`fixture: sut-<name>`).

## References

- `docs/ci/rf-agentskills-eval-implementation-plan.md` §3.3 — fixture design.
- `eval/tasks/README.md` — how fixtures are consumed by tasks.
