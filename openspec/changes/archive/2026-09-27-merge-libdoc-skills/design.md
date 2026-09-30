## Context

- Motivation: see `proposal.md`. Requirements: `specs/libdoc-skill`, `specs/robotcode-skill`, `specs/rf-script-output`.
- Today: `skills/robotframework-libdoc-search/` holds `rf_libdoc.py` (regular file); `skills/robotframework-libdoc-explain/scripts/rf_libdoc.py` is a relative symlink to it. `sync-skills.sh` copies the non-symlink into the flat plugin `scripts/`, and `cp -r` into `vscode-extension/skills/` dereferences it into two regular copies. The release workflow's `cp -r skills/robotframework-*/` keeps the symlink in the Codex/Copilot/standalone tarballs.
- The script already supports four modes with one schema (`list` with no query, `search`, `explain`, `fallback`), verified with `rf_libdoc.py --library String` → `mode: "list"`. The two SKILL.md files differ only in examples and one intro line.
- MCP server: `rf_libdoc_search` and `rf_libdoc_explain` both load the same module; their schemas differ (search requires `search`, explain requires `keyword`, optional `search_fallback`).
- Sibling changes: `retire-generator-skills` (lands first; adds sync orphan pruning, drift orphan check and installer prune-on-reinstall), `align-skill-names-with-spec` (lands after; renames every root dir to `skills/rf-<topic>/`, plugin dirs to `rf-<topic>`, drops `SHORT_NAMES`), `harden-skill-script-execution` (script invocation form), `restructure-library-skills` and `sharpen-skill-descriptions` (assume `rf-libdoc`), `strengthen-skill-eval-harness` (task `skill:` validation).

## Goals / Non-Goals

**Goals:**
- One skill, one description, one script file per channel, zero symlinks.
- No behaviour change for anyone calling the script or the MCP tools.

**Non-Goals:**
- Changing `rf_libdoc.py` flags, ranking or schema.
- Choosing how scripts are run (`python` vs `uv run` vs `${CLAUDE_SKILL_DIR}`); that is `harden-skill-script-execution`.
- Final description wording and trigger evals (`sharpen-skill-descriptions`, `strengthen-skill-eval-harness`).

## Decisions

### D1: Name `rf-libdoc`, root dir `skills/rf-libdoc/` now
Create the merged skill directly at `skills/rf-libdoc/` rather than `skills/robotframework-libdoc/`, so `align-skill-names-with-spec` does not have to rename it again (its proposal already expects this). Until align lands, `SHORT_NAMES` gets `["rf-libdoc"]="libdoc"`, so the plugin copy is `plugins/rf-agentskills/skills/libdoc/` with `name: libdoc` and the slash command is `/rf-agentskills:libdoc`; VS Code gets `rf-libdoc` (it already uses the `name:` as dir). The sync sed rules `rf-libdoc-search`/`rf-libdoc-explain` → short are replaced by one `` `rf-libdoc` `` → `` `libdoc` `` rule, ordered so it cannot partially match other names. Alternatives: `rf-keyword-docs` / `rf-keywords` — rejected; "libdoc" is the RF term users and the hook regex already use.

### D2: `git mv` the real script, delete the symlink skill
`git mv skills/robotframework-libdoc-search/scripts/rf_libdoc.py skills/rf-libdoc/scripts/rf_libdoc.py` keeps history. The explain skill dir (with its symlink) is deleted. `check-drift.sh` gains a "no symlinks under `skills/`, plugin `skills/`/`scripts/`, `vscode-extension/skills/`" check, and its `SCRIPT_MAP` (derived from root per `retire-generator-skills` D4) picks up the new path automatically.

### D3: Keep both MCP tool names, no aliases
The MCP tools are operations with different required inputs, not skill names, so the merge has nothing to rename. Keeping them avoids breaking MCP clients and eval graders (`input_pattern` on `rf_libdoc`). Alternative: merge into one `rf_libdoc` tool with optional `keyword`/`search` — rejected: a breaking API change for no token saving (tool schemas are small) and it would need aliases for a release. Only docstrings that mention the old skill names change.

