# Robot Framework Agent Skills

AI agent skills for Robot Framework test automation, distributed for **seven coding agents**: Claude Code, GitHub Copilot (VS Code), OpenAI Codex, Cursor, OpenCode, Project Goose, Claude Desktop. Includes skills for web testing (Browser/Selenium), API testing (Requests/RESTinstance), mobile testing (Appium), native desktop testing (PlatynUI, preview), asset generation, and RF analysis tools — plus 4 specialised subagents, 4 hooks, and an MCP server.

## Install

### Recommended: cross-agent Python installer (`rf-agentskills`)

A single command auto-detects every supported agent on your machine and writes the bundle into each one's documented install paths:

```bash
# Install the installer
pipx install https://github.com/manykarim/robotframework-agentskills/releases/download/rf-agentskills-v0.4.0/rf_agentskills-0.4.0-py3-none-any.whl

# Detect what's installed
rf-agentskills targets

# Install into every detected agent
rf-agentskills install --all

# Or just one
rf-agentskills install --agent claude-code
```

Other commands: `uninstall`, `list`, `doctor`, `version`. Useful flags: `--scope user|project [--project DIR]`, `--prefix DIR`, `--dry-run`, `--what skills,agents,hooks,mcp`, `--force`.

Manifest at `$XDG_DATA_HOME/rf-agentskills/installed.json` tracks every file we wrote (hash + transform); `uninstall` only removes files whose hash still matches, so any user edits are preserved.

| Agent | What lands where | Coverage |
|---|---|---|
| **Claude Code** ≥ 2.1 | `~/.claude/skills`, `~/.claude/agents`, `settings.json` hooks, `~/.mcp.json` | full native |
| **GitHub Copilot** (VS Code ≥ 1.108) | reuses Claude Code paths (Copilot reads them natively) | full native |
| **OpenAI Codex** | `~/.agents/skills` per docs, `~/.codex/agents/*.toml`, MCP in `config.toml` | full (hooks experimental, opt-in via `[features] codex_hooks=true`) |
| **Cursor** ≥ 2.4 | `~/.cursor/skills`, `~/.cursor/agents`, `mcp.json`, `hooks.json` (namespaced matchers) | full native |
| **OpenCode** | `~/.config/opencode/skills`, `agents`, `opencode.json` MCP block | full native (hooks deferred — JS-only) |
| **Project Goose** ≥ 1.25 | `~/.agents/skills` (Summon), MCP in `config.yaml`, `.goosehints` persona | skills + MCP; hooks N/A |
| **Claude Desktop** | per-OS `claude_desktop_config.json` (MCP only) | MCP only — no skill/agent loader |

