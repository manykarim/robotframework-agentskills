# Robot Framework Agent Skills for Claude Code

A Claude Code plugin marketplace providing AI agent skills for Robot Framework test automation. Includes skills for web testing (Browser/Selenium), API testing (Requests/RESTinstance), mobile testing (Appium), asset generation, and RF analysis tools.

## Quick Install

```bash
# Add the marketplace
/plugin marketplace add manykarim/robotframework-agentskills

# Install the plugin
/plugin install rf-agentskills@robotframework-agentskills
```

## What You Get

### 11 Skills

| Skill | Command | Description |
|-------|---------|-------------|
| Browser Library | `/rf-agentskills:browser` | Web testing with Playwright (auto-waiting, assertions, Shadow DOM) |
| SeleniumLibrary | `/rf-agentskills:selenium` | Web testing with Selenium WebDriver |
| AppiumLibrary | `/rf-agentskills:appium` | Mobile testing for iOS and Android |
| RequestsLibrary | `/rf-agentskills:requests` | REST API testing with HTTP methods |
| RESTinstance | `/rf-agentskills:restinstance` | REST API testing with JSON Schema validation |
| Keyword Builder | `/rf-agentskills:keyword-builder` | Generate RF user keywords from structured input |
| Test Case Builder | `/rf-agentskills:testcase-builder` | Generate RF test cases from structured input |
| Resource Architect | `/rf-agentskills:resource-architect` | Design resource/variable file layouts |
| Libdoc Search | `/rf-agentskills:libdoc-search` | Search library keywords by use case |
| Libdoc Explain | `/rf-agentskills:libdoc-explain` | Explain keyword arguments and documentation |
| Results | `/rf-agentskills:results` | Parse output.xml into JSON summaries |

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

## Standalone Usage (Without Marketplace)

You can also use the skills directly without the marketplace by loading the plugin directory:

```bash
claude --plugin-dir ./plugins/rf-agentskills
```

Or copy the `skills/` directory to your project's `.claude/skills/` for standalone skill usage without the plugin system.

## What is an Agent Skill?

Agent Skills are modular, self-contained packages that include a `SKILL.md` file (instructions) plus optional scripts, references, and assets. AI agents load a skill when its name or description matches the user request. Skills use progressive disclosure: only metadata is loaded initially; the full skill body and references are loaded on demand.

## Project Structure

```
robotframework-agentskills/
  .claude-plugin/
    marketplace.json          # Marketplace catalog
  plugins/
    rf-agentskills/           # The plugin
      .claude-plugin/
        plugin.json           # Plugin manifest
      skills/                 # 11 RF skills
        browser/              # Browser Library skill
        selenium/             # SeleniumLibrary skill
        appium/               # AppiumLibrary skill
        requests/             # RequestsLibrary skill
        restinstance/         # RESTinstance skill
        keyword-builder/      # Keyword generation
        testcase-builder/     # Test case generation
        resource-architect/   # Resource/variable design
        libdoc-search/        # Library keyword search
        libdoc-explain/       # Keyword documentation
        results/              # output.xml analysis
      agents/                 # 4 specialized agents
      hooks/                  # Automated event hooks
      scripts/                # Python scripts + hook helpers
      servers/                # Optional MCP server
  skills/                     # Original skills (standalone usage)
```

## Development

### Validate the marketplace locally

```bash
python scripts/validate-marketplace.py
```

### Run tests

```bash
pip install pytest robotframework
pytest tests/ -v
```

### Test the plugin locally

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
