# Robot Framework Agent Skills - Architecture Review Report

**Date:** 2026-03-17
**Scope:** Skill structure, script organization, hook/agent/MCP design, cross-agent portability

---

## Executive Summary

The project has 11 skills distributed across 3 channels (root `skills/`, Claude Code plugin, VS Code extension) with **298 files that need to stay in sync** and **5 Python scripts duplicated up to 7 times each**. The current flat `plugins/.../scripts/` layout contradicts both Anthropic's official best practices and Block Engineering's principles for designing agent skills. Critical bugs exist in the MCP server path resolution, and drift has already begun between copies.

**Recommendation:** Move to per-skill `scripts/` subdirectories in the canonical `skills/` root, and derive all distribution channels from that single source of truth via a build step.

---

## 1. Current Structure Analysis

### 1.1 Three Distribution Channels

```
skills/                          ← Root (canonical source)
  robotframework-keyword-builder/
    scripts/keyword_builder.py   ← Per-skill scripts/ ✓
    SKILL.md
  robotframework-browser-skill/
    references/*.md              ← Per-skill references/ ✓
    assets/examples/*.robot
    SKILL.md
  ...

plugins/rf-agentskills/          ← Claude Code Plugin
  scripts/                       ← Flat scripts/ for ALL skills ✗
    keyword_builder.py
    testcase_builder.py
    resource_architect.py
    rf_libdoc.py
    rf_results.py
  skills/                        ← Short-named skill dirs
    keyword-builder/SKILL.md     ← Different paths in SKILL.md
    browser/SKILL.md
    ...
  agents/                        ← 4 agent definitions
  hooks/hooks.json
  servers/rf-tools-server.py     ← MCP server (BROKEN paths)

vscode-extension/skills/         ← VS Code Extension
  robotframework-keyword-builder/
    scripts/keyword_builder.py   ← Duplicate copy
    SKILL.md
  ...
  skills/                        ← DOUBLE NESTING BUG (full duplicate)
    robotframework-keyword-builder/
      scripts/keyword_builder.py ← Another duplicate copy!
    ...
```

### 1.2 Duplication Metrics

| Resource | Root | Plugin | VS Code | VS Code/skills/skills/ | Total Copies |
|----------|------|--------|---------|----------------------|-------------|
| `keyword_builder.py` (7.5KB) | 1 | 1 | 1 | 1 | **4** |
| `testcase_builder.py` (3.9KB) | 1 | 1 | 1 | 1 | **4** |
| `resource_architect.py` (4.9KB) | 1 | 1 | 1 | 1 | **4** |
| `rf_libdoc.py` (10.9KB) | 2* | 1 | 2* | 2* | **7** |
| `rf_results.py` (14.1KB) | 1 | 1 | 1 | 1 | **4** |
| SKILL.md files (11 skills) | 11 | 11 | 11 | 11 | **44** |
| Reference .md files | 35 | 35 | 35 | 35 | **140** |

*`rf_libdoc.py` is shared by `libdoc-search` and `libdoc-explain` skills, each with its own copy.

**Total duplicated script bytes:** ~160KB across 23 unnecessary copies
**Total files requiring sync:** 298 (74 root + 76 plugin + 148 vscode)

### 1.3 Known Drift (Already Occurring)

| File | Root → Plugin Drift | Description |
|------|-------------------|-------------|
| `rf_libdoc.py` | **9 diff lines** | Plugin added `try/except ImportError` guard |
| `rf_results.py` | **11 diff lines** | Plugin added `try/except ImportError` guard |
| `testcase_builder.py` | **2 diff lines** | Plugin removed unused `import re` |
| All SKILL.md (script skills) | **Path divergence** | Root: `python scripts/foo.py`, Plugin: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/foo.py"` |
| All SKILL.md (all skills) | **Name divergence** | Root: `robotframework-keyword-builder`, Plugin: `keyword-builder` |

The plugin copies are actually **better** (graceful error handling, unused import removed), meaning the canonical source has fallen behind its derivative.

---

## 2. Scripts/ Subfolder: Per-Skill vs Flat Plugin Root

### 2.1 Current State: Hybrid (Inconsistent)

- **Root `skills/`**: Per-skill `scripts/` subdirectories ✓ (correct per best practices)
- **Plugin `plugins/rf-agentskills/`**: Flat `scripts/` at plugin root ✗ (all scripts in one dir)
- **VS Code extension**: Per-skill `scripts/` (mirrors root) ✓

