# Claude Code Plugin Marketplace Implementation Plan

## Robot Framework Agent Skills

**Status**: Planning (not yet implemented)
**Date**: 2026-02-23
**Source**: Synthesized from 5 parallel research agents analyzing Claude Code plugin documentation, existing codebase, and marketplace architecture options.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Analysis](#2-current-state-analysis)
3. [Architecture Decision: Packaging Strategy](#3-architecture-decision-packaging-strategy)
4. [Target Plugin Structure](#4-target-plugin-structure)
5. [Migration Requirements](#5-migration-requirements)
6. [New Components: Agents, Hooks, MCP Server](#6-new-components-agents-hooks-mcp-server)
7. [Marketplace Manifest Design](#7-marketplace-manifest-design)
8. [Distribution Strategy](#8-distribution-strategy)
9. [CI/CD Pipeline](#9-cicd-pipeline)
10. [Release Management](#10-release-management)
11. [Implementation Phases](#11-implementation-phases)
12. [Risks and Mitigations](#12-risks-and-mitigations)

---

## 1. Executive Summary

This plan converts the existing `robotframework-agentskills` repository (11 Robot Framework skills) into a **Claude Code plugin marketplace**, enabling distribution via:

```
/plugin marketplace add manykarim/robotframework-agentskills
/plugin install rf-agentskills@robotframework-agentskills
```

The marketplace will provide:
- **11 skills**: 5 library-specific (Browser, Selenium, Appium, Requests, RESTinstance), 3 builders (keyword, testcase, resource), 3 tools (libdoc-search, libdoc-explain, results)
- **4 custom agents**: Test Architect, Debug Expert, Keyword Consultant, Migration Guide
- **4 hooks**: .robot validation on save, RF skill routing on prompt, environment check on session start, test reminder on stop
- **1 optional MCP server**: wrapping Python scripts as structured MCP tools
- **Full CI/CD**: GitHub Actions for validation, testing, and release automation

---

## 2. Current State Analysis

### 2.1 Skill Inventory (11 skills)

| # | Skill | Category | Has Scripts | Has References | Has Examples |
|---|-------|----------|-------------|----------------|--------------|
| 1 | `robotframework-browser-skill` | Library/Web | No | 9 files | 5 .robot |
| 2 | `robotframework-selenium-skill` | Library/Web | No | 8 files | 5 .robot |
| 3 | `robotframework-appium-skill` | Library/Mobile | No | 7 files | 5 .robot |
| 4 | `robotframework-requests-skill` | Library/API | No | 6 files | 4 .robot |
| 5 | `robotframework-restinstance-skill` | Library/API | No | 5 files | 4 .robot |
| 6 | `robotframework-keyword-builder` | Builder | `keyword_builder.py` | No | No |
| 7 | `robotframework-testcase-builder` | Builder | `testcase_builder.py` | No | No |
| 8 | `robotframework-resource-architect` | Builder | `resource_architect.py` | No | No |
| 9 | `robotframework-libdoc-search` | Tool | `rf_libdoc.py` | No | No |
| 10 | `robotframework-libdoc-explain` | Tool | (shares rf_libdoc.py) | No | No |
| 11 | `robotframework-results` | Tool | `rf_results.py` | No | No |

### 2.2 Python Script Dependencies

| Script | Stdlib Only | External Dependency |
|--------|-------------|---------------------|
| `keyword_builder.py` (219 lines) | Yes | None |
| `testcase_builder.py` (127 lines) | Yes | None |
| `resource_architect.py` (149 lines) | Yes | None |
| `rf_libdoc.py` (319 lines) | No | `robotframework` (`from robot import libdoc`) |
| `rf_results.py` (416 lines) | No | `robotframework` (`from robot import rebot`, `robot.api`) |

### 2.3 Current Directory Structure

```
robotframework-agentskills/
  skills/
    robotframework-browser-skill/
      SKILL.md
      references/ (9 .md files)
      assets/examples/ (5 .robot files)
    robotframework-selenium-skill/
      SKILL.md
      references/ (8 .md files)
      assets/examples/ (5 .robot files)
    ... (same pattern for other library skills)
    robotframework-keyword-builder/
      SKILL.md
      scripts/keyword_builder.py
    robotframework-libdoc-search/
      SKILL.md
      scripts/rf_libdoc.py
    robotframework-libdoc-explain/
      SKILL.md                          # No scripts/ dir - references search's script
    ...
```

### 2.4 Key Issues Identified

| # | Issue | Severity | Description |
|---|-------|----------|-------------|
| 1 | No `plugin.json` manifest | Critical | Must create `.claude-plugin/plugin.json` |
| 2 | No `marketplace.json` | Critical | Must create `.claude-plugin/marketplace.json` |
| 3 | Script paths break after cache copy | Critical | `python scripts/foo.py` won't resolve when plugin is copied to `~/.claude/plugins/cache/` |
| 4 | Cross-skill script dependency | Critical | `libdoc-explain` has no scripts/ dir, references `libdoc-search`'s `rf_libdoc.py` |
| 5 | `robotframework` package dependency | High | 2 scripts require RF installed; no install mechanism in plugins |
| 6 | Long skill directory names | Medium | `robotframework-browser-skill` -> `/rf-agentskills:robotframework-browser-skill` is unwieldy |
| 7 | No agents, hooks, or MCP | Medium | Missing value-add plugin components |

---

## 3. Architecture Decision: Packaging Strategy

### Options Evaluated

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Single plugin** | All 11 skills in one plugin | Simple install, shared scripts, single version | Users get all skills even if they only need web |
| **B. Category-based (6 plugins)** | 5 domain plugins + 1 meta-plugin | Granular install, smaller footprint | Shared script problem, cross-references break, version matrix |
| **C. Individual (11 plugins)** | One plugin per skill | Maximum granularity | Complex management, 11 manifests, 11 versions |

### Recommendation: Option A (Single Plugin) with Category Tags

**Rationale:**
1. **Install simplicity**: One command installs everything: `/plugin install rf-agentskills@robotframework-agentskills`
2. **Shared scripts**: `rf_libdoc.py` is used by both libdoc-search and libdoc-explain -- no duplication needed
3. **Cross-skill references**: Skills can reference each other naturally within one plugin
4. **Unused skills have zero runtime cost**: Skills only activate when invoked by name or matched by description
5. **Total size ~868KB**: Well within reasonable plugin size
6. **Single version**: All skills tested together, no compatibility matrix
7. **User mental model**: "I installed the Robot Framework plugin" -- done

Category-based grouping (Option B) is viable as a **future enhancement** if the skill count grows significantly. The marketplace `tags` and `category` fields provide discoverability without requiring separate plugins.

### Naming

| Element | Value |
|---------|-------|
| Marketplace name | `robotframework-agentskills` |
| Plugin name | `rf-agentskills` |
| Skill invocation | `/rf-agentskills:browser`, `/rf-agentskills:libdoc-search`, etc. |
| GitHub repo | `manykarim/robotframework-agentskills` |

---

## 4. Target Plugin Structure

```
robotframework-agentskills/                     # Repository root = marketplace root
  .claude-plugin/
    marketplace.json                            # Marketplace catalog (1 plugin)
  plugins/
    rf-agentskills/                             # The single plugin
      .claude-plugin/
        plugin.json                             # Plugin manifest
      skills/
        browser/                                # RENAMED from robotframework-browser-skill
          SKILL.md                              # MODIFIED: updated name in frontmatter
          references/ (9 files)                 # UNCHANGED
          assets/examples/ (5 files)            # UNCHANGED
        selenium/                               # RENAMED
          SKILL.md, references/, assets/
        appium/                                 # RENAMED
          SKILL.md, references/, assets/
        requests/                               # RENAMED
          SKILL.md, references/, assets/
        restinstance/                            # RENAMED
          SKILL.md, references/, assets/
        keyword-builder/                        # RENAMED
          SKILL.md                              # MODIFIED: script paths use ${CLAUDE_PLUGIN_ROOT}
        testcase-builder/
          SKILL.md
        resource-architect/
          SKILL.md
        libdoc-search/
          SKILL.md                              # MODIFIED: points to shared script
        libdoc-explain/
          SKILL.md                              # MODIFIED: points to shared script
        results/
          SKILL.md
      agents/
        rf-test-architect.md                    # NEW
        rf-debug-expert.md                      # NEW
        rf-keyword-consultant.md                # NEW
        rf-migration-guide.md                   # NEW
      hooks/
        hooks.json                              # NEW
      scripts/                                  # CONSOLIDATED from individual skill dirs
        rf_libdoc.py                            # Shared by libdoc-search + libdoc-explain
        rf_results.py
        keyword_builder.py
        testcase_builder.py
        resource_architect.py
        validate_robot.sh                       # Hook script
        check_rf_environment.sh                 # Hook script
      servers/
        rf-tools-server.py                      # NEW (optional MCP server)
      settings.json                             # NEW: plugin defaults
  # Repository-level files (not part of the plugin):
  .github/workflows/                            # CI/CD
  tests/                                        # Test suite
  docs/                                         # Documentation
  scripts/                                      # Build/release scripts
  README.md
  LICENSE
```

---

## 5. Migration Requirements

### 5.1 Create Plugin Manifest

**File**: `plugins/rf-agentskills/.claude-plugin/plugin.json`

```json
{
  "name": "rf-agentskills",
  "version": "1.0.0",
  "description": "Robot Framework agent skills for Claude Code - library references, test/keyword/resource generators, libdoc search, and results analysis",
  "author": {
    "name": "manykarim",
    "email": "manykarim@users.noreply.github.com"
  },
  "homepage": "https://github.com/manykarim/robotframework-agentskills",
  "repository": "https://github.com/manykarim/robotframework-agentskills",
  "license": "Apache-2.0",
  "keywords": [
    "robotframework", "testing", "automation", "web-testing",
    "api-testing", "mobile-testing", "playwright", "selenium",
    "appium", "requests", "restinstance"
  ]
}
```

### 5.2 Rename Skill Directories

| Current | Target | Invocation |
|---------|--------|------------|
| `robotframework-browser-skill/` | `browser/` | `/rf-agentskills:browser` |
| `robotframework-selenium-skill/` | `selenium/` | `/rf-agentskills:selenium` |
| `robotframework-appium-skill/` | `appium/` | `/rf-agentskills:appium` |
| `robotframework-requests-skill/` | `requests/` | `/rf-agentskills:requests` |
| `robotframework-restinstance-skill/` | `restinstance/` | `/rf-agentskills:restinstance` |
| `robotframework-keyword-builder/` | `keyword-builder/` | `/rf-agentskills:keyword-builder` |
| `robotframework-testcase-builder/` | `testcase-builder/` | `/rf-agentskills:testcase-builder` |
| `robotframework-resource-architect/` | `resource-architect/` | `/rf-agentskills:resource-architect` |
| `robotframework-libdoc-search/` | `libdoc-search/` | `/rf-agentskills:libdoc-search` |
| `robotframework-libdoc-explain/` | `libdoc-explain/` | `/rf-agentskills:libdoc-explain` |
| `robotframework-results/` | `results/` | `/rf-agentskills:results` |

### 5.3 Update SKILL.md Frontmatter

All 11 SKILL.md files need `name` updated to match directory name:

**Before:**
```yaml
---
name: robotframework-browser-skill
description: Guide AI agents in creating Browser Library tests...
---
```

**After:**
```yaml
---
name: browser
description: Guide AI agents in creating Browser Library tests...
---
```

### 5.4 Fix Script Path References (Critical)

All 6 SKILL.md files that reference scripts must use `${CLAUDE_PLUGIN_ROOT}`:

**Before:**
```bash
python scripts/rf_libdoc.py --library BuiltIn --search "create temp file" --pretty
```

**After:**
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/rf_libdoc.py --library BuiltIn --search "create temp file" --pretty
```

**Files requiring changes:**
| SKILL.md | Script Referenced | Occurrences |
|----------|-------------------|-------------|
| `libdoc-search/SKILL.md` | `rf_libdoc.py` | 2 |
| `libdoc-explain/SKILL.md` | `rf_libdoc.py` | 3 |
| `results/SKILL.md` | `rf_results.py` | 4 |
| `keyword-builder/SKILL.md` | `keyword_builder.py` | 2 |
| `testcase-builder/SKILL.md` | `testcase_builder.py` | 1 |
| `resource-architect/SKILL.md` | `resource_architect.py` | 3 |

### 5.5 Consolidate Scripts to Plugin Root

Move all Python scripts from individual skill directories to `plugins/rf-agentskills/scripts/`:

```
scripts/
  rf_libdoc.py              # FROM skills/robotframework-libdoc-search/scripts/
  rf_results.py             # FROM skills/robotframework-results/scripts/
  keyword_builder.py        # FROM skills/robotframework-keyword-builder/scripts/
  testcase_builder.py       # FROM skills/robotframework-testcase-builder/scripts/
  resource_architect.py     # FROM skills/robotframework-resource-architect/scripts/
```

This solves the libdoc-explain cross-dependency: both libdoc-search and libdoc-explain reference `${CLAUDE_PLUGIN_ROOT}/scripts/rf_libdoc.py`.

### 5.6 Dependency Documentation

Add error handling to `rf_libdoc.py` and `rf_results.py` for missing `robotframework`:

```python
try:
    from robot import libdoc
except ImportError:
    print("Error: robotframework package required. Install: pip install robotframework", file=sys.stderr)
    sys.exit(1)
```

---

## 6. New Components: Agents, Hooks, MCP Server

### 6.1 Custom Agents (4)

| Agent | File | When Invoked | Skills Orchestrated |
|-------|------|-------------|---------------------|
| **RF Test Architect** | `agents/rf-test-architect.md` | Planning test projects, choosing libraries, designing directory layout | resource-architect, keyword-builder, testcase-builder, libdoc-search |
| **RF Debug Expert** | `agents/rf-debug-expert.md` | Analyzing test failures from output.xml, diagnosing flaky tests | results, libdoc-search, troubleshooting references |
| **RF Keyword Consultant** | `agents/rf-keyword-consultant.md` | Finding right keywords, comparing across libraries | libdoc-search, libdoc-explain, keyword-builder |
| **RF Migration Guide** | `agents/rf-migration-guide.md` | Upgrading RF versions, migrating Selenium->Browser, modernizing syntax | libdoc-search, libdoc-explain, keyword-builder |

**Agent file format:**
```markdown
---
name: rf-test-architect
description: Plan and design Robot Framework test suites, resource structures,
  and keyword hierarchies. Invoke when the user needs to architect a complete
  test automation project, decide between testing libraries, or design patterns.
---

# Robot Framework Test Architect

You are a senior test automation architect specializing in Robot Framework...
```

### 6.2 Hooks (4 events)

**File**: `plugins/rf-agentskills/hooks/hooks.json`

| Event | Type | Purpose |
|-------|------|---------|
| `PostToolUse` (Write\|Edit) | command | Auto-validate `.robot`/`.resource` files after every write/edit using `robot.api.get_model` |
| `UserPromptSubmit` | prompt | Inject RF skill/agent routing guidance so Claude considers appropriate skills |
| `SessionStart` | command | Check for python3, robotframework, and optional libraries; print actionable install commands |
| `Stop` | prompt | Remind user to run test suite if `.robot` files were created/modified during session |

**Hook design principles:**
- All hooks exit 0 (never block the user)
- Scripts use `${CLAUDE_PLUGIN_ROOT}` for paths
- `validate_robot.sh` gracefully handles non-RF files and missing RF installation
- `check_rf_environment.sh` is informational only

### 6.3 MCP Server (Optional)

**File**: `plugins/rf-agentskills/servers/rf-tools-server.py`

A Python MCP server exposing 6 tools:

| MCP Tool | Wraps Script | Parameters |
|----------|-------------|------------|
| `rf_libdoc_search` | `rf_libdoc.py` | library, search, limit, weights |
| `rf_libdoc_explain` | `rf_libdoc.py` | library, keyword |
| `rf_results_analyze` | `rf_results.py` | output_path, sections |
| `rf_keyword_builder` | `keyword_builder.py` | keyword_name, steps, arguments, ... |
| `rf_testcase_builder` | `testcase_builder.py` | test_name, steps, setup, teardown, ... |
| `rf_resource_architect` | `resource_architect.py` | plan, project_root, write |

**Benefits over bash invocation:**
- Structured JSON schemas (Claude can call with validated parameters)
- Module imports instead of subprocess spawn (faster)
- Graceful degradation if `mcp` package not installed

**Plugin `.mcp.json`:**
```json
{
  "mcpServers": {
    "rf-tools": {
      "command": "python3",
      "args": ["${CLAUDE_PLUGIN_ROOT}/servers/rf-tools-server.py"],
      "env": {
        "PLUGIN_ROOT": "${CLAUDE_PLUGIN_ROOT}"
      }
    }
  }
}
```

### 6.4 Plugin Settings

**File**: `plugins/rf-agentskills/settings.json`

```json
{
  "agent": "rf-test-architect"
}
```

This activates the Test Architect agent as the default for the plugin. Users can invoke other agents explicitly.

---

## 7. Marketplace Manifest Design

**File**: `.claude-plugin/marketplace.json` (repository root)

```json
{
  "name": "robotframework-agentskills",
  "owner": {
    "name": "manykarim",
    "email": "manykarim@users.noreply.github.com"
  },
  "metadata": {
    "description": "Robot Framework agent skills for Claude Code - web, API, mobile testing, asset generation, and RF analysis tools",
    "version": "1.0.0",
    "pluginRoot": "./plugins"
  },
  "plugins": [
    {
      "name": "rf-agentskills",
      "source": "./rf-agentskills",
      "description": "Complete Robot Framework skills suite: 11 skills for web/API/mobile testing, keyword/test/resource generation, and libdoc/results tools. Includes 4 specialized agents and automated .robot validation.",
      "version": "1.0.0",
      "author": { "name": "manykarim" },
      "homepage": "https://github.com/manykarim/robotframework-agentskills",
      "repository": "https://github.com/manykarim/robotframework-agentskills",
      "license": "Apache-2.0",
      "keywords": [
        "robotframework", "testing", "automation", "playwright", "selenium",
        "appium", "requests", "restinstance", "web-testing", "api-testing",
        "mobile-testing", "test-generation", "libdoc"
      ],
      "category": "testing",
      "tags": [
        "robot-framework", "test-automation", "browser-testing",
        "api-testing", "mobile-testing", "code-generation"
      ]
    }
  ]
}
```

---

## 8. Distribution Strategy

### 8.1 Installation Methods

**Individual users:**
```bash
# Add marketplace
/plugin marketplace add manykarim/robotframework-agentskills

# Install the plugin
/plugin install rf-agentskills@robotframework-agentskills

# Test a skill
/rf-agentskills:browser
```

**Team distribution via `.claude/settings.json`:**
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

**Organizational lockdown:**
```json
{
  "strictKnownMarketplaces": [
    {
      "source": "github",
      "repo": "manykarim/robotframework-agentskills"
    }
  ]
}
```

### 8.2 Release Channels

| Channel | Branch/Ref | Purpose | Update Frequency |
|---------|-----------|---------|-----------------|
| **stable** | `stable` branch | Production releases only | On tagged releases |
| **latest** | `latest` branch | Includes release candidates | On main CI pass |
| **pinned** | `v1.0.0` tag / SHA | Exact version lock | Never (immutable) |

### 8.3 Auto-Updates

- Public repo: auto-updates work without tokens
- Private repo: requires `GITHUB_TOKEN` or `GH_TOKEN` environment variable
- Users refresh manually: `/plugin marketplace update`

---

## 9. CI/CD Pipeline

### 9.1 CI Workflow (on push/PR to main)

```yaml
Jobs:
  1. validate-marketplace    # JSON schema validation
  2. validate-structure      # All skills have SKILL.md
  3. validate-frontmatter    # YAML frontmatter has name + description
  4. test-python-scripts     # py_compile + smoke tests (Python 3.10-3.13 matrix)
  5. validate-robot-syntax   # Parse all .robot files with robot.api.get_model
  6. lint                    # ruff check on all Python scripts
  7. unit-tests              # pytest tests/
```

### 9.2 Release Workflow (on tag push)

```yaml
Triggers on: v*.*.* tags
Steps:
  1. Run full CI validation
  2. Generate changelog from commits since last tag
  3. Create GitHub Release with changelog
  4. Fast-forward 'stable' branch to tag
  5. Fast-forward 'latest' branch to tag
  6. Create release/X.Y branch
```

### 9.3 Latest Branch Auto-Update (on main CI pass)

```yaml
Triggers on: CI success on main
Steps:
  1. Fast-forward 'latest' branch to main HEAD
```

### 9.4 Validation Script (local)

`scripts/validate-marketplace.py` -- local equivalent of `claude plugin validate .`:
- Validates marketplace.json schema
- Checks all SKILL.md files have valid frontmatter
- Verifies all skill directories referenced in marketplace exist
- Checks Python scripts compile
- Validates .robot file syntax

---

## 10. Release Management

### 10.1 Version Bumping

```bash
# scripts/bump-version.sh
./scripts/bump-version.sh patch    # 1.0.0 -> 1.0.1
./scripts/bump-version.sh minor    # 1.0.0 -> 1.1.0
./scripts/bump-version.sh major    # 1.0.0 -> 2.0.0
```

Updates version in both `plugin.json` and `marketplace.json`.

### 10.2 Release Workflow

```bash
# 1. Bump version
./scripts/bump-version.sh minor

# 2. Commit and tag
git add plugins/rf-agentskills/.claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "release: v1.1.0"
git tag v1.1.0
git push origin main --tags

# 3. GitHub Actions automatically:
#    - Validates everything
#    - Creates GitHub Release
#    - Updates stable + latest branches
```

### 10.3 Semantic Versioning Policy

| Change Type | Version Bump | Examples |
|-------------|-------------|---------|
| Bug fix in SKILL.md or script | Patch | Fix keyword example, fix script error |
| New reference file or example | Patch | Add troubleshooting.md to a skill |
| New skill added | Minor | Add robotframework-datadriver-skill |
| New agent or hook added | Minor | Add rf-performance-analyst agent |
| Breaking SKILL.md restructure | Major | Rename skills, change script interfaces |
| Plugin name change | Major | rf-agentskills -> rf-testing-suite |

---

## 11. Implementation Phases

### Phase 1: Plugin Scaffold (est. 2-3 hours)

- [ ] Create `.claude-plugin/marketplace.json` at repository root
- [ ] Create `plugins/rf-agentskills/.claude-plugin/plugin.json`
- [ ] Create `plugins/rf-agentskills/settings.json`
- [ ] Create directory structure under `plugins/rf-agentskills/`

### Phase 2: Migrate Skills (est. 4-6 hours)

- [ ] Copy/move all 11 skill directories from `skills/` to `plugins/rf-agentskills/skills/` with shortened names
- [ ] Update all 11 SKILL.md `name` fields in frontmatter
- [ ] Consolidate all 5 Python scripts to `plugins/rf-agentskills/scripts/`
- [ ] Update 15 script path references in 6 SKILL.md files to use `${CLAUDE_PLUGIN_ROOT}`
- [ ] Add ImportError handling to `rf_libdoc.py` and `rf_results.py`
- [ ] Verify all `references/` relative paths still resolve correctly
- [ ] Remove empty `scripts/` subdirectories from individual skill dirs

### Phase 3: Add Plugin Components (est. 4-6 hours)

- [ ] Create 4 agent markdown files in `plugins/rf-agentskills/agents/`
  - `rf-test-architect.md` -- suite architecture and library selection
  - `rf-debug-expert.md` -- failure diagnosis from output.xml
  - `rf-keyword-consultant.md` -- keyword discovery and comparison
  - `rf-migration-guide.md` -- version/library migration
- [ ] Create `plugins/rf-agentskills/hooks/hooks.json` with 4 hook events
- [ ] Create `plugins/rf-agentskills/scripts/validate_robot.sh` (PostToolUse hook)
- [ ] Create `plugins/rf-agentskills/scripts/check_rf_environment.sh` (SessionStart hook)
- [ ] Create `plugins/rf-agentskills/servers/rf-tools-server.py` (optional MCP server)
- [ ] Create `plugins/rf-agentskills/.mcp.json` (MCP server config)

### Phase 4: CI/CD Setup (est. 2-3 hours)

- [ ] Create `.github/workflows/ci.yml`
- [ ] Create `.github/workflows/release.yml`
- [ ] Create `.github/workflows/update-latest.yml`
- [ ] Create `scripts/validate-marketplace.py`
- [ ] Create `scripts/bump-version.sh`

### Phase 5: Testing (est. 3-4 hours)

- [ ] Write marketplace validation tests (`tests/test_marketplace_validation.py`)
- [ ] Write Python script unit tests (`tests/test_*.py` for each script)
- [ ] Test plugin locally: `claude --plugin-dir ./plugins/rf-agentskills`
- [ ] Test each skill invocation: `/rf-agentskills:browser`, etc.
- [ ] Test agents appear in `/agents`
- [ ] Test hooks fire correctly
- [ ] Validate with `claude plugin validate .`

### Phase 6: Release & Distribution (est. 1-2 hours)

- [ ] Create `stable` and `latest` branches
- [ ] Tag `v1.0.0` and push
- [ ] Verify GitHub Release created
- [ ] Test marketplace installation: `/plugin marketplace add manykarim/robotframework-agentskills`
- [ ] Test plugin installation: `/plugin install rf-agentskills@robotframework-agentskills`
- [ ] Create team distribution template (`.claude/settings.json` snippet)
- [ ] Update repository README with installation instructions

### Phase 7: Cleanup & Polish (est. 1-2 hours)

- [ ] Decide: keep original `skills/` at repo root (for standalone use) or remove (marketplace only)
- [ ] Update top-level README with marketplace installation instructions
- [ ] Add GitHub topics: robotframework, claude-code, agent-skills, test-automation, plugin-marketplace
- [ ] Clean up draft files created by research agents
- [ ] Add `CONTRIBUTING.md` for skill contribution guidelines

**Total estimated effort: 17-26 hours**

---

## 12. Risks and Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | `${CLAUDE_PLUGIN_ROOT}` not expanded in SKILL.md bash blocks | Medium | Scripts fail entirely | Test early; if unsupported, use wrapper scripts or MCP server as fallback |
| 2 | Reference file paths not resolved relative to SKILL.md | Low | Degraded AI guidance | Test path resolution; if broken, move references to plugin-level directory |
| 3 | User lacks `robotframework` Python package | High | 2 of 5 scripts fail | Add clear ImportError messages + SessionStart env check hook |
| 4 | Plugin spec evolves (breaking changes) | Medium | Migration rework | Pin to current spec version; monitor Claude Code changelogs |
| 5 | `python` not in PATH (only `python3`) | Medium | All scripts fail | Use `python3` consistently in all SKILL.md examples |
| 6 | Reserved marketplace names block our choice | Low | Must rename | `robotframework-agentskills` is not in the reserved list (verified) |
| 7 | Plugin cache copy breaks symlinks | Medium | Shared script fails | Eliminate symlinks; use consolidated scripts/ at plugin root |
| 8 | Release branch force-push conflicts | Low | Branch out of sync | Workflow uses `--force` for ref-tracking branches |

---

## Appendix A: Draft Artifacts Created by Research Agents

The following files were created as drafts during the research phase and need review/refinement before implementation:

| File | Created By | Status |
|------|-----------|--------|
| `agents/rf-test-architect.md` | agents/hooks designer | Draft - needs move to plugin dir |
| `agents/rf-debug-expert.md` | agents/hooks designer | Draft - needs move to plugin dir |
| `agents/rf-keyword-consultant.md` | agents/hooks designer | Draft - needs move to plugin dir |
| `agents/rf-migration-guide.md` | agents/hooks designer | Draft - needs move to plugin dir |
| `hooks/hooks.json` | agents/hooks designer | Draft - needs move to plugin dir |
| `scripts/validate_robot.sh` | agents/hooks designer | Draft - needs move to plugin dir |
| `scripts/check_rf_environment.sh` | agents/hooks designer | Draft - needs move to plugin dir |
| `servers/rf-tools-server.py` | agents/hooks designer | Draft - needs move to plugin dir |
| `plugins/rf-web-testing/plugin.json` | marketplace architect | Draft - superseded by single-plugin approach |
| `plugins/rf-api-testing/plugin.json` | marketplace architect | Draft - superseded |
| `plugins/rf-mobile-testing/plugin.json` | marketplace architect | Draft - superseded |
| `plugins/rf-builders/plugin.json` | marketplace architect | Draft - superseded |
| `plugins/rf-tools/plugin.json` | marketplace architect | Draft - superseded |
| `plugins/rf-all/plugin.json` | marketplace architect | Draft - superseded |
| `scripts/build-plugins.sh` | marketplace architect | Draft - superseded |
| `.github/workflows/ci.yml` | distribution planner | Draft - needs review |
| `.github/workflows/release.yml` | distribution planner | Draft - needs review |
| `.github/workflows/update-latest.yml` | distribution planner | Draft - needs review |
| `scripts/validate-marketplace.py` | distribution planner | Draft - needs review |
| `scripts/bump-version.sh` | distribution planner | Draft - needs review |
| `tests/test_marketplace_validation.py` | distribution planner | Draft - needs review |
| `tests/test_keyword_builder.py` | distribution planner | Draft - needs review |
| `tests/test_libdoc_search.py` | distribution planner | Draft - needs review |
| `docs/marketplace-architecture.md` | marketplace architect | Draft - superseded by this plan |

## Appendix B: Alternative Architecture (Category-Based)

If the single-plugin approach proves limiting (e.g., skill count grows beyond 20+), the category-based approach splits into:

| Plugin | Skills | Install Command |
|--------|--------|-----------------|
| `rf-web-testing` | browser, selenium | `/plugin install rf-web-testing@robotframework-agentskills` |
| `rf-api-testing` | requests, restinstance | `/plugin install rf-api-testing@...` |
| `rf-mobile-testing` | appium | `/plugin install rf-mobile-testing@...` |
| `rf-builders` | keyword-builder, testcase-builder, resource-architect | `/plugin install rf-builders@...` |
| `rf-tools` | libdoc-search, libdoc-explain, results | `/plugin install rf-tools@...` |
| `rf-all` | All 11 skills (meta-plugin) | `/plugin install rf-all@...` |

Draft manifests for this approach exist in `plugins/rf-*/plugin.json` (created by the marketplace architect agent).

## Appendix C: Integration Flow Diagram

```
Session Start
    |
    v
[SessionStart hook] -> check_rf_environment.sh -> prints installed RF packages
    |
    v
User sends prompt
    |
    v
[UserPromptSubmit hook] -> injects RF skill/agent routing context
    |
    v
Claude processes request
    |-- Complex planning?   -> invokes rf-test-architect agent
    |-- Failure analysis?   -> invokes rf-debug-expert agent
    |-- Keyword question?   -> invokes rf-keyword-consultant agent
    |-- Migration task?     -> invokes rf-migration-guide agent
    |-- Direct generation   -> loads appropriate SKILL.md
    |-- Script-based tool   -> calls MCP server or runs Python script via bash
    |
    v
Claude writes/edits .robot file
    |
    v
[PostToolUse hook] -> validate_robot.sh -> parses file with robot.api.get_model
    |
    v
Session ends
    |
    v
[Stop hook] -> reminds user to run tests and check results
```