### D4: SKILL.md shape
Short router (target ≤ 80 lines): frontmatter; one-line boundary with `rf-robotcode` (check `robotcode --version` once; if present prefer `robotcode libdoc <Lib> list/show` or REPL `.kw`); a "which command" table (find keywords for a task → `--search`; how to call keyword X → `--keyword`; unsure of exact name → `--keyword` + `--search`; what does library X offer → no query + `--limit`); sources (`--library/--resource/--suite/--spec`, repeatable); the output contract once (from the current explain SKILL.md, the more complete of the two); filters. Draft description (≤ 1024 chars, `sharpen-skill-descriptions` may refine):
"Finds Robot Framework keywords for a task and explains a keyword's arguments, types and defaults from libdoc of libraries, resource files and suites, returning stable JSON. Use when choosing which keyword to call, checking a keyword's signature before writing it, or searching several libraries at once. If robotcode is installed, `robotcode libdoc` (rf-robotcode) is usually quicker."
Commands keep the current `python scripts/rf_libdoc.py` form so `harden-skill-script-execution` rewrites all scripts in one place.

### D5: Reference updates
- Companion tables (appium, browser, platynui, requests, restinstance, selenium): two rows → "Search keywords / explain keyword arguments | `rf-libdoc`". `rf-robotcode` table: two rows → one row with both robotcode commands in the "With robotcode" column and `rf-libdoc` in the fallback column.
- Subagents (`rf-debug-expert`, `rf-keyword-consultant`, `rf-migration-guide`, `rf-test-architect`) currently say `robotframework-libdoc-search` / `-explain`, a spelling that exists in no channel; they become `rf-libdoc` (align later canonicalises all agent references). MCP tool mentions (`rf_libdoc_search`, `rf_libdoc_explain`) stay.
- Hook: injected text "Script-based tools: libdoc, results" and "Prefer the libdoc skill (or `robotcode libdoc` …)"; regex drops `libdoc-search|libdoc-explain` and keeps `\blibdoc\b`, which already matches `rf-libdoc`/`libdoc`. Old names are dropped from the regex (they no longer exist; `libdoc` still matches prompts containing them because `\blibdoc\b` matches inside `libdoc-search`).
- Eval: keep task ids (`narrow-libdoc-search-01`, `-02-no-mcp`) so run history stays comparable; change `skill:` to the plugin name (`libdoc`, later `rf-libdoc`) and grader `input_pattern`s from `(rf_libdoc|libdoc-search|libdoc-explain|…)` to `(rf_libdoc|\blibdoc\b|find_keywords|get_keyword_info)` style patterns that match the skill, the script and the MCP tools.
- Tests: `test_robotcode_skill.py` fallback/link-back lists → `rf-results`, `rf-libdoc` / `skills/rf-libdoc`; installer tests and `docker/checks/*.sh` use `libdoc` as the sample installed skill; `test_transforms.py` sample frontmatter strings updated for consistency; `test_scoring_session_based.py` patterns updated.

### D6: Migration and versioning
Plugin and VS Code updates replace the tree. Installer users: the prune-on-reinstall rule from `retire-generator-skills` removes `libdoc-search/` and `libdoc-explain/` because they are in the previous manifest record and absent from the new plan; nothing libdoc-specific is needed in the installer. Tarball users delete the folders by hand (CHANGELOG). Versioning: ship in the same content 2.0.0 as the retirement (both break slash commands). If it slips to a later release on its own, it is again a major content bump (removed slash commands), so bundling is strongly preferred.

## Risks / Trade-offs

