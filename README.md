# Robot Framework Agent Skills

AI agent skills for Robot Framework test automation, distributed for **eight coding agents**: Claude Code, GitHub Copilot CLI, GitHub Copilot in VS Code, OpenAI Codex, Cursor, OpenCode, Project Goose, Claude Desktop. Includes skills for the Robot Framework language (tests, keywords, resources, variables), web testing (Browser/Selenium), API testing (Requests/RESTinstance), mobile testing (Appium), native desktop testing (PlatynUI, preview), environment setup, and RF analysis tools — plus 4 specialised subagents, and 4 hooks.

## Install

There are two ways to install, and both work at **user scope** (every project on your machine) or **project scope** (one repository, shared with your team):

- **Plugin marketplace**: Claude Code, GitHub Copilot CLI, VS Code (Copilot), OpenAI Codex and Cursor all read this repository's `.claude-plugin/marketplace.json`. Add the marketplace `manykarim/robotframework-agentskills` and install the plugin `rf-agentskills`. Updates arrive through the agent.
- **Python installer** (`rf-agentskills`): copies the files into each agent's own folders. Use it for OpenCode, Goose and Claude Desktop, which have no plugin marketplace, or wherever you prefer plain files. It can also write the marketplace settings for you (`--mode plugin`).

### Plugin marketplace, per agent

| Agent (verified version) | Skills | Subagents | Hooks | Project scope (committed file) |
|---|---|---|---|---|
| **Claude Code** | yes | yes | yes | `.claude/settings.json` enables the plugin |
| **Copilot CLI** (1.0.91) | yes | yes | yes; only validation errors reach the model (see below) | `.claude/settings.json` or `.github/copilot/settings.json` loads the plugin, no install step |
| **VS Code Copilot** (1.138) | yes | yes | yes, with `chat.useHooks` | `.claude/settings.json` recommends the plugin to the workspace |
| **Codex** (0.153.4, 0.161.0) | yes | from the installer | yes, after trusting them once with `/hooks` | none: each user runs the two `codex plugin` commands |
| **Cursor** (CLI 2026.10.01, verified from its plugin loader, not run live) | yes | yes | yes (Cursor converts them) | imports the plugin from Claude Code's `.claude/settings.json` |

The plugin does not set a default main agent. The four subagents are available for delegation, and you can still choose one as your main agent yourself.

**Project scope for your team.** Commit this `.claude/settings.json` (or let `rf-agentskills install --mode plugin` merge it into the existing file):

```json
{
  "extraKnownMarketplaces": {
    "robotframework-agentskills": {
      "source": { "source": "github", "repo": "manykarim/robotframework-agentskills", "ref": "v2.1.0" }
    }
  },
  "enabledPlugins": {
    "rf-agentskills@robotframework-agentskills": true
  }
}
```

Leave out `ref` to follow `main`, or use `stable` for the latest release. Each content release is tagged `v<version>`, and a tag always installs exactly that version.

#### Claude Code

```bash
claude plugin marketplace add manykarim/robotframework-agentskills       # pin: ...agentskills#v2.1.0
claude plugin install rf-agentskills@robotframework-agentskills          # --scope user (default) | project | local
```

In a session, `/plugin marketplace add …` and `/plugin install …` do the same. `--scope project` writes the committed `.claude/settings.json` above. To try the in-tree plugin without a marketplace: `claude --plugin-dir ./plugins/rf-agentskills`.

#### GitHub Copilot CLI

```bash
copilot plugin marketplace add manykarim/robotframework-agentskills
copilot plugin install rf-agentskills@robotframework-agentskills
```

That is user scope. For project scope, commit `.claude/settings.json` (or `.github/copilot/settings.json` with the same keys): Copilot CLI loads the plugin in that repository without an install step. Pin a release with its `ref` there.

Copilot CLI passes only a hook's `decision`/`reason` to the model. So the model sees Robot Framework **validation errors** after an edit ("The edit was applied, but …"), but not the advisory context the other agents get: deprecation and formatting warnings, the skill hint on prompts, error hints after `robot` runs, and the session environment report.