### 2.2 Anthropic's Official Best Practices

From https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices:

> The complete Skill directory structure might look like this:
> ```
> pdf/
> ├── SKILL.md
> ├── FORMS.md
> ├── reference.md
> └── scripts/
>     ├── analyze_form.py
>     ├── fill_form.py
>     └── validate.py
> ```

**Key principles from Anthropic:**
1. **Each skill is a self-contained folder** with `SKILL.md` + supporting files
2. **Scripts belong inside the skill directory** in a `scripts/` subfolder
3. **Progressive disclosure**: SKILL.md is loaded first, references on demand, scripts executed (not loaded into context)
4. **References one level deep** from SKILL.md - no deeply nested references
5. **SKILL.md body under 500 lines** for optimal performance
6. **Forward slashes only** in paths (no Windows-style backslashes)
7. **Consistent terminology** throughout
8. **Name field**: max 64 chars, lowercase + hyphens only, no reserved words
9. **Description in third person**: "Processes files..." not "I can help you..." or "You can use this..."
10. **Scripts should solve, not punt**: Handle errors explicitly with fallback behavior, not bare crashes
11. **No voodoo constants**: All configuration values must be justified and documented

### 2.3 Block Engineering's Principles

From https://engineering.block.xyz/blog/3-principles-for-designing-agent-skills:

1. **"Know What the Agent Should NOT Decide"** → Deterministic tasks in scripts, not prompts
   - "Same input, same output -- every time"
   - Scripts are the "single source of truth"
   - The agent is explicitly forbidden from overriding script output
2. **"Know What the Agent SHOULD Decide"** → Agent handles interpretation, not execution
   - Two-zone architecture: Scripts own rules/execution; Agent owns interpretation/action
3. **"Write a Constitution, Not a Suggestion"** → Hard constraints prevent drift
   - Explicit non-negotiable constraints in SKILL.md
   - "Defensive design against the agent's helpfulness"
4. **Bonus: Design for the Arc** → Skills should create conversation arcs, not just one-shot output
   - Script output becomes agent input for follow-up dialogue

### 2.4 Recommendation: Per-Skill `scripts/` is Better

| Factor | Per-Skill `scripts/` | Flat Plugin `scripts/` |
|--------|---------------------|----------------------|
| **Portability** | Skill is self-contained, works anywhere | Depends on external `scripts/` dir |
| **Anthropic standard** | Matches official best practices | Violates recommended structure |
| **Cross-agent compat** | Works with Cursor, Copilot, Goose, etc. | Only works with Claude Code plugin system |
| **Skill discovery** | Agent sees `scripts/` when reading skill dir | Agent must know about separate scripts dir |
| **Path resolution** | Relative `scripts/foo.py` from skill dir | Requires `${CLAUDE_PLUGIN_ROOT}` or absolute |
| **Independence** | Can copy/distribute a single skill folder | Must copy skill + shared scripts |
| **Testing** | `cd skill-dir && python scripts/foo.py` | Need to set CWD to plugin root |

**The flat `plugins/.../scripts/` pattern exists because** the plugin system needs all scripts accessible via `${CLAUDE_PLUGIN_ROOT}/scripts/`. But this is a distribution concern, not an authoring concern. The build/release step should handle this.

---

## 3. Cross-Agent Portability Analysis

### 3.1 Path Resolution Across Agents

| Agent | Skill Discovery | Script CWD | Plugin Root Variable |
|-------|----------------|-----------|---------------------|
| **Claude Code** | `.claude/skills/`, plugins | **Project root** (not skill dir) | `${CLAUDE_PLUGIN_ROOT}` (JSON only!) |
| **GitHub Copilot** | `.github/skills/`, `.claude/skills/` | Project root | None |
| **OpenAI Codex** | `.codex/skills/`, `.claude/skills/` | `.codex/` folder | None |
| **Cursor** | `.cursor/rules/` (no native SKILL.md) | Project root | None |
| **Goose/Amp/Gemini CLI** | `.claude/skills/` (compatibility) | Project root | None |

### 3.2 Key Findings (with GitHub Issue Citations)

