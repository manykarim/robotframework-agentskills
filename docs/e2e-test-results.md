# E2E Test Results: Cross-Agent Skill Portability

**Date:** 2026-03-17
**Tools Tested:** Codex CLI 0.114.0, Copilot CLI 0.0.399, Claude CLI 2.1.77

---

## Summary

| Test | Codex | Copilot | Claude |
|------|-------|---------|--------|
| 1. Skill Discovery (11 skills) | PASS | PASS | PASS |
| 2. keyword_builder script | PASS | PASS | PASS |
| 3. testcase_builder script | PASS | PASS | PASS |
| 4. libdoc_search script | PASS | PASS | PASS |
| 5. rf_results script | PASS | PASS | PASS |
| 6. Browser Library reference | PASS | PASS | PASS |
| 7. Cross-skill composition | PASS (retry) | N/A | PASS |
| 8. Path resolution | N/A | PASS | PASS |

**Pass rate: 21/21 completed tests passed (100%).** Codex test 7 timed out at 120s but passed with 300s timeout on retry.

---

## Test Details

### Test 1: Skill Discovery

All three agents discovered all 11 skills from their respective skill directories:
- **Codex**: Read from `.codex/skills/` (symlinks to `skills/`)
- **Copilot**: Read from `.github/skills/` (symlinks to `skills/`)
- **Claude**: Read directly from `skills/` directory

Each correctly extracted the `name` and `description` frontmatter fields from all 11 SKILL.md files.

### Test 2: keyword_builder Script Execution

All three agents:
1. Read the SKILL.md to understand the script's JSON input format
2. Constructed valid JSON with keyword_name, arguments, and steps
3. Ran the `keyword_builder.py` script successfully
4. Produced valid Robot Framework keyword syntax

**Path resolution approaches:**
- **Codex**: `python skills/robotframework-keyword-builder/scripts/keyword_builder.py` (full relative path from project root via `.codex/skills/` symlinks)
- **Copilot**: `cd .github/skills/robotframework-keyword-builder && python scripts/keyword_builder.py` (cd into skill dir first via `.github/skills/` symlinks)
- **Claude**: `python skills/robotframework-keyword-builder/scripts/keyword_builder.py` (full relative path from project root)

### Test 3: testcase_builder Script Execution

All three agents successfully generated test cases with tags, setup/teardown, and steps. Each produced correctly formatted Robot Framework test case syntax.

### Test 4: libdoc_search Script Execution

All three agents ran the `rf_libdoc.py` script against the BuiltIn library. Results included:
- Exact matches with score 1.0
- Partial matches with token-based scores
- Library metadata (version 7.4.2)

### Test 5: rf_results Script Execution

All three agents parsed `output.xml` and correctly identified:
- 6 tests total, 2 passed, 4 failed
- Root cause: TimeoutError on SauceDemo login page
- Cascade failures in dependent tests
- Claude provided the most detailed failure analysis

### Test 6: Browser Library Reference Skill

Codex and Claude both generated correct Browser Library test files using:
- Proper `*** Settings ***` with `Library    Browser`
- Browser → Context → Page hierarchy
- Auto-waiting assertions (`Get Title contains`)
- Screenshot capture

### Test 7: Cross-Skill Composition

Claude successfully chained all three script-based skills:
1. `libdoc-search` → found `Fill Text` in Browser library (score 1.0)
2. `keyword-builder` → generated `Fill Login Form` keyword using `Fill Text`
3. `testcase-builder` → generated test case using the keyword from step 2

All scripts ran with zero warnings. The skills composed seamlessly.

### Test 8: Path Resolution

Claude resolved the correct full path from the SKILL.md's relative `scripts/keyword_builder.py` reference to `skills/robotframework-keyword-builder/scripts/keyword_builder.py` and executed successfully.

---

## Path Resolution Analysis

| Agent | Discovery Dir | Path Strategy | Success |
|-------|--------------|---------------|---------|
| **Codex** | `.codex/skills/` | Full relative path from project root | Yes |
| **Copilot** | `.github/skills/` | `cd` into skill dir, then relative `scripts/` | Yes |
| **Claude** | `skills/` | Full relative path from project root | Yes |

All three agents successfully resolved script paths. The per-skill `scripts/` subdirectory pattern works across all tested agents because:
1. Agents read SKILL.md and see `scripts/foo.py`
2. They know which directory the SKILL.md is in (from their skill discovery)
3. They construct the full path by combining skill dir + relative script path

---

## Key Findings

1. **Per-skill `scripts/` works across all three agents** - the Anthropic-recommended structure is confirmed portable
2. **Symlinks work** for Codex and Copilot skill discovery (`.codex/skills/` and `.github/skills/`)
3. **SKILL.md relative paths** are resolved correctly by all agents (via full path construction)
4. **No agent required `${CLAUDE_PLUGIN_ROOT}`** - the plugin variable is unnecessary for direct skill usage
5. **Cross-skill composition works** - agents can chain multiple skills in sequence
6. **Script JSON I/O protocol** (stdin/stdout) works identically across all agents
7. **Progressive disclosure confirmed** - agents read SKILL.md first, then execute scripts only when needed

## Recommendations

1. Keep per-skill `scripts/` as the canonical structure
2. Publish `.codex/skills/` and `.github/skills/` symlinks in the repo for out-of-box Codex/Copilot support
3. Consider adding an `AGENTS.md` at repo root for broad cross-agent compatibility
4. The MCP server remains the best approach for the Claude Code plugin channel (handles path resolution at import time)
