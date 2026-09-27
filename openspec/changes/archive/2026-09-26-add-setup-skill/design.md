## Context

- Package facts, checked on PyPI 2026-09-26: robotframework 7.5 (Py ≥3.8), robotframework-browser 20.5.0 (≥3.10, extra `bb` → robotframework-browser-batteries; Node 22/24/26 LTS for the Node path), SeleniumLibrary 6.9.0 (≥3.10), AppiumLibrary 3.2.1, RequestsLibrary 0.9.7, RESTinstance 1.8.0 (≥3.11), PlatynUI new_core pre-release (≥3.12; plain install resolves the old 0.9.2), robotcode 2.7.0 (≥3.10), robocop 9.1.0 (≥3.10). Appium server 3.8.0 on npm.
- Local tools for verification: uv 0.9.26, Poetry 2.4.1, Python 3.12.3.
- House pattern, as in rf-robotcode: router SKILL.md, `references/`, `assets/examples/`, a structural test, a `SHORT_NAMES` entry and sync.
- `check_rf_environment.mjs` already lists missing packages and prints `pip install` hints. The test only asserts exit 0 and the banner on stderr.
- The rf-agentskills installer writes `python_runtime.json` so that hooks use the interpreter that has RF. This is why "install into the project env and point tools at it" matters.

## Goals / Non-Goals

**Goals:**
- An agent can take an empty folder or an existing repo to a verified, runnable RF setup using the tool the project already uses.
- Each command in the skill has been run once, with the versions named above.

**Non-Goals:**
- No installer scripts or automation; the skill contains only Markdown and example files.
- No docs on conda, hatch, pdm or rye (a one-line mention that uv/pip recipes translate at most).
- No Docker image guidance beyond pointing to the official Browser images.
- No change to the SessionStart output channel (see proposal).

## Decisions

### D1: Detect first, uv by default
SKILL.md opens with a detection table (lockfile or config → tool) and one rule: follow what the project uses, and use uv for new projects. The alternative, always converting to uv, would rewrite the user's toolchain without asking.

### D2: Recommend Python 3.12, document floors
3.12 satisfies every library that has a skill here, including PlatynUI new_core, and is widely available. The floors table has a "checked 2026-09-26" stamp. The alternative, "latest Python", fails on PlatynUI (<3.14 in current metadata) and is a moving target.

### D3: uv project style
For test projects, use `uv init --bare --python 3.12` (only a `pyproject.toml`, no sample `main.py`). Add libraries with `uv add`, dev tools (robotcode, robocop) with `uv add --dev`, run with `uv run robot`, and reproduce with `uv sync --locked`. Commit `uv.lock` and `.python-version`. The alternative, `uv pip install` into a `uv venv`, gives no lockfile, so it is shown only as a pip-compatible fallback in `venv-pip.md`.

### D4: Poetry in non-package mode
`poetry init --no-interaction`, then set `package-mode = false` (Poetry 2), `poetry add`, `poetry add --group dev`, `poetry run robot`, `poetry install` to reproduce. Test projects aren't distributable packages, and package mode fails without a package directory.

### D5: venv + pip with `requirements.txt`
`python3.12 -m venv .venv`, activation per shell, `python -m pip install -r requirements.txt`. Show `pip freeze > requirements.lock.txt` for exact pins. Always use `python -m pip` so the pip matches the venv's interpreter.

### D6: Browser defaults to `[bb]`
The no-Node path (`robotframework-browser[bb]` + `rfbrowser install`) is shown first, because it has fewer moving parts for agents. The Node path follows, for users who need Node plugins or whose platform has no batteries wheel. Both are verified in scratch. With uv, `rfbrowser` runs as `uv run rfbrowser …`.

### D7: Links, not copies
Library usage stays in the library skills. `libraries.md` only covers install and post-install. PlatynUI install details point to `rf-platynui` (a one-line warning about the version pitfall stays here). robotcode config points to `rf-robotcode`.

### D8: Example files avoid dotfiles
A real `.gitignore` inside `skills/` would affect this repo's git, so the example is named `gitignore.txt`. The CI example is `github-actions-robot.yml`, not placed under `.github/`.

### D9: Hook touches are text-only
Inject hook: add `setup` to the listed skills. SessionStart hint: prepend `See the setup skill (uv / venv + pip / poetry)` and a `uv add robotframework` line to the existing pip lines. No change to exit codes or channels, and the regex is unchanged ("install robot framework" already matches `robot framework`).

### D10: Tests check examples mechanically
`tests/test_setup_skill.py`: structure; frontmatter; references present; detection table and floors present; "no sudo pip / pipx for libraries" wording; example TOML parses (`tomllib`); `smoke.robot` passes `robot --dryrun` (robot is always installed in CI); workflow YAML parses (`pytest.importorskip("yaml")`). Recipe execution is manual during implementation (network, minutes long), not a CI test.

## Risks / Trade-offs

- [Package floors and versions drift] → a date stamp on the floors table; library skill tests catch keyword drift, and the floors are rechecked when a library skill changes.
- [BrowserBatteries is missing for some OS/arch] → the Node path is documented as the fallback, with how to spot the failure.
- [Poetry 1.x users hit `package-mode` as an unknown key] → note that it needs Poetry ≥1.8, with `poetry install --no-root` for older versions.
- [Agents install heavy browsers unnecessarily] → recommend `rfbrowser install chromium` (one browser) by default.

## Migration Plan

Additive only. Rollback is removing the skill folder, the name-map entry and the text additions, then running sync again.