#### VS Code (GitHub Copilot)

Plugins and hooks are preview features. In your **user** settings, enable them and add the marketplace:

```json
{
  "chat.plugins.enabled": true,
  "chat.useHooks": true,
  "chat.plugins.marketplaces": ["manykarim/robotframework-agentskills"]
}
```

Pin with `"manykarim/robotframework-agentskills#v2.1.0"`. Then install `rf-agentskills` from that marketplace in the Extensions view. For project scope, the committed `.claude/settings.json` recommends the plugin to everyone who opens the workspace (`chat.plugins.marketplaces` itself is a user-only setting). VS Code asks before running hook commands unless your chat approval mode allows them.

#### OpenAI Codex

```bash
codex plugin marketplace add manykarim/robotframework-agentskills        # pin: --ref v2.1.0
codex plugin add rf-agentskills@robotframework-agentskills
```

Then, once, run `/hooks` in a Codex session and trust the plugin's hooks; Codex runs none of them before that. Codex plugins cannot ship subagents, so install the four TOML subagents with the installer:

```bash
uvx rf-agentskills install --agent codex --mode plugin            # writes .codex/agents/*.toml, prints the two commands
uvx rf-agentskills install --agent codex --mode plugin --yes      # also runs them
```

Codex has no committed project-scope plugin file: every user runs the two `codex plugin` commands once. The subagents can be committed in `.codex/agents/`.

#### Cursor

Add the marketplace by its git URL, `https://github.com/manykarim/robotframework-agentskills` (Customize → Plugins, or `cursor-agent plugin marketplace add …`), install `rf-agentskills` and choose project or user scope. Cursor keeps marketplaces on your Cursor account. It also imports the plugin when it is installed in Claude Code or enabled in `.claude/settings.json` (Settings → Third-Party Imports).

### Python installer (`rf-agentskills`)

Run it with zero install and let it walk you through the agents to set up:

```bash
# Zero-install: bare `install` is interactive — multi-select of known agents,
# with the ones detected on your machine pre-checked.
uvx rf-agentskills install            # or: pipx run rf-agentskills install

# See what's detected first
uvx rf-agentskills targets
```

Fully scriptable too — no prompt with an explicit selection, `--yes`, or a non-TTY stdin:

```bash
rf-agentskills install --agents all                 # every known agent
rf-agentskills install --agents claude-code,cursor  # explicit list
rf-agentskills install --agents detected --yes      # only detected, headless
rf-agentskills install --agent claude-code          # single (back-compat)
rf-agentskills install --agent claude-code --mode plugin --ref v2.1.0   # marketplace settings instead of files
```

Installs default to **project scope** (into the current directory, e.g. `./.claude/`); add `--scope user` for a global install under your home directory. Other commands: `uninstall`, `list`, `doctor`, `version`. Useful flags: `--scope project|user [--project DIR]`, `--mode files|plugin [--ref TAG]`, `--prefix DIR`, `--dry-run`, `--what skills,agents,hooks`, `--force`, `--no-input`.

`--mode plugin` writes the marketplace entries into `.claude/settings.json` (Claude Code, Copilot, VS Code; Copilot also gets `.github/copilot/settings.json`, or `~/.copilot/settings.json` for user scope), installs the Codex subagents and prints the Codex commands, and prints the Cursor steps. Agents without a marketplace (OpenCode, Goose, Claude Desktop) fall back to files.

A manifest (per-project under `<project>/.rf-agentskills/`, or global for user scope) tracks every file written (hash + transform); `uninstall` removes only files whose hash still matches and only the hook config entries it added — user edits and other tools' hooks are preserved. Re-running `install` after an upgrade removes files the previous install wrote that the new bundle no longer ships (same hash check; user-modified files are kept), including the `rf-tools` MCP server entry and files that installers before content 2.0.0 registered.

