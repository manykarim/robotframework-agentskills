---
name: rf-setup
description: "Use first, before reading pyproject.toml, to install or fix Robot Framework and libraries (uv, pip, venv)."
license: Apache-2.0
compatibility: Requires one of uv (preferred), Python 3.10+ with venv and pip, or Poetry 1.8+; network access to PyPI. Installs robotcode[all]>=2.8 into the project environment, which the other rf-agentskills skills and hooks require.
metadata:
  author: manykarim
  version: "3.0.0"
---

# Robot Framework Setup Skill

## When to use

Load this skill first, before reading pyproject.toml or answering from memory, when Robot Framework, a test library or its tooling has to be installed, added as a dependency or repaired:

- the project's tool: uv by default, venv + pip, or Poetry; Python version floors;
- `rfbrowser init`, the Appium server and drivers, PlatynUI pre-releases;
- a new Robot Framework project or CI setup;
- `ModuleNotFoundError` / No module named '...', `robot: command not found` after installing, externally-managed-environment, a wrong interpreter.

Not this skill: when the user asks for a test to be written or fixed, use the library skills (`rf-browser`, `rf-selenium`, `rf-requests`, ...), even if the library is not installed yet.

## Quick Reference

Install Robot Framework **into the project's own environment**, never into the system Python, and verify it before writing tests. Every other rf-agentskills skill assumes this setup works.

Recipes verified on 2026-09-26 with uv 0.9.26, Poetry 2.4.1, pip 26, Python 3.12, Robot Framework 7.5.

## Step 1: Use the tool the project already uses

Look at the project root before installing anything:

| You find | Tool | Reference |
|---|---|---|
| `uv.lock` (or `[tool.uv]` / `[dependency-groups]` with a uv workflow) | **uv** | `references/uv.md` |
| `poetry.lock` or `[tool.poetry]` in `pyproject.toml` | **Poetry** | `references/poetry.md` |
| `requirements*.txt`, or an existing `.venv/` without a lockfile | **venv + pip** | `references/venv-pip.md` |
| Nothing (new project) | **uv** (default) | `references/uv.md` |

Don't switch a project to another tool unless the user asks. Converting `requirements.txt` to uv is shown in `references/uv.md`.

## Step 2: Pick the Python version

**Recommend Python 3.12.** It satisfies every library covered by rf-agentskills. Floors checked on PyPI on 2026-09-26:

| Package | Python |
|---|---|
| robotframework 7.5 | ≥ 3.8 |
| robotframework-browser 20.x, robotframework-seleniumlibrary 6.9, robotcode 2.8, robotframework-robocop 9.x | ≥ 3.10 |
| RESTinstance 1.8 | ≥ 3.11 |
| robotframework-PlatynUI (new_core pre-release) | ≥ 3.12 |

On Debian/Ubuntu, `python3.12 -m venv` needs the `python3.12-venv` package. uv avoids this by installing its own Python (`uv python install 3.12`).

## Step 3: Install (new project with uv)

```bash
uv init --bare --python 3.12          # pyproject.toml only; --python avoids requires-python >= newest
uv python pin 3.12                    # writes .python-version; without it uv may pick a newer Python
uv add robotframework robotframework-requests          # test libraries
uv add --dev "robotcode[all]>=2.8"    # required: robotcode CLI (+ Robocop), see below
uv run robot --version                # "Robot Framework 7.5 (Python 3.12…)"; exit code 251 is normal here
uv run robotcode --version            # "robotcode, version 2.8.…"
```

Commit `pyproject.toml`, `uv.lock` and `.python-version`. On another machine or in CI: `uv sync --locked`.

venv + pip and Poetry equivalents: `references/venv-pip.md`, `references/poetry.md`.

## Required: robotcode in the project environment

The other rf-agentskills skills and the validation hooks run the robotcode CLI (`robotcode doc`, `robotcode analyze code`, `robotcode results`, `robotcode robot-debug`). Install it in every new or repaired setup, right after Robot Framework, with the tool the project uses:

| Tool | Command |
|---|---|
| uv | `uv add --dev "robotcode[all]>=2.8"` |
| Poetry | `poetry add --group dev "robotcode[all]>=2.8"` |
| venv + pip | `pip install "robotcode[all]>=2.8"` (venv active; also add it to `requirements-dev.txt`) |

