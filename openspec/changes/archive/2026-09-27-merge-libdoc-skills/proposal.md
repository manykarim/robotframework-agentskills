## Why

`rf-libdoc-search` and `rf-libdoc-explain` are two skills over one script (`rf_libdoc.py`): the same flags, the same stable JSON contract, only the example commands differ (`--search` vs `--keyword`, and explain already falls back to search). Two near-identical descriptions cost description tokens in every session, split triggering between two skills that answer one question ("which keyword, and how do I call it?"), and the explain skill gets its script through a symlink (`skills/robotframework-libdoc-explain/scripts/rf_libdoc.py -> ../../robotframework-libdoc-search/...`) that breaks in zip downloads, on Windows and in installers that do not preserve links. Neither description says when to use `robotcode libdoc` instead, although `rf-robotcode` covers the same lookups.

## What Changes

- **BREAKING** Replace `rf-libdoc-search` and `rf-libdoc-explain` with one skill `rf-libdoc` at `skills/rf-libdoc/` (directory == `name`, matching `align-skill-names-with-spec`). One `SKILL.md` covers both jobs — find keywords for a use case (`--search`), explain a keyword's arguments (`--keyword`, with `--search` fallback), list a library (no query) — and states the boundary: prefer `robotcode libdoc` / REPL `.kw` when `robotcode` is installed (`rf-robotcode`), use `rf-libdoc` otherwise or when a ranked multi-library search or the structured JSON contract is needed.
- Ship exactly one copy of `rf_libdoc.py` per channel as a regular file; no symlinks in any skill tree. Plugin keeps its flat `scripts/rf_libdoc.py`.
- Output contract unchanged: `rf_libdoc.py` flags and JSON schema (`openspec/specs/rf-script-output`) stay as they are; the merged `SKILL.md` documents the contract once.
- MCP server: keep the two tool names `rf_libdoc_search` and `rf_libdoc_explain` unchanged (they are operations, not skill names); no aliases are needed and no tool is renamed.
- Distribution: plugin skill `libdoc` (or `rf-libdoc` once `align-skill-names-with-spec` lands), VS Code `rf-libdoc`, `package.json` lists one libdoc skill; the old plugin/VS Code dirs are removed by sync; installer re-install removes previously installed `libdoc-search/` and `libdoc-explain/` via the prune-on-reinstall rule introduced by `retire-generator-skills`.
- Update every reference: companion tables in all skills (two rows → one `rf-libdoc` row), `rf-robotcode` fallback text, the four subagents, the context-injection hook (text and trigger regex), README, marketplace/plugin/extension descriptions, installer docker checks, eval tasks (`skill:` and grader patterns), and tests (`test_robotcode_skill.py`, installer tests, hook tests, eval scoring fixtures).
- Content CHANGELOG entry; ships in the same 2.0.0 content release as `retire-generator-skills`.

Out of scope: changing `rf_libdoc.py` behaviour or flags; how scripts are invoked (interpreter / `uv run` / `${CLAUDE_SKILL_DIR}`) — that belongs to `harden-skill-script-execution`, and this change only uses the current `python scripts/rf_libdoc.py` form so that change can rewrite it in one place; final description wording (owned by `sharpen-skill-descriptions`, which will edit the merged description).

## Capabilities

### New Capabilities
- `libdoc-skill`: one keyword-lookup skill (`rf-libdoc`) covering search, explain and list over libraries/resources/suites/specs, its boundary with `rf-robotcode`, single non-symlinked script copy, unchanged MCP tool names, and drift-free distribution with removal of the old skill names.

### Modified Capabilities
- `robotcode-skill`: requirement "rf-robotcode complements the script-based skills" now names `rf-results` and `rf-libdoc` (instead of `rf-libdoc-search` / `rf-libdoc-explain`) as the fallbacks that link back to `rf-robotcode`.
- `rf-script-output`: requirement "In-repo consumers stay consistent with the contract" now names the single `rf-libdoc` skill doc as the place the contract is documented and pins the MCP tool names.

## Impact

- New: `skills/rf-libdoc/SKILL.md`, `skills/rf-libdoc/scripts/rf_libdoc.py` (moved with `git mv` from `skills/robotframework-libdoc-search/scripts/`).
- Deleted: `skills/robotframework-libdoc-search/`, `skills/robotframework-libdoc-explain/` (incl. the symlink), plugin `skills/libdoc-search/`, `skills/libdoc-explain/`, VS Code `skills/rf-libdoc-search/`, `skills/rf-libdoc-explain/`.
- Edited: `scripts/sync-skills.sh` (name map + sed rules), `scripts/check-drift.sh` (script path; symlink check), `plugins/rf-agentskills/servers/rf-tools-server.py` (docstrings only), `plugins/rf-agentskills/agents/*.md`, `plugins/rf-agentskills/scripts/maybe_inject_rf_context.mjs`, `plugins/rf-agentskills/hooks/README.md`, companion tables in 8 skills, `vscode-extension/package.json`, `.claude-plugin/marketplace.json`, `README.md`, `docs/installer/docker/checks/*.sh`, `eval/tasks/narrow/*libdoc*`, `narrow-non-rf-control-01`, `narrow-rf-injection-positive-01`, tests (`test_robotcode_skill.py`, `test_drift_detection.py`, `test_hook_scripts.py`, `tests/installer/*`, `tests/eval/*`), CHANGELOGs.
- API: slash commands `/rf-agentskills:libdoc-search` and `/rf-agentskills:libdoc-explain` are replaced by `/rf-agentskills:libdoc` (→ `rf-libdoc` after the naming change). MCP tools unchanged.
- Order: after `retire-generator-skills` (prune + orphan sync), before `align-skill-names-with-spec`, `restructure-library-skills` and `sharpen-skill-descriptions`, which all assume the name `rf-libdoc`.
