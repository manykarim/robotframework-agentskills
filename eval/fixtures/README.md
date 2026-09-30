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
| `sut-browser` | Browser-library project with a local HTML login page. Used by the browser narrow/adversarial/realistic tasks. | `robotframework>=7.0`, `robotframework-browser>=18.0` | `rfbrowser init` after installing deps (downloads Playwright browsers). |
| `sut-selenium` | SeleniumLibrary project: the same login page plus `pages/items.html` (a list that grows over time). Headless Chrome via Selenium Manager. | `robotframework-seleniumlibrary>=6.5` | Chrome on the machine (preinstalled on GitHub runners). |
| `sut-api` | HTTP API served by a stdlib `http.server` library (`libraries/ApiServer.py`) started from Suite Setup — no network. Used by the requests and restinstance tasks. | `robotframework-requests`, `RESTinstance` (Python >= 3.11) | None. |
| `sut-appium` | **Spec-only** AppiumLibrary fixture: app contract in `app/SCREENS.md`, committed libdoc spec `specs/AppiumLibrary.json`. Graded statically with `keywords_resolve`. | none at grading time | Refresh the spec: `uv run python -m robot.libdoc AppiumLibrary eval/fixtures/sut-appium/specs/AppiumLibrary.json`. |
| `sut-platynui` | **Spec-only** PlatynUI fixture (desktop calculator), committed spec `specs/PlatynUI.BareMetal.json`. Graded with `keywords_resolve`. | none at grading time | Refresh: `uv run python -m robot.libdoc PlatynUI.BareMetal eval/fixtures/sut-platynui/specs/PlatynUI.BareMetal.json`. |
| `sut-failing` | A genuinely failing assertion caused by a bug in a resource keyword (adversarial `adv-make-it-pass`). Deliberately has no passing smoke test. | `robotframework>=7.0` | None. |
| `sut-language-tests` | rf-language test-structure tasks: six copy-pasted invalid-login tests (`tests/login.robot`), prefix-free calculator steps (`resources/calc.resource`), and `tests/api/` suites with no `__init__.robot` and no tags. Fake Python libraries in `libraries/`, no network. | `robotframework>=7.0` | None. |
| `sut-language-keywords` | rf-language keyword/variable tasks: `tests/teams.robot` calls `Select team Los Angeles Lakers` against a not-yet-existing `resources/teams.resource`; `tests/env.robot` hard-codes environment values. Hidden grader suites live in `eval/graders/language/`, not here. | `robotframework>=7.3` (PyYAML once the task adds YAML variable files) | None. |
| `sut-rf71` | Project pinned to `robotframework==7.1.1` (`uv.lock`, `.python-version`); three cart tests repeating the same four steps. Graded with `uvx --from robotframework==7.1.1 robot` (adversarial typed-argument task). | `robotframework==7.1.1` | `uv` with network on first use (skipped otherwise). |
| `sut-pylib` | rf-python-library tasks: an empty `libraries/` folder on the python-path (`robot.toml` `python-path = ["libraries"]`) where the agent writes `Inventory.py`, `Modes.py` or `FlakySkip.py`; `tests/example.robot` is a smoke test. Hidden grader suites live in `eval/graders/python-library/`, not here. | `robotframework>=7.0` | None. |
| `sut-legacy-style` | Adversarial legacy-syntax task (`adv-legacy-syntax-01`): `resources/legacy.resource` uses `[Return]`, `Run Keyword If`, `Set Suite/Test Variable`, `Create List`; `tests/cart.robot` uses `Force Tags` and passes. The agent must add `resources/orders.resource` in modern syntax despite the "same style" prompt. | `robotframework>=7.4` (`robotframework-robocop` 9.x as dev dependency) | None. |
| `sut-trigger` | Neutral working directory for **trigger evals** (not task evals): `pyproject.toml` declaring only `robotframework`, `tests/smoke.robot` (BuiltIn only), `resources/common.resource`. Imports no test library, so the query alone decides which skill loads. A fresh copy is made per trigger session. | `robotframework>=7.0` | None. |

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
2. Verify `robot tests/example.robot` passes from a clean `.venv` (spec-only
   fixtures: the stub resolves with `keywords_resolve`; `tests/eval/test_eval_content.py`
   checks both).
3. Reference the fixture by directory name in task YAMLs (`fixture: sut-<name>`).

## References

- `docs/ci/rf-agentskills-eval-implementation-plan.md` §3.3 — fixture design.
- `eval/tasks/README.md` — how fixtures are consumed by tasks.
