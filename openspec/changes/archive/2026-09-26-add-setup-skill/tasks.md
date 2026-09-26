## 1. Verify the recipes in scratch projects

- [x] 1.1 uv recipe: in an empty scratch dir run `uv init --bare --python 3.12`, `uv add robotframework robotframework-requests`, `uv add --dev robotcode[all] robotframework-robocop`, `uv run robot --version`, `uv run robot` on the smoke test, `uv sync --locked` in a fresh clone copy. Verify: every command exits as expected; notes record the output
- [x] 1.2 venv + pip recipe: `python3.12 -m venv .venv`, `.venv/bin/python -m pip install -r requirements.txt`, smoke test, `pip freeze` lock. Verify: smoke test passes with the venv interpreter
- [x] 1.3 Poetry recipe: `poetry init --no-interaction`, `package-mode = false`, `poetry add`, `poetry add --group dev`, `poetry run robot`, `poetry install` from the lock. Verify: smoke test passes via `poetry run`
- [x] 1.4 Browser paths: `uv add "robotframework-browser[bb]"` + `uv run rfbrowser install chromium`, and the Node path `robotframework-browser` + `uv run rfbrowser init chromium`; run a one-line Browser smoke. Verify: both paths reach a passing `New Page` run, or the limitation is recorded

## 2. Skill content

- [x] 2.1 Create `skills/robotframework-setup-skill/SKILL.md` (`name: rf-setup`): when to use, detection table, Python floors + 3.12 recommendation with date, uv quick start, library add-on table with companion skills, verification steps, the rule against system-wide installs, reference index, companion skills. Verify: ≤ 200 lines and all linked paths exist
- [x] 2.2 Write `references/uv.md` from 1.1 (init, python pin, add/dev groups, lock/sync, run, upgrade, existing-project adoption, `uv pip` fallback). Verify: commands match the 1.1 notes
- [x] 2.3 Write `references/venv-pip.md` from 1.2 (create, activate for bash/zsh/PowerShell/cmd, no-activation calls, requirements + pinned lock, upgrade). Verify: commands match the 1.2 notes
- [x] 2.4 Write `references/poetry.md` from 1.3 (non-package mode, groups, run/shell, install from lock, Poetry <1.8 note). Verify: commands match the 1.3 notes
- [x] 2.5 Write `references/cli-tools.md` (`uv tool install` / `uvx` / `pipx` for CLIs such as rf-agentskills; why libraries and robotcode belong in the project env). Verify: no library is installed via tool commands
- [x] 2.6 Write `references/libraries.md` (per library: package, Python floor, post-install, verify command, companion skill; Browser both paths from 1.4; Appium server/drivers; PlatynUI warning + link). Verify: floors match design Context
- [x] 2.7 Write `references/project-layout.md` (tree, robot.toml, gitignore, `.python-version`, where outputs go) and `references/ci.md` (GitHub Actions with uv, caching, Browser install in CI, artifacts upload). Verify: examples referenced exist in assets
- [x] 2.8 Write `references/troubleshooting.md` with symptom → cause → fix for the five required problems plus other failures seen in group 1. Verify: five required entries present
- [x] 2.9 Add `assets/examples/`: `pyproject.uv.toml`, `pyproject.poetry.toml`, `requirements.txt`, `robot.toml`, `gitignore.txt`, `smoke.robot`, `github-actions-robot.yml`. Verify: files were used in the group 1 runs (`smoke.robot`, requirements, pyprojects)

## 3. Cross-links and hooks

- [x] 3.1 Add an `rf-setup` row to the companion section of `skills/robotframework-robotcode-skill/SKILL.md`. Verify: `git diff` shows one added row
- [x] 3.2 Add `setup` to the injected skill list in `maybe_inject_rf_context.mjs`, and a setup-skill pointer + `uv add` line to the install hint in `check_rf_environment.mjs` (text only). Verify: hook tests (3.3) pass and the env check still exits 0
- [x] 3.3 Extend `tests/test_hook_scripts.py`: injected text names `setup`; env-check stderr mentions the setup skill. Verify: `uv run pytest tests/test_hook_scripts.py` passes

## 4. Tests

- [x] 4.1 Create `tests/test_setup_skill.py`: structure, frontmatter, references, detection table, floors + 3.12, no-system-install wording, companion links, TOML examples parse, `smoke.robot` passes `robot --dryrun`, workflow YAML parses (importorskip yaml). Verify: `uv run pytest tests/test_setup_skill.py` passes

## 5. Distribution and docs

- [x] 5.1 Add `["robotframework-setup-skill"]="setup"` to `SHORT_NAMES` and a `rf-setup` → `setup` rename in the plugin transform, then run sync. Verify: `plugins/rf-agentskills/skills/setup/SKILL.md` has `name: setup`; `vscode-extension/skills/rf-setup/` exists; package.json lists it
- [x] 5.2 Run `scripts/check-drift.sh` and the full test suite. Verify: no drift; `uv run pytest tests/ --ignore=tests/eval` passes
- [x] 5.3 Add the skill to the README skills table and the installer CHANGELOG "Unreleased" section; note the SessionStart stderr channel as a follow-up in the CHANGELOG. Verify: README lists `rf-setup`