| Agent | What lands where (files mode) | Coverage |
|---|---|---|
| **Claude Code** ≥ 2.1 | `~/.claude/skills`, `~/.claude/agents`, `settings.json` hooks | full native |
| **GitHub Copilot** (VS Code ≥ 1.108) | reuses Claude Code paths (Copilot reads them natively) | full native |
| **OpenAI Codex** | `~/.agents/skills` per docs, `~/.codex/agents/*.toml`, `hooks.json` | full (hooks experimental, opt-in via `[features] codex_hooks=true`) |
| **Cursor** ≥ 2.4 | `~/.cursor/skills`, `~/.cursor/agents`, `hooks.json` (namespaced matchers) | full native |
| **OpenCode** | `.opencode/skills`, `.opencode/agents` (`mode: subagent`), `.opencode/plugins/rf-agentskills.js` + hook scripts (or `~/.config/opencode/…`) | skills, subagents; edit validation, error hints and the environment report through the JS plugin (prompt context and the Stop reminder are not ported) |
| **Project Goose** ≥ 1.25 | `~/.agents/skills` (Summon), `.goosehints` persona | skills; subagents folded into hints; hooks N/A |
| **Claude Desktop** | one upload-ready `rf-*.zip` per skill in `~/rf-agentskills-claude-desktop/` | skills via upload (Customize → Skills → Upload a skill; needs code execution); no subagents/hooks |