- **Why `[all]`:** the base `robotcode` package only has `config` and `profiles`. The skills need the `runner` extra (`robot`, `discover`, `results`, `libdoc`), `analyze` (`analyze code`) and `repl` (`doc`, `repl`, `robot-debug`), and the hooks need Robocop. Only `[all]` brings all of them.
- **Why ≥ 2.8:** `robotcode doc` (keyword lookup) first ships in 2.8. For an older install, run the same command again: it raises the lower bound and upgrades robotcode.
- **CI that only runs tests** can install `robotcode[runner]` instead.
- Verify with `uv run robotcode --version` and `uv run robotcode discover info` (the Python and Robot Framework it reports must be the project's).
- For how to drive robotcode (running, discovery, keyword docs, results, debugging), install the robotcode plugin from `robotcodedev/robotframework-agent-plugins` next to rf-agentskills.

## Step 4: Add libraries and their post-install steps

| Library | Install (uv form) | Extra step | Usage skill |
|---|---|---|---|
| Browser (Playwright) | `uv add "robotframework-browser[bb]"` | `uv run rfbrowser install chromium` (no Node.js needed) | `rf-browser` |
| Browser with Node.js | `uv add robotframework-browser` | Node 22/24/26 LTS, then `uv run rfbrowser init chromium` | `rf-browser` |
| SeleniumLibrary | `uv add robotframework-seleniumlibrary` | A browser installed; Selenium Manager fetches the driver | `rf-selenium` |
| AppiumLibrary | `uv add robotframework-appiumlibrary` | `npm i -g appium` + `appium driver install uiautomator2` / `xcuitest` | `rf-appium` |
| RequestsLibrary | `uv add robotframework-requests` | — | `rf-requests` |
| RESTinstance | `uv add RESTinstance` | Python ≥ 3.11 | `rf-restinstance` |
| PlatynUI (preview) | `uv add --prerelease allow robotframework-PlatynUI` | Python ≥ 3.12; a plain install gets the old 0.9.2 | `rf-platynui` |

Details, pip/Poetry forms and verification per library: `references/libraries.md`.

## ⚠️ Never install test libraries globally

- No `sudo pip install`, no `pip install --break-system-packages`, no `pip install --user` for project dependencies.
- **Don't use `pipx`, `uvx` or `uv tool` for test libraries or robotcode.** Those create isolated environments that `robot` in the project can't import from. They are only for standalone CLIs such as `rf-agentskills` (see `references/cli-tools.md`).
- Run tools through the project environment: `uv run …`, `poetry run …`, or `.venv/bin/python -m …` / an activated venv.

## Step 5: Verify before handing over

```bash
uv run robot --version                           # right interpreter? (poetry run … / .venv/bin/python -m robot …)
uv run robotcode discover info                   # Python, RF and robotcode actually used
uv run robot --outputdir results tests/smoke.robot           # smoke test (assets/examples/smoke.robot)
uv run robotcode analyze code tests                          # all suites parse, imports and keywords resolve
```

`robotcode analyze code` catches missing libraries, misspelled keywords and wrong arguments without running anything, and it reads `robot.toml`. Report the versions from `robotcode discover info` to the user.

## Project layout

```text
my-tests/
  pyproject.toml   uv.lock   .python-version     # or poetry.lock / requirements.txt
  robot.toml                                      # shared robot options + profiles
  tests/           resources/        libraries/   variables/
  results/                                        # output (gitignored)
```

Details and example files: `references/project-layout.md`, `assets/examples/`.

## When to Load Additional References

| Need | Reference File |
|------|----------------|
| uv: init, pin, add, lock, sync, upgrade, adopt requirements.txt | `references/uv.md` |
| venv + pip: create, activate (bash/PowerShell/cmd), requirements, pin | `references/venv-pip.md` |
| Poetry: non-package mode, groups, run, install from lock | `references/poetry.md` |
| Standalone CLIs with `uv tool` / `uvx` / `pipx` | `references/cli-tools.md` |
| Per-library install, post-install and verification | `references/libraries.md` |
| Folder structure, `robot.toml`, `.gitignore` | `references/project-layout.md` |
| GitHub Actions and other CI | `references/ci.md` |
| Errors: wrong interpreter, PEP 668, `rfbrowser` not found, old Python, PowerShell policy | `references/troubleshooting.md` |

Examples in `assets/examples/`: `pyproject.uv.toml`, `pyproject.poetry.toml`, `requirements.txt`, `robot.toml`, `gitignore.txt`, `smoke.robot`, `github-actions-robot.yml`.

## Companion Skills

| Need | Skill |
|------|-------|
| Web UI tests with Browser Library (Playwright) | `rf-browser` |
| Web UI tests with SeleniumLibrary (WebDriver) | `rf-selenium` |
| Mobile app tests with AppiumLibrary | `rf-appium` |
| API tests with RequestsLibrary | `rf-requests` |
| API tests with RESTinstance / JSON Schema | `rf-restinstance` |
| Native desktop tests with PlatynUI | `rf-platynui` |
| Write tests, suites, user keywords, resources and variables in Robot Framework syntax | `rf-language` |
| Write or fix a Python keyword library or listener | `rf-python-library` |

For running, discovering, keyword documentation, result analysis and debugging with the robotcode CLI, use the `robotcode` skill of the robotcode plugin (`robotcode@robotframework-agent-plugins`).
