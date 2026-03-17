# Robot Framework Agent Skills for Claude Code

A Claude Code plugin marketplace providing AI agent skills for Robot Framework test automation. Includes skills for web testing (Browser/Selenium), API testing (Requests/RESTinstance), mobile testing (Appium), asset generation, and RF analysis tools.

## Quick Install

### Claude Code Plugin

```bash
# Install as Claude Code Plugin
claude plugin add github:manykarim/robotframework-agentskills

# Or install skills directly to your project
cp -r skills/robotframework-browser-skill .claude/skills/
```

### VS Code Extension

```bash
# Install from VSIX
code --install-extension vscode-extension/robotframework-agentskills-1.0.0.vsix
```

### Standalone (Without Plugin System)

```bash
# Load the plugin directory directly
claude --plugin-dir ./plugins/rf-agentskills
```

Or copy individual skills from `skills/` to your project's `.claude/skills/` for standalone usage without the plugin system.

## What You Get

### 11 Skills

| Skill | Type | Command | Description |
|-------|------|---------|-------------|
| Browser Library | library-reference | `/rf-agentskills:browser` | Web testing with Playwright (auto-waiting, assertions, Shadow DOM) |
| SeleniumLibrary | library-reference | `/rf-agentskills:selenium` | Web testing with Selenium WebDriver |
| AppiumLibrary | library-reference | `/rf-agentskills:appium` | Mobile testing for iOS and Android |
| RequestsLibrary | library-reference | `/rf-agentskills:requests` | REST API testing with HTTP methods |
| RESTinstance | library-reference | `/rf-agentskills:restinstance` | REST API testing with JSON Schema validation |
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
skills/                        # Canonical source of truth (11 skills)
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

- Robot Framework 7+ (uses modern syntax: RETURN, IF/ELSE, TRY/EXCEPT)
- Python 3.8+
- Claude Code 1.0.33+

## Cross-Agent Compatibility

Agent Skills are an open standard supported by multiple agent systems. The `skills/` directory at the repository root provides standalone skill access for systems that don't use the Claude Code plugin format (e.g., GitHub Copilot).

## License

Apache-2.0