1. **`${CLAUDE_PLUGIN_ROOT}` does NOT expand in SKILL.md** ([Issue #9354](https://github.com/anthropics/claude-code/issues/9354)): The variable is only expanded in JSON config files (hooks.json, .mcp.json), not in SKILL.md markdown content. Claude sees the literal string and must infer the path from context. **This means all plugin SKILL.md files using `"${CLAUDE_PLUGIN_ROOT}/scripts/..."` are fragile.**

2. **Relative paths fail on first attempt** ([Issue #11011](https://github.com/anthropics/claude-code/issues/11011)): When SKILL.md uses `python scripts/foo.py`, Claude Code's Bash CWD is the project root, not the skill directory. Claude gets a `base_path` from the Skill tool and can self-correct on retry, but wastes a round-trip.

3. **`${CLAUDE_PLUGIN_ROOT}` not set in SessionStart hooks** ([Issue #27145](https://github.com/anthropics/claude-code/issues/27145)), **fails on Windows** ([Issue #16116](https://github.com/anthropics/claude-code/issues/16116)), and can point to **stale cache** ([Issue #15642](https://github.com/anthropics/claude-code/issues/15642)).

4. **MCP server approach is the most reliable**: Uses `os.path.dirname(os.path.abspath(__file__))` at import time, bypassing all CWD/variable-expansion issues.

5. **AGENTS.md standard** ([agents.md](https://agents.md/)): The Agentic AI Foundation (Linux Foundation, co-founded by Anthropic + OpenAI + Block) defines project-level instructions but has no script packaging. SKILL.md remains the de facto standard for bundled skills with scripts.

6. **SkillKit** ([github.com/rohitg00/skillkit](https://github.com/rohitg00/skillkit)): Package manager that translates skills across 44+ agents. Consider publishing to it for maximum portability.

### 3.3 Path Resolution Status for This Project

| Channel | Path Pattern | Works? | Why |
|---------|-------------|--------|-----|
| Root `skills/` SKILL.md | `python scripts/rf_libdoc.py` | **Only if CWD is skill dir** | CWD is usually project root |
| Plugin SKILL.md | `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/..."` | **Fragile** | Variable not expanded in markdown |
| VS Code SKILL.md | `python scripts/rf_libdoc.py` | **Only if CWD is skill dir** | Same issue as root |
| MCP server | `os.path.join(_PLUGIN_ROOT, "scripts", ...)` | **Correct approach** (but has wrong paths) | `__file__`-relative resolution |

### 3.4 Portable Solutions

**Option A: pip-installable package** (most portable)
```bash
pip install robotframework-agentskills
# Then SKILL.md references: rf-libdoc-search --library BuiltIn --search "query"
```
No path resolution issues. Works with every agent.

**Option B: MCP server** (already exists, needs fixes)
Tools are invoked by the agent via tool calls, not bash commands. Path resolution is handled at server startup. Works with any MCP-compatible agent.

**Option C: Skill-relative instructions** (simplest)
SKILL.md says "Run the script in this skill's `scripts/` subdirectory" and the agent resolves the full path from the skill's `base_path`.

---

## 4. Bugs and Issues Found

### 4.1 CRITICAL: MCP Server Broken Script Paths

**File:** `plugins/rf-agentskills/servers/rf-tools-server.py:56-61`

```python
_SCRIPT_PATHS = {
    "rf_libdoc": os.path.join(_SKILLS_DIR, "robotframework-libdoc-search", "scripts", "rf_libdoc.py"),
    ...
}
```

The server constructs paths like `plugins/rf-agentskills/skills/robotframework-libdoc-search/scripts/rf_libdoc.py` but:
- Plugin skills use **short names**: `skills/libdoc-search/` (not `robotframework-libdoc-search/`)
- Plugin skills have **no `scripts/` subdirectories** - scripts are in `plugins/rf-agentskills/scripts/`

**Impact:** The MCP server will fail with `ImportError` / `FileNotFoundError` for every tool call.
**Fix:** `os.path.join(_PLUGIN_ROOT, "scripts", "rf_libdoc.py")`

### 4.2 CRITICAL: `sys.exit(1)` in `rf_results.py` Will Crash MCP Server

**File:** `plugins/rf-agentskills/scripts/rf_results.py:138` (and root copy)

```python
def _load_result(paths, merge, name):
    if len(paths) == 1:
        try:
            return ExecutionResult(paths[0]), False
        except Exception as e:
            json.dump({"error": f"Failed to parse output file: {e}"}, sys.stdout, indent=2)
            sys.exit(1)  # ← KILLS THE MCP SERVER PROCESS
```

`SystemExit` is a subclass of `BaseException`, NOT `Exception`. The MCP server's `try/except Exception` handler will NOT catch this. A parse failure on any output file will **terminate the entire MCP server process**.

**Fix:** Raise an exception instead of `sys.exit()`, or catch `SystemExit` in the MCP server.

### 4.3 CRITICAL: Double-Nested VS Code Extension Skills

```
vscode-extension/skills/
  robotframework-keyword-builder/   ← Copy 1
  ...
  skills/                           ← DUPLICATE DIRECTORY
    robotframework-keyword-builder/ ← Copy 2 (of the same skill!)
    ...
```

The `vscode-extension/skills/skills/` directory is a **complete duplicate** of `vscode-extension/skills/`, adding 148 unnecessary files. Likely a build script bug that copied skills into a `skills/` subdirectory inside the already-correct `skills/` directory.

### 4.4 HIGH: `rf_libdoc.py` Duplicated Within Root Skills

The same `rf_libdoc.py` script exists in:
- `skills/robotframework-libdoc-search/scripts/rf_libdoc.py`
- `skills/robotframework-libdoc-explain/scripts/rf_libdoc.py`

These two skills share the same script but each has its own copy. They should either:
- Share one canonical copy via symlink or build step, OR
- Be merged into a single skill with both capabilities (search + explain)

### 4.5 HIGH: Root Scripts Missing Graceful Import Handling

The plugin copies of `rf_libdoc.py` and `rf_results.py` have `try/except ImportError` guards. The root copies lack this, causing unhelpful tracebacks when `robotframework` is not installed.

Note: The plugin copies also have a redundant `import sys` inside the `except` block (sys is already imported at the top of the file).

### 4.6 HIGH: Agent Markdown Files Reference Broken Script Paths

All four agents (`rf-debug-expert.md`, `rf-keyword-consultant.md`, `rf-migration-guide.md`, `rf-test-architect.md`) use bare `python scripts/rf_results.py` and `python scripts/rf_libdoc.py` paths. These will fail when CWD is the user's project root (the common case). The SKILL.md files correctly use `${CLAUDE_PLUGIN_ROOT}`, but the agents don't.

### 4.7 MEDIUM: `_find_keyword` Indentation Bug

**File:** `plugins/rf-agentskills/scripts/rf_libdoc.py:228-230` (and root copy)

```python
matches.append({
    "library": _library_meta(lib),
    "keyword": _keyword_to_dict(kw),
"usage": _parse_keyword_args(...),  # ← under-indented (12 vs 20 spaces)
})
```

Not a runtime bug (Python allows it), but a readability issue that suggests copy-paste error.

### 4.8 MEDIUM: Unused Import in Root `testcase_builder.py`

`skills/robotframework-testcase-builder/scripts/testcase_builder.py` has `import re` on line 4 that is never used. The plugin copy correctly removed it.

### 4.9 MEDIUM: `_read_input()` and `_render_step()` Duplicated

- `_read_input()` is identical in `keyword_builder.py`, `testcase_builder.py`, `resource_architect.py` (3 scripts x 4+ copies = 12+ copies)
- `_render_step()` is identical in `keyword_builder.py` and `testcase_builder.py` (2 scripts x 4+ copies = 8+ copies)

---

## 5. Skill Design Issues

### 5.1 Hook Token Efficiency

**File:** `plugins/rf-agentskills/hooks/hooks.json` - `UserPromptSubmit` hook

The hook injects a ~1200-token prompt listing ALL 11 skills and 4 agents on every single user message, regardless of whether the message is RF-related. This contradicts Anthropic's guidance:

> "The context window is a public good... Only add context Claude doesn't already have."

**Fix:** Either use a more selective matcher (e.g., `robot|rf|test|automation|keyword|browser|selenium`) or condense to a minimal routing prompt.

### 5.2 Stop Hook References Bare Script Path

The `Stop` hook prompt tells users to run `python scripts/rf_results.py --output results/output.xml ...` which is a bare relative path. Should use `${CLAUDE_PLUGIN_ROOT}/scripts/rf_results.py` for consistency (though per Issue #9354, this won't expand in prompt text either -- the hook should construct the actual path).

### 5.3 `libdoc-search` and `libdoc-explain` Should Be Merged

These two skills use the **exact same script** (`rf_libdoc.py`) with different flags:
- `libdoc-search`: `--search "query"`
- `libdoc-explain`: `--keyword "name"`

They could be a single skill `robotframework-libdoc` with both capabilities documented in one SKILL.md, eliminating a script copy and reducing discovery confusion.

### 5.4 Library Skills Don't Cross-Reference Script Skills

The 5 library-reference skills (Browser, Selenium, Appium, Requests, RESTinstance) don't mention the complementary script-based skills (keyword-builder, testcase-builder, etc.). Adding cross-references would improve agent skill composition.

### 5.5 Naming Inconsistency Across Channels

Root uses long names (`robotframework-keyword-builder`), plugin uses short names (`keyword-builder`). The same skill has a different identity depending on distribution channel. Should be standardized.

Anthropic recommends **gerund form** (e.g., `building-keywords`), **third-person descriptions**, and **max 64 chars** for names.

---

## 6. MCP Server Design Issues

### 6.1 Module Reloading on Every Call

Every tool call re-executes `_load_module()`, which imports the module from disk, re-runs `re.compile()` calls, and for `rf_libdoc.py`, triggers the heavy `from robot import libdoc` import.

**Fix:** Cache modules in a dict, load each once on first use.

### 6.2 `sys.argv` Monkeypatching + stdout Capture

Three tool functions (`tool_keyword_builder`, `tool_testcase_builder`, `tool_resource_architect`) use fragile `sys.argv` manipulation and `sys.stdout` capture. This is not thread-safe and will break under concurrent MCP requests.

Note: `tool_libdoc_search` and `tool_libdoc_explain` already call internal functions directly (the correct approach). The other 3 tools should be refactored to match.

**Fix:** Refactor builder scripts to expose a `build(data: dict) -> dict` function separate from the CLI `main()`, and call that directly.

### 6.3 `LibraryDocumentation` Not Cached

`tool_libdoc_search` and `tool_libdoc_explain` both instantiate `LibraryDocumentation` objects on every call. For standard libraries (`BuiltIn`, `Collections`, `String`), these are expensive to construct. An LRU cache keyed by library name would speed up repeated searches.

---

## 7. Test Coverage Gaps

Current tests: 21 passing (7 keyword_builder, 6 libdoc_search, 8 marketplace_validation)

**Note:** Existing tests point to the **plugin** copies as the working version:
```python
SCRIPT = ... / "plugins" / "rf-agentskills" / "scripts" / "keyword_builder.py"
```
This confirms the plugin scripts are treated as canonical at runtime, even though the root `skills/` directory is the intended source of truth.

**Missing test coverage:**
- `testcase_builder.py` - 0 tests (previously existed per memory, now deleted)
- `resource_architect.py` - 0 tests (previously existed per memory, now deleted)
- `rf_results.py` - 0 tests (previously existed per memory, now deleted)
- MCP server `rf-tools-server.py` - 0 tests (would have caught the broken `_SCRIPT_PATHS`)
- Script drift detection (root vs plugin) - 0 tests
- Hook behavior - 0 tests
- `sys.exit` vs `SystemExit` in MCP context - 0 tests

**Additional note:** The entire `vscode-extension/` directory is **untracked in git** (shown as `??` in git status). This means 136+ files including TypeScript source, package.json, built VSIX, and all skill copies are not version-controlled. If someone runs `git add vscode-extension/`, the 148-file double-nested duplicate would also be committed.

---

## 8. Recommended Architecture

### 8.1 Single Source of Truth

```
skills/                                    ← CANONICAL (one truth)
  robotframework-keyword-builder/
    scripts/
      keyword_builder.py                   ← Authoritative copy
    SKILL.md                               ← Authoritative, uses relative paths
  robotframework-libdoc/                   ← MERGED search + explain
    scripts/
      rf_libdoc.py                         ← Single copy (not duplicated)
    SKILL.md                               ← Covers both search and explain
  robotframework-browser-skill/
    references/
      locators.md
      assertion-engine.md
      ...
    assets/examples/
    SKILL.md
  ...
```

### 8.2 Derived Distribution Channels (Build Step)

```
scripts/build-plugin.sh     ← Copies skills/ → plugins/, rewrites paths
scripts/build-vscode.sh     ← Copies skills/ → vscode-extension/skills/
scripts/sync-check.sh       ← CI job: verify derived channels match source
```

The build scripts would:
1. Copy skills from root `skills/` to each distribution channel
2. Rewrite SKILL.md paths for the target context
3. Flatten scripts into plugin's `scripts/` dir if needed for plugin system
4. Add graceful import guards to copies requiring `robotframework`
5. Rename skill names to short form for plugin channel

### 8.3 Alternative: pip-installable CLI

The most portable long-term solution: publish scripts as `robotframework-agentskills` on PyPI with CLI entry points. Then SKILL.md simply references commands in PATH:

```bash
rf-libdoc-search --library BuiltIn --search "click" --pretty
rf-keyword-builder --input keyword.json
```

No path resolution issues. Works with every agent on every platform.

### 8.4 Per-Skill Scripts Benefits for Portability

With per-skill `scripts/`, any agent can use a skill by:
1. Reading `SKILL.md` from the skill directory
2. Executing `python <skill-dir>/scripts/foo.py` with the documented args
3. No knowledge of the broader project structure needed

This works with: Claude Code, Cursor, GitHub Copilot, Goose, Gemini CLI, Amp, VS Code, Windsurf, and any future agent that follows the open skill standard.

---

## 9. Summary of Issues by Priority

| # | Priority | Issue | Section |
|---|----------|-------|---------|
| 1 | **CRITICAL** | MCP server `_SCRIPT_PATHS` point to non-existent paths | 4.1 |
| 2 | **CRITICAL** | `sys.exit(1)` in `rf_results.py` will crash MCP server (`SystemExit` is `BaseException`) | 4.2 |
| 3 | **CRITICAL** | `vscode-extension/skills/skills/` double nesting (148 duplicate files) | 4.3 |
| 4 | **HIGH** | 5 scripts x 4-7 copies with active drift | 1.2, 1.3 |
| 5 | **HIGH** | Root scripts missing graceful import guards | 4.5 |
| 6 | **HIGH** | `${CLAUDE_PLUGIN_ROOT}` not expanded in SKILL.md (Issue #9354) | 3.2 |
| 7 | **HIGH** | Agent .md files use bare script paths that won't resolve | 4.6 |
| 8 | **MEDIUM** | `UserPromptSubmit` hook injects ~1200 tokens on every message | 5.1 |
| 9 | **MEDIUM** | `libdoc-search` + `libdoc-explain` are separate skills sharing same script | 5.3 |
| 10 | **MEDIUM** | MCP server reloads modules on every call | 6.1 |
| 11 | **MEDIUM** | MCP server uses `sys.argv` + stdout monkeypatching (not thread-safe) | 6.2 |
| 12 | **MEDIUM** | 3 test files deleted; 3 scripts have 0 test coverage | 7 |
| 13 | **MEDIUM** | `_find_keyword` indentation bug in rf_libdoc.py | 4.7 |
| 14 | **LOW** | `_read_input()` + `_render_step()` duplicated across scripts | 4.9 |
| 15 | **LOW** | Library skills don't cross-reference script skills | 5.4 |
| 16 | **LOW** | Naming inconsistency across channels | 5.5 |
| 17 | **LOW** | Redundant `import sys` in plugin ImportError handlers | 4.5 |

---

## 10. Experiment Results

All 5 Python scripts were tested and work correctly:

| Script | Test Method | Result |
|--------|------------|--------|
| `keyword_builder.py` | stdin JSON pipe | Generates correct RF keyword syntax |
| `testcase_builder.py` | stdin JSON pipe | Generates correct RF test case syntax |
| `resource_architect.py` | stdin JSON pipe | Generates correct project layouts |
| `rf_libdoc.py` | `--library BuiltIn --search` | Searches RF 7.4.2 successfully |
| `rf_results.py` | `--output output.xml --sections` | Parses real output.xml correctly |
| pytest suite | `python -m pytest tests/` | 21/21 passing |

---

## Sources

- **Anthropic Best Practices**: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- **Block Engineering Blog**: https://engineering.block.xyz/blog/3-principles-for-designing-agent-skills
- **Claude Code Skills Docs**: https://code.claude.com/docs/en/skills
- **Claude Code Plugins Reference**: https://code.claude.com/docs/en/plugins-reference
- **GitHub Issue #9354**: `${CLAUDE_PLUGIN_ROOT}` not expanded in SKILL.md
- **GitHub Issue #11011**: Relative path resolution fails on first execution
- **GitHub Issue #27145**: `CLAUDE_PLUGIN_ROOT` not set in SessionStart hooks
- **GitHub Issue #16116**: Plugin hooks fail on Windows
- **GitHub Issue #15642**: Plugin cache staleness
- **AGENTS.md Standard**: https://agents.md/
- **SkillKit**: https://github.com/rohitg00/skillkit
- **Mikhail Shilkov Analysis**: https://mikhail.io/2025/10/claude-code-skills/

*Report generated from project analysis, 5 concurrent research agents, hands-on experiments with all scripts, and review of Anthropic/Block best practices.*
