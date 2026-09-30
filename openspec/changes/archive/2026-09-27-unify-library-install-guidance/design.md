## Context

- The source of truth is `skills/robotframework-setup-skill/SKILL.md`, Step 4 table, which gives the uv install form, the extra step and the companion skill for each library. Its details are in `references/libraries.md`, which has both Browser paths, Selenium Manager with an offline escape hatch, the Appium npm server and drivers, the RESTinstance Python ≥ 3.11 floor, and the PlatynUI `--prerelease allow` install. `openspec/specs/setup-skill` pins this content.
- Current library-skill install content, found by grep on 2026-09-27:

  | Skill | Location | Content |
  |---|---|---|
  | rf-browser | `SKILL.md` L14–17 | `pip install` + `rfbrowser init` |
  | rf-browser | `references/troubleshooting.md` L426–449 | `rfbrowser init` variants, `pip uninstall/install` |
  | rf-selenium | `SKILL.md` L14–26 | `pip install`, `webdriver-manager` |
  | rf-selenium | `SKILL.md` L59–60 | `executable_path=${DRIVER_PATH}` |
  | rf-selenium | `references/webdriver-setup.md` L7–70 | "WebDriver Manager (Recommended)", `browser_setup.py`, manual driver downloads with `executable_path` |
  | rf-selenium | `references/webdriver-setup.md` L283–350 | CI with `pip install … webdriver-manager` and `setup-chromedriver` |
  | rf-selenium | `references/webdriver-setup.md` L409–430 | driver troubleshooting table with `executable_path` |
  | rf-selenium | `references/troubleshooting.md` L170–198 | ChromeDriver download, `pip install webdriver-manager` |
  | rf-appium | `SKILL.md` L12–24 | `pip install` + npm Appium server/drivers |
  | rf-requests | `SKILL.md` L14–16 | `pip install` |
  | rf-requests | `references/troubleshooting.md` L76 | `pip install --upgrade certifi` |
  | rf-restinstance | `SKILL.md` L14–16 | `pip install` |
  | rf-platynui | `SKILL.md` L14–34, L224 | `pip install` pin / `--pre` / footgun |
  | rf-platynui | `references/platform-setup.md` L7–17, L60 | install matrix and footgun in pip form |
  | rf-platynui | `references/cli-and-inspector.md` L8 | venv `pip install --pre` alternative |
  | rf-platynui | `references/status-and-migration.md` L20 | table row explaining what a plain pip install resolves to |
  | rf-platynui | `assets/examples/calculator.robot` L5 | header comment |

- `tests/test_setup_skill.py` already asserts that rf-setup has no line starting with `pip install`. `tests/test_platynui_skill.py` asserts that `--pre` or `0.12.0.dev` appears in the skill.

## Goals / Non-Goals

**Goals:**
- One install story across all skills. Library skills restate only what an agent needs inline to avoid a round trip: the `uv add` line and the one post-install step.
- A cheap, deterministic regression test.

**Non-Goals:**
- Changing rf-setup content or the setup-skill spec.
- Restructuring the library skills (decision tables, gotchas, reference pruning). That belongs to `restructure-library-skills`.
- Hook install hints (`check_rf_environment.mjs`), which the setup-skill change already covered.
- Eval fixtures and eval task text.

## Decisions

### D1: Standard installation block
Every library SKILL.md uses the same shape, so the test and the agents can rely on it:

````markdown
## Installation

Install into the project environment (see **rf-setup** for uv/venv/Poetry, CI and troubleshooting):

```bash
uv add robotframework-requests
```
<one line: library-specific post-install essential, or "No post-install step.">
````

The Browser block has a second fenced block for the Node escape hatch, headed "Only if no BrowserBatteries wheel exists for your platform, or you need Node plugins". The Appium block keeps its three npm lines (`npm install -g appium`, `appium driver install uiautomator2`, `appium driver install xcuitest`), because the Appium server lives outside the Python environment and every Appium session needs it. The alternative, a pointer only with no install line, was rejected: agents would have to load a second skill for a one-line command, and the Step 4 table already exists to be quoted.

### D2: The uv line is copied verbatim from rf-setup and tested
The test parses rf-setup's Step 4 table (library → install cell) and asserts that each library SKILL.md contains the same backtick command. When rf-setup changes a command, the library skills must follow, and the test enforces this. A shared include or template was rejected: SKILL.md files are static Markdown read by agents, and there is no include mechanism across the three distribution channels.

### D3: How the pip-alternative label works
A `pip install` / `pip3 install` occurrence is allowed only when the same line contains `pip alternative` or `# pip:` (case-insensitive). This keeps the PlatynUI footgun explainable, for example `uv add --prerelease allow robotframework-PlatynUI   # pip: pip install --pre robotframework-PlatynUI`, which is the style rf-setup's `libraries.md` already uses. It also makes every exception visible in review. The `status-and-migration.md` table row gets rewritten to name the resolution behaviour ("unpinned install without pre-release opt-in → 0.9.2") and not a pip command. A per-file allowlist was rejected because the label is local and self-documenting.