Release notes, sha256 hashes, and the latest wheel + sdist are on the **[rf-agentskills releases](https://github.com/manykarim/robotframework-agentskills/releases)** page (tag prefix `rf-agentskills-v*`) and on [PyPI](https://pypi.org/project/rf-agentskills/).

### Manual: drop skill files into your project

Each skill is a self-contained folder under `skills/`. Copy what you need:

```bash
cp -r skills/rf-browser <your-project>/.claude/skills/
```

This works for any agent that reads SKILL.md files from a project-local directory (Claude Code, Codex via `.codex/skills/`, Copilot via `.github/skills/`, Cursor via `.cursor/skills/`, etc.).

## Versioning

This repo ships two release scopes — see **[`RELEASING.md`](RELEASING.md)** for the policy:

- **Content** (the marketplace plugin / skills tarballs) — currently `v2.0.0`, tagged `v*`; a tag is the ref you pin a marketplace to.
- **Tooling** (`rf-agentskills` Python installer) — currently `0.7.0`, tagged `rf-agentskills-v*`.

The two channels are versioned independently. `rf-agentskills version` prints both:

```console
$ rf-agentskills version
rf-agentskills 0.7.0
bundled content: 2.0.0  (from rf-agentskills plugin manifest)
```

## What You Get

### 11 Skills

| Skill | Type | Command | Description |
|-------|------|---------|-------------|
| Browser Library | library-reference | `/rf-agentskills:rf-browser` | Web UI tests with Browser Library (Playwright); the default when no web library is chosen yet |
| SeleniumLibrary | library-reference | `/rf-agentskills:rf-selenium` | Web UI tests with SeleniumLibrary (WebDriver, Selenium Grid) for suites that import `SeleniumLibrary` |
| AppiumLibrary | library-reference | `/rf-agentskills:rf-appium` | Mobile app tests (Android/iOS native, hybrid, mobile web) with AppiumLibrary |
| RequestsLibrary | library-reference | `/rf-agentskills:rf-requests` | HTTP/REST API tests with RequestsLibrary; the default when no API library is named |
| RESTinstance | library-reference | `/rf-agentskills:rf-restinstance` | REST API tests with RESTinstance (`Library    REST`): JSON Schema / OpenAPI-driven assertions |
| PlatynUI (preview) | library-reference | `/rf-agentskills:rf-platynui` | Native desktop UI testing (Windows UIA, Linux AT-SPI2) via PlatynUI.BareMetal |
| robotcode CLI | cli-reference | `/rf-agentskills:rf-robotcode` | Discover, run, debug and statically check with the `robotcode` CLI (`robot.toml` profiles, `robot-debug`, REPL); also keyword docs and results when robotcode is installed |
| Robot Framework language | language-guide + script | `/rf-agentskills:rf-language` | Write and review tests (keyword-driven, data-driven, BDD), suites, `__init__.robot`, tags, user keywords, `.resource` and variable files in modern, version-gated syntax; `rf_conventions` script detects the project's conventions (requires robotframework). Not for Python keyword libraries |
| Python keyword libraries | library-guide + script | `/rf-agentskills:rf-python-library` | Write and fix keyword libraries and listeners in Python: `@library`/`@keyword`, scope by state lifetime (TEST/SUITE/GLOBAL), type-hint conversion and custom converters, failures and logging, dynamic/hybrid APIs, listener API v3, libdoc; `check_library` script finds "contains no keywords", leaked imports, lost signatures and state kept in `TEST` scope before tests run (requires robotframework, Python 3.10+) |
| Setup | setup-guide | `/rf-agentskills:rf-setup` | Install Robot Framework and libraries with uv, venv + pip or Poetry; fix environment errors (`ModuleNotFoundError`, wrong interpreter); project layout, CI |
| Libdoc | script-based | `/rf-agentskills:rf-libdoc` | Look up keyword names, arguments and docs; use `rf-robotcode` instead when robotcode is installed (requires robotframework) |
| Results | script-based | `/rf-agentskills:rf-results` | Analyze output.xml results (failures, summaries, merges); use `rf-robotcode` instead when robotcode is installed (requires robotframework) |

#### Renamed in 2.0

Every skill now has one identifier, `rf-<topic>`, used as its folder name and its `name` in every channel (agentskills.io requires the two to match). In Claude Code the plugin skills are invoked as `/rf-agentskills:rf-browser` instead of `/rf-agentskills:browser`; description-based auto-loading is unaffected. `rf-agentskills install` migrates earlier installs automatically (old folders it installed are removed; files you edited are kept and reported). Folders you copied by hand are not touched — `rf-agentskills doctor` lists them so you can delete them.

| Before 2.0: repo `skills/` folder | Before 2.0: plugin / installer folder and command | Now (everywhere) |
|---|---|---|
| `robotframework-browser-skill` | `browser`, `/rf-agentskills:browser` | `rf-browser` |
| `robotframework-selenium-skill` | `selenium`, `/rf-agentskills:selenium` | `rf-selenium` |
| `robotframework-appium-skill` | `appium`, `/rf-agentskills:appium` | `rf-appium` |
| `robotframework-requests-skill` | `requests`, `/rf-agentskills:requests` | `rf-requests` |
| `robotframework-restinstance-skill` | `restinstance`, `/rf-agentskills:restinstance` | `rf-restinstance` |
| `robotframework-platynui-skill` | `platynui`, `/rf-agentskills:platynui` | `rf-platynui` |
| `robotframework-robotcode-skill` | `robotcode`, `/rf-agentskills:robotcode` | `rf-robotcode` |
| `robotframework-setup-skill` | `setup`, `/rf-agentskills:setup` | `rf-setup` |
| `robotframework-results` | `results`, `/rf-agentskills:results` | `rf-results` |
| `robotframework-libdoc-search`, `robotframework-libdoc-explain` | `libdoc-search`, `libdoc-explain` | `rf-libdoc` (merged) |

The library-reference skills provide documentation and usage guidance. The robotcode CLI skill guides agents through the `robotcode` command line and is preferred over the libdoc and results scripts when `robotcode` is installed. The 2 script-based skills execute Python scripts to look up keywords or analyze results. Each skill ships its script in its own `scripts/` folder, and the documented command runs it in the project environment: `uv run python scripts/<name>.py …` (the Claude Code plugin copy uses `"${CLAUDE_SKILL_DIR}/scripts/<name>.py"`, and the installer writes absolute paths for agents that do not expand that variable). The scripts use fixed exit codes (0 ok, 1 internal, 2 usage, 3 Robot Framework missing or < 7, 4 input not loadable) and print `error:`/`hint:` lines on stderr. Library-reference skills cross-reference their companion skills (e.g., the Browser skill suggests Libdoc and Setup). Agents write keywords, test cases and resource files directly and verify them with libdoc and `robot --dryrun`; the validation hooks check every written `.robot`/`.resource` file.

### 4 Specialized Agents

| Agent | Purpose |
|-------|---------|
| RF Test Architect | Plan test suites, select libraries, design project structure |
| RF Debug Expert | Diagnose test failures, analyze output.xml, fix flaky tests |
| RF Keyword Consultant | Find, explain, and compare keywords across libraries |
| RF Migration Guide | Upgrade RF versions, migrate between libraries |

### Automated Hooks

- **Post-save validation**: Validates every written `.robot`/`.resource` file with Robocop (project environment first): syntax errors are fed back to the agent; deprecated syntax (`[Return]`, `Run Keyword If`, `Force Tags`, …) is reported as a **non-blocking warning** (`RF_AGENTSKILLS_DEPRECATION_CHECK=warn|off`); an opt-in per-file dry run (`RF_AGENTSKILLS_FILE_DRYRUN=1`). See `plugins/rf-agentskills/hooks/README.md`.
- **Skill routing**: Routes RF-related prompts to the appropriate skill (short routing text, ≤ 450 characters)
- **Environment check**: Checks for installed RF packages and Robocop at session start (install advice via rf-setup)
- **Test reminder**: Reminds you to run tests when the session ends

## Prerequisites

- **Claude Code** 1.0.33 or later
- **Python 3.8+** (for the tool scripts)
- **robotframework** Python package (required for the libdoc and results skills)
- New to Robot Framework setup? The `setup` skill (`rf-setup`) walks an agent through installing it into a project environment (uv preferred; it also covers venv + pip and Poetry).

```bash
uv add robotframework        # pip alternative (inside the project venv): pip install robotframework
```

All scripts handle a missing `robotframework` package gracefully and report how to install it.

Optional libraries (for their respective skills), installed into the project environment -- same commands as the `rf-setup` skill's library table:
```bash
uv add "robotframework-browser[bb]" && uv run rfbrowser install chromium   # Browser skill (no Node.js needed)
uv add robotframework-seleniumlibrary              # Selenium skill (Selenium Manager fetches drivers)
uv add robotframework-appiumlibrary                # Appium skill (+ npm Appium server and drivers)
uv add robotframework-requests                     # Requests skill
uv add RESTinstance                                # RESTinstance skill (Python 3.11+)
uv add --prerelease allow robotframework-PlatynUI  # PlatynUI skill (preview; Python 3.12+; a plain install gets old 0.9.2)
uv add --dev "robotcode[all]"                      # robotcode CLI skill
```

## What is an Agent Skill?

Agent Skills are modular, self-contained packages that include a `SKILL.md` file (instructions) plus optional scripts, references, and assets. AI agents load a skill when its name or description matches the user request. Skills use progressive disclosure: only metadata is loaded initially; the full skill body and references are loaded on demand.

## Project Structure

```
skills/                        # Canonical source of truth (12 skills)
├── rf-*/                      # One folder per skill; folder name == SKILL.md name
│   ├── SKILL.md               # Skill definition (loaded by agent)
│   ├── scripts/               # Python scripts (executed, not loaded)
│   └── references/            # Deep reference docs (loaded on demand)
.claude-plugin/marketplace.json  # The marketplace every plugin-capable agent reads
plugins/rf-agentskills/        # The plugin (Claude format)
├── skills/rf-*/               # Skill copies incl. their own scripts/ (synced from root)
├── scripts/                   # Hook scripts (.mjs) only
├── agents/                    # 4 agent definitions
├── hooks/                     # Session/edit hooks
└── variants/                  # Generated: Codex TOML subagents, OpenCode agents + JS plugin
tests/                         # pytest test suite
scripts/                       # Build and sync utilities
```

The root `skills/` directory is the single source of truth. The plugin copies are derived from it using `scripts/sync-skills.sh`, which also regenerates `variants/` with `scripts/build-agent-variants.py`. The `scripts/check-drift.sh` script (also run in CI) verifies that all distribution channels stay in sync, and `scripts/validate-skills.py` (also run in CI) checks every `SKILL.md` against the [agentskills.io](https://agentskills.io) frontmatter rules: the folder name equals `name`, which is `rf-<topic>` in every channel, plus `license`, `compatibility` and `metadata.version` (= `VERSION`; kept in step by `scripts/bump-version.sh`).

## Development

### Syncing Distribution Channels

After modifying any skill in `skills/`, a subagent or `hooks/hooks.json`, sync the plugin:

```bash
bash scripts/sync-skills.sh
```

### Checking for Drift

Verify all distribution channels are in sync:

```bash
bash scripts/check-drift.sh
```

This also runs in CI to prevent drift from being committed.

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test files
python -m pytest tests/test_rf_results.py -v          # requires robotframework
python -m pytest tests/test_drift_detection.py -v
python -m pytest tests/test_rf_libdoc.py -v            # requires robotframework
python -m pytest tests/test_script_execution.py -v    # script CLI contract (exit codes, --help, --json-out)
python -m pytest tests/test_skill_commands.py -v      # how SKILL.md / agents / hooks run the scripts
python -m pytest tests/test_libdoc_skill.py -v
python -m pytest tests/test_marketplace_validation.py -v
python -m pytest tests/test_skill_validation.py -v
```

### Validate the Marketplace and Skills

```bash
python scripts/validate-marketplace.py
python scripts/validate-skills.py --channel all   # root and plugin copies
```

### Bundled scripts

Skills run their Python scripts directly (`uv run python scripts/<name>.py …`, or the project's interpreter); there is no MCP server. Each script prints JSON:

| Script (skill) | Purpose |
|----------------|---------|
| `rf_libdoc.py` (rf-libdoc) | Search keywords across RF libraries and explain one keyword's arguments |
| `rf_results.py` (rf-results) | Summarise, merge and time `output.xml` results |
| `rf_conventions.py` (rf-language) | Report a project's Robot Framework conventions and version |
| `check_library.py` (rf-python-library) | Check the project's own Python keyword libraries: keywords, scope, API style and defect findings (runs in a subprocess, never imports user code into the agent) |

### Claude Desktop and claude.ai

Claude Desktop loads custom skills uploaded as ZIP files, not from disk. `rf-agentskills install --agent claude-desktop` writes one archive per skill to `~/rf-agentskills-claude-desktop/` (the CI and release artifacts contain the same archives). Upload each under **Customize → Skills → + → Create skill → Upload a skill** and start a new chat; code execution must be enabled. Build them from a checkout with `python scripts/build-skill-zips.py --out dist/skill-zips`.

### Test the Plugin Locally

```bash
claude --plugin-dir ./plugins/rf-agentskills
```

## Compatibility

- **Robot Framework** 7+ (uses modern syntax: RETURN, IF/ELSE, TRY/EXCEPT)
- **Python** 3.10+ for the `rf-agentskills` installer; 3.8+ for running the skill scripts themselves
- **Coding agents** (see the install matrices above): Claude Code ≥ 2.1, GitHub Copilot CLI (plugin verified with 1.0.91), GitHub Copilot in VS Code ≥ 1.108 (plugin verified with 1.138), OpenAI Codex (plugin verified with 0.153.4 and 0.161.0), Cursor ≥ 2.4 (plugin loader checked in CLI 2026.10.01), OpenCode, Project Goose ≥ 1.25, Claude Desktop (skills via ZIP upload)

Anthropic's SKILL.md format is an open standard supported by all eight agents listed above (Claude Code, Copilot, Codex, Cursor, OpenCode, and Goose all read it natively as of their respective recent releases). The `rf-agentskills` installer handles the path-routing per agent so you don't have to memorise where each one wants its skills.

## Running skill evaluations

This repository ships an evaluation harness (`rf-skill-eval`) that grades each
skill under controlled Claude Code sessions and produces a scorecard. See
[docs/ci/usage.md](docs/ci/usage.md) for the full walkthrough. Quick start:

```bash
cp .env.example .env      # add your CLAUDE_CODE_OAUTH_TOKEN
uv sync
uv run rfbrowser init
uv run rf-skill-eval doctor
bash scripts/eval-local.sh
```

## License

Apache-2.0