- [Merged description triggers less often for "explain" prompts than the dedicated skill did] → description names both jobs with trigger terms; `strengthen-skill-eval-harness` adds trigger evals; the hook injection still names the skill.
- [Plugin name changes twice (`libdoc-search` → `libdoc` → `rf-libdoc`)] → ship retirement, this change and `align-skill-names-with-spec` in the same 2.0.0 if possible, so users see one rename.
- [Grader regex `\blibdoc\b` over-matches raw `python -m robot.libdoc` use] → acceptable for "used documentation tooling" checks; tasks that must tell them apart use `rf_libdoc` explicitly.
- [Symlink check fails on a developer's local symlink under `skills/`] → intended; symlinks are the defect being removed.

## Migration Plan

1. Land after `retire-generator-skills` (needs its orphan-pruning sync and installer prune).
2. `git mv` script, write `skills/rf-libdoc/SKILL.md`, delete the two old dirs, update sync map, run sync/drift, update references and tests.
3. Release with content 2.0.0; CHANGELOG notes the merge, unchanged MCP tools, manual cleanup for tarball users.
4. Rollback: revert; old plugin/VS Code dirs come back through sync; installer users re-install.

## Open Questions

- Whether `align-skill-names-with-spec` lands in the same release. It does not change this design: only the plugin short name (`libdoc` vs `rf-libdoc`) and the eval `skill:` values differ, and align already plans to update those.

## Implementation Notes

- **Reused from `retire-generator-skills`:** sync orphan pruning (deleting the two root dirs + their `SHORT_NAMES` entries was enough to drop the plugin/VS Code copies), the drift orphan check, and installer prune-on-reinstall (no installer code change; 4.3 only adds a test in `tests/installer/test_reinstall_prune.py`). Content 2.0.0 / installer 0.7.0 were already bumped; this change only adds CHANGELOG entries (installer "### Changed (BREAKING)", VS Code "2.0.0 (unreleased)") and rewrites the retirement entry's "use instead" wording from the two old names to `rf-libdoc`.
- **Release/CI packaging globs (added task 3.5a):** `.github/workflows/release.yml` and `ci.yml` copied `skills/robotframework-*/` into the Codex/Copilot tarballs; `skills/rf-libdoc/` does not match, so the loops now use `skills/*/`. Without this the merged skill would silently be missing from two channels.
- **VS Code script comparison (task 2.2):** the spec's "Copies identical" scenario requires the drift check to compare the VS Code copy too; `check-drift.sh` now diffs each root `skills/*/scripts/*.py` against `vscode-extension/skills/<name:>/scripts/` in addition to the plugin copy, and fails on any symlink under root `skills/`, plugin `skills/` + `scripts/`, and `vscode-extension/skills/`.
- **List mode and `--limit`:** `rf_libdoc.py --library String --limit 3` still returns all keywords (`--limit` applies to search only). D4's "no query + `--limit`" was therefore not used; SKILL.md shows list mode without `--limit` and documents `--limit` on search. Script behaviour is out of scope.
- **SKILL.md** is 57 lines; description 435 chars. The robotcode boundary is a blockquote before the command table (the plugin copy reads `` `robotcode` `` / `` `libdoc` `` after sync's backtick rewrites).
- **MCP server (2.4):** no docstring named the old skills; the module docstring now says both libdoc tools belong to the single libdoc skill. `tests/test_rf_tools_server.py` asserts the unchanged `required` lists.
- **Eval graders (4.1):** YAML `input_pattern`s moved to single quotes so `\b` is not a YAML escape. `narrow-libdoc-search-01` uses `(rf_libdoc|"skill": "(rf-agentskills:)?(rf-)?libdoc")` (anchored on the Skill tool's `skill` arg so raw `python -m robot.libdoc` does not count as using the skill, per the risk noted above); `narrow-non-rf-control-01` (negative) and `narrow-rf-injection-positive-01` use the broader `\blibdoc\b` form from D5. Task ids `narrow-libdoc-search-01`/`-02-no-mcp` are kept (D5), so those ids are an accepted exception to the old-name scan, as are absence assertions in tests, CHANGELOG history and dated docs under `docs/` (plans, reviews, proposals, e2e reports).
- **Test file rename:** `tests/test_libdoc_search.py` (script tests) was renamed to `tests/test_rf_libdoc.py` so the reference scan's `libdoc_search` pattern has no hit outside the exclusions.
- **Hook regex:** the skill-id group is now `\b(rf-libdoc|rf-results)\b`; the plugin name `libdoc` is caught by the existing `\blibdoc\b` tooling term. Injected lines: "Script-based tools: libdoc, results" and "Prefer the libdoc skill (or `robotcode libdoc` …)".
- **Docker checks (3.5):** there is no upgrade phase in these scripts, so `need_no_file` for `libdoc-search/` and `libdoc-explain/` was added to `--post-install` (next to the existing retired-generator assertion); `--post-uninstall` now checks `libdoc/`.