### D4: Scope of the scan
The scan covers all text files under the six library skill dirs (`SKILL.md`, `references/**`, `assets/**`) in root `skills/`. The same test is parametrized over `plugins/rf-agentskills/skills/{browser,selenium,appium,requests,restinstance,platynui}` so the synced copies are guarded too. Patterns:
- `\bpip3? install\b`
- `webdriver[-_]manager`
- `executable_path\s*=` (rf-selenium only)
- `rfbrowser init` in rf-browser, allowed only inside the labelled Node escape hatch: the line or the fenced block's preceding heading/sentence must contain "Node"

`uv tool install` never matches `\bpip3? install\b`.

### D5: Selenium content after removal
`references/webdriver-setup.md` loses its "WebDriver Manager (Recommended)" and "Manual WebDriver Setup" sections. They are replaced by a short "Drivers: Selenium Manager" section with three points:
- a browser must be installed
- the driver is fetched on first `Open Browser`, cached in `~/.cache/selenium`, and `SE_CACHE_PATH` overrides the location
- offline or locked-down machines: see rf-setup `references/libraries.md`

The CI examples become one GitHub Actions example that uses `astral-sh/setup-uv` + `uv sync --locked` + `uv run robot` and drops `setup-chromedriver`. The GitLab and Jenkins examples keep the Grid variants, with `uv sync --locked` as the install line. The troubleshooting "driver version mismatch" entry now says: clear the Selenium Manager cache or upgrade selenium through the project env. This is still consistent with rf-setup, which allows `executable_path` offline. The escape hatch lives only there.

### D6: Where this check lives
The check lives in a pytest (`tests/test_library_install_guidance.py`) and not in the keyword checker of `fix-library-skill-keyword-correctness`. It is pure text matching, it needs no libraries, and it runs in the existing CI `test` job on every OS and Python version in the matrix. The two changes stay independent.

## Risks / Trade-offs

- [The uv line drifts from rf-setup when rf-setup is edited] → D2's test fails and names the mismatch.
- [Users on pip or Poetry feel ignored] → Each block's first sentence points to rf-setup, which has full venv + pip and Poetry recipes. rf-setup's detection rule (follow the project's existing tool) is referenced in the pointer sentence.
- [Removing `executable_path` leaves offline users without guidance in rf-selenium] → The pointer to rf-setup's offline note is explicit in the Selenium Manager section.
- [`restructure-library-skills` later rewrites these SKILL.md files] → That change's skeleton includes an "Import and one recommended configuration" section. Its tasks should carry this change's install block forward unchanged, and the test from this change guards it.

## Migration Plan

Content-only change plus one test. Land it in one PR: edit root skills, run the sync, run the tests. Rollback: revert the PR.

## Implementation Notes

- Adapted after `fix-library-skill-keyword-correctness` landed: that change added `scripts/check-skill-keywords.py` with one allowlist entry (selenium `references/webdriver-setup.md` `Get Chrome Driver`). Removing the webdriver-manager section makes it stale, so task 2.4.1 deletes it. The keyword checker (`--require-all`, root and plugin copies) is part of verification.
- The Context grep missed `references/keywords-reference.md` L10 in rf-selenium (`executable_path=None` in the `Open Browser` signature). The spec forbids any `executable_path=` in rf-selenium, so task 2.4.2 drops the argument from the documented signature and mentions it in prose (without `=`) as an offline-only option deferred to rf-setup.
- Test commands: `uv run pytest -q` only runs `tests/eval` (pyproject testpaths); the new test runs via `uv run pytest -q tests/ --ignore=tests/eval`, which is what CI's `test` job runs. No CI change needed.
- `sync-skills.sh` rewrites backticked skill names in plugin SKILL.md (`` `rf-setup` `` → `` `setup` ``), so the companion-section check expects `` `setup` `` for plugin copies. The Installation pointer uses bold `**rf-setup**` (not backticked), so it survives the sync unchanged.
- rf-browser troubleshooting keeps `rfbrowser init` only in a "Node.js path" subsection (Node-labelled context before the fence satisfies check (f)). `--skip-browsers` exists only on `rfbrowser init` (verified with `rfbrowser install --help`), so it lives in that Node subsection; the `[bb]` path documents `--with-deps` instead.
- rf-selenium CI: GitHub Actions uses `astral-sh/setup-uv@v6` + `browser-actions/setup-chrome@v1` + `uv sync --locked`; GitLab uses the `ghcr.io/astral-sh/uv:python3.12-bookworm` image. Pointer to rf-setup `references/ci.md` added.
- README: the `pip install robotframework` line became `uv add robotframework` with a labelled pip alternative; the optional-libraries block copies rf-setup's Step 4 commands.