Release notes, sha256 hashes, and the latest wheel + sdist are on the **[rf-agentskills releases](https://github.com/manykarim/robotframework-agentskills/releases)** page (tag prefix `rf-agentskills-v*`). PyPI publication pending.

### Alternative: Claude Code marketplace

If you prefer Claude Code's native plugin system over the cross-agent installer:

```bash
claude plugin marketplace add manykarim/robotframework-agentskills
claude plugin install rf-agentskills@robotframework-agentskills
```

Or load the in-tree plugin directly without registering a marketplace:

```bash
claude --plugin-dir ./plugins/rf-agentskills
```

### Alternative: VS Code Marketplace extension (`.vsix`)

A standalone VS Code extension ships **chat skills only** (no subagents, hooks, or MCP server — for those, use the `rf-agentskills` installer above with `--agent copilot`):

```bash
# Latest .vsix is attached to the v* GitHub release
code --install-extension robotframework-agentskills-1.2.0.vsix
```

### Manual: drop skill files into your project

Each skill is a self-contained folder under `skills/`. Copy what you need:

```bash
cp -r skills/robotframework-browser-skill <your-project>/.claude/skills/
```

This works for any agent that reads SKILL.md files from a project-local directory (Claude Code, Codex via `.codex/skills/`, Copilot via `.github/skills/`, Cursor via `.cursor/skills/`, etc.).

## Versioning

This repo ships two release scopes — see **[`RELEASING.md`](RELEASING.md)** for the policy:

- **Content** (Claude plugin / `.vsix` / skills tarballs) — currently `v1.2.0`, tagged `v*`.
- **Tooling** (`rf-agentskills` Python installer) — currently `0.4.0`, tagged `rf-agentskills-v*`.

The two channels are versioned independently. `rf-agentskills version` prints both:

```console
$ rf-agentskills version
rf-agentskills 0.4.0
bundled content: 1.2.0  (from rf-agentskills plugin manifest)
```

## What You Get

### 12 Skills

| Skill | Type | Command | Description |
|-------|------|---------|-------------|
| Browser Library | library-reference | `/rf-agentskills:browser` | Web testing with Playwright (auto-waiting, assertions, Shadow DOM) |
| SeleniumLibrary | library-reference | `/rf-agentskills:selenium` | Web testing with Selenium WebDriver |
| AppiumLibrary | library-reference | `/rf-agentskills:appium` | Mobile testing for iOS and Android |
| RequestsLibrary | library-reference | `/rf-agentskills:requests` | REST API testing with HTTP methods |
| RESTinstance | library-reference | `/rf-agentskills:restinstance` | REST API testing with JSON Schema validation |
| PlatynUI (preview) | library-reference | `/rf-agentskills:platynui` | Native desktop UI testing (Windows UIA, Linux AT-SPI2) via PlatynUI.BareMetal |
| Keyword Builder | script-based | `/rf-agentskills:keyword-builder` | Generate RF user keywords from structured input |
| Test Case Builder | script-based | `/rf-agentskills:testcase-builder` | Generate RF test cases from structured input |
| Resource Architect | script-based | `/rf-agentskills:resource-architect` | Design resource/variable file layouts |
| Libdoc Search | script-based | `/rf-agentskills:libdoc-search` | Search library keywords by use case |
| Libdoc Explain | script-based | `/rf-agentskills:libdoc-explain` | Explain keyword arguments and documentation |
| Results | script-based | `/rf-agentskills:results` | Parse output.xml into JSON summaries (requires robotframework) |

The 5 library-reference skills provide documentation and usage guidance. The 6 script-based skills execute Python scripts to generate code or analyze artifacts. Library-reference skills cross-reference their companion script-based skills (e.g., the Browser skill suggests using Keyword Builder and Libdoc Search).

### 4 Specialized Agents

| Agent | Purpose |
|-------|---------|
| RF Test Architect | Plan test suites, select libraries, design project structure |
| RF Debug Expert | Diagnose test failures, analyze output.xml, fix flaky tests |
| RF Keyword Consultant | Find, explain, and compare keywords across libraries |
| RF Migration Guide | Upgrade RF versions, migrate between libraries |

### Automated Hooks

- **Post-save validation**: Automatically validates `.robot` files after every write/edit
- **Skill routing**: Routes RF-related prompts to the appropriate skill or agent
- **Environment check**: Checks for installed RF packages at session start
- **Test reminder**: Reminds you to run tests when the session ends

## Prerequisites

- **Claude Code** 1.0.33 or later
- **Python 3.8+** (for builder and tool scripts)
- **robotframework** Python package (required for libdoc-search, libdoc-explain, and results skills)

```bash
pip install robotframework
```

All scripts handle a missing `robotframework` package gracefully -- script-based skills that do not require it (keyword-builder, testcase-builder, resource-architect) work with the Python standard library alone.

Optional libraries (for their respective skills):
```bash
pip install robotframework-browser    # Browser skill
pip install robotframework-seleniumlibrary  # Selenium skill
pip install robotframework-appiumlibrary    # Appium skill
pip install robotframework-requests   # Requests skill
pip install RESTinstance              # RESTinstance skill
pip install --pre robotframework-PlatynUI   # PlatynUI skill (preview; Python 3.12+; NOT plain install — see skill)
```

## Team Distribution

Add to your project's `.claude/settings.json` to auto-configure for your team:

```json
{
  "extraKnownMarketplaces": {
    "robotframework-agentskills": {
      "source": {
        "source": "github",
        "repo": "manykarim/robotframework-agentskills",
        "ref": "stable"
      }
    }
  },
  "enabledPlugins": {
    "rf-agentskills@robotframework-agentskills": true
  }
}
```

## What is an Agent Skill?

Agent Skills are modular, self-contained packages that include a `SKILL.md` file (instructions) plus optional scripts, references, and assets. AI agents load a skill when its name or description matches the user request. Skills use progressive disclosure: only metadata is loaded initially; the full skill body and references are loaded on demand.

## Project Structure

```
skills/                        # Canonical source of truth (12 skills)
├── robotframework-*/          # Each skill is a self-contained folder
│   ├── SKILL.md               # Skill definition (loaded by agent)
│   ├── scripts/               # Python scripts (executed, not loaded)
│   └── references/            # Deep reference docs (loaded on demand)
plugins/rf-agentskills/        # Claude Code Plugin distribution
├── skills/                    # Short-named skill copies (synced from root)
├── scripts/                   # Centralized script copies (synced from root)
├── agents/                    # 4 agent definitions
├── hooks/                     # Session/edit hooks
└── servers/                   # MCP server
vscode-extension/              # VS Code Extension distribution
├── skills/                    # Skill copies for VS Code (synced from root)
└── src/                       # Extension TypeScript source
tests/                         # pytest test suite
scripts/                       # Build and sync utilities
```

The root `skills/` directory is the single source of truth. Plugin and VS Code copies are derived from it using `scripts/sync-skills.sh`. The `scripts/check-drift.sh` script (also run in CI) verifies that all distribution channels stay in sync.

## Development

### Syncing Distribution Channels

After modifying any skill in `skills/`, sync to plugin and VS Code:

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
python -m pytest tests/test_keyword_builder.py -v
python -m pytest tests/test_testcase_builder.py -v
python -m pytest tests/test_resource_architect.py -v
python -m pytest tests/test_rf_results.py -v          # requires robotframework
python -m pytest tests/test_drift_detection.py -v
python -m pytest tests/test_libdoc_search.py -v        # requires robotframework
python -m pytest tests/test_marketplace_validation.py -v
```

### Validate the Marketplace

```bash
python scripts/validate-marketplace.py
```

### MCP Server

The plugin includes an MCP server that exposes all script-based tools:

| MCP Tool | Description |
|----------|-------------|
| `rf_libdoc_search` | Search keywords across RF libraries |
| `rf_libdoc_explain` | Explain keyword arguments in detail |
| `rf_results_analyze` | Parse output.xml into structured JSON |
| `rf_keyword_builder` | Generate RF user keywords from JSON |
| `rf_testcase_builder` | Generate RF test cases from JSON |
| `rf_resource_architect` | Design resource file layouts |

Test the MCP server:
```bash
python3 plugins/rf-agentskills/servers/rf-tools-server.py
```

### Test the Plugin Locally

```bash
claude --plugin-dir ./plugins/rf-agentskills
```

## Compatibility

- **Robot Framework** 7+ (uses modern syntax: RETURN, IF/ELSE, TRY/EXCEPT)
- **Python** 3.10+ for the `rf-agentskills` installer; 3.8+ for running the skill scripts themselves
- **Coding agents** (see install matrix above): Claude Code ≥ 2.1, GitHub Copilot in VS Code ≥ 1.108, OpenAI Codex, Cursor ≥ 2.4, OpenCode, Project Goose ≥ 1.25, Claude Desktop (MCP only)

Anthropic's SKILL.md format is an open standard supported by all seven agents listed above (Claude Code, Copilot, Codex, Cursor, OpenCode, and Goose all read it natively as of their respective recent releases). The `rf-agentskills` installer handles the path-routing per agent so you don't have to memorise where each one wants its skills.

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
