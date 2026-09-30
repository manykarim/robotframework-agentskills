## Context

- Motivation: see `proposal.md` (Why). Requirements: `specs/skill-catalog`, `specs/installer-uninstall-safety`, `specs/rf-script-output`.
- Channels today: root `skills/<long-name>/` → `scripts/sync-skills.sh` → `plugins/rf-agentskills/skills/<short>/` + flat `plugins/rf-agentskills/scripts/*.py` → `vscode-extension/skills/rf-*` (regenerated from scratch each sync) and `vscode-extension/package.json`. The installer's `_assets/` is a gitignored mirror of the plugin tree, wiped and re-copied by `installer/hatch_build.py` at build time. Release tarballs (`release.yml`) pack `skills/` and the plugin tree.
- The plugin sync step only writes; it never deletes plugin skill dirs or scripts whose root source is gone. `check-drift.sh` only diffs a hard-coded `SCRIPT_MAP`; it does not look for orphans. Deleting a root skill therefore leaves the plugin copy behind silently.
- Installer re-install calls `Manifest.upsert`, which replaces the (agent, scope) record with only the files written this time. Files from the previous install that are not in the new plan become untracked and stay on disk forever. The same happens today for any `--what` subset re-install (a latent bug: agents/hooks written earlier drop out of the record).
- MCP server (`rf-tools-server.py`) dispatches by name with an `else: {"error": "Unknown tool"}` branch, so removing tools needs no new error path.
- Reference inventory (grep, excluding archive/runs/deps): 7 `SKILL.md` companion tables (appium, browser, platynui, requests, restinstance, selenium, robotcode) + `rf-setup` SKILL.md and `references/project-layout.md`; 3 subagents; `maybe_inject_rf_context.mjs` and `hooks/README.md`; MCP server; sync/drift/eval-smoke scripts; `vscode-extension/package.json`; README (skills table, requirements, tests, MCP tools); marketplace + plugin + extension descriptions ("keyword/test/resource generation", "11 skills"); `docs/ci/usage.md`, `docs/installer/docker/checks/{claude-code,codex,goose,opencode}.sh`; `eval/tasks/README.md`, 4 eval tasks, `eval/fixtures/sut-minimal` comments; tests (`test_keyword_builder`, `test_testcase_builder`, `test_resource_architect`, `test_drift_detection`, `test_hook_scripts`, `tests/eval/*` fixtures using `keyword-builder` as a sample skill name). Historical docs (`docs/*implementation-plan.md`, `docs/RF_AGENTSKILLS_ISSUE_REPORT.md`, `docs/skill-architecture-review.md`, `docs/e2e-test-results.md`, `docs/ci/faq.md`, `docs/ci/implementation-plan.md`, `docs/plugin/hooks-fix-proposal.md`, `docs/marketplace-implementation-plan.md`) are records, not current behaviour.

## Goals / Non-Goals

**Goals:**
- After this change, no channel ships, advertises or recommends a generator, and an installer upgrade leaves no stale generator copies.
- Removing a skill in future is a one-directory delete in `skills/` plus reference cleanup; sync/drift enforce the rest.

**Non-Goals:**
- Designing the replacement guidance skills. They are follow-up changes: `add-rf-language-skill` (skill `rf-language`: test-writing styles and keyword/resource/variable design, merged into one skill by user decision) and `add-rf-python-library-skill` (skill `rf-python-library`). This change only records candidate content for them (D7).
- Rewriting historical documents or eval run outputs.
- Changing `rf_libdoc.py`, `rf_results.py` or their MCP tools (the libdoc skill merge is `merge-libdoc-skills`).

## Decisions

### D1: Hard removal, no deprecation window
Delete the skills, scripts and MCP tools in one release instead of shipping a "deprecated" stub first. A stub skill still costs description tokens in every session and still triggers; a stub MCP tool still appears in tool lists. Users who depend on the JSON contract can pin content 1.2.0 (plugin marketplace version, `.vsix` 1.2.0, or `rf-agentskills` ≤ 0.6.0). Alternative considered: one release with `deprecated:` descriptions pointing to "write RF directly" — rejected because it keeps the cost the user wants removed and there is no programmatic consumer outside this repo that we know of.

### D2: Subagents write RF directly, verify with tools
`rf-test-architect`, `rf-keyword-consultant` and `rf-migration-guide` keep their roles. Their generator steps become: write the keyword/test/resource directly following the library skill's conventions → check keyword names and arguments with the libdoc skill (or `robotcode libdoc` when installed) → run `robot --dryrun` (the validation hooks also run on write). `rf-test-architect`'s "Design structure" step keeps the layout advice inline (resources dir, `common.resource`, per-domain resources, per-environment variables) instead of calling `resource_architect.py`. The skills table in each agent drops the three rows.

### D3: Companion tables — delete rows, no placeholder
Rows pointing to the generators are removed, not replaced with "coming soon". The future guidance skills add their own rows when they land. `rf-setup`'s "Design resource file layout" row and `project-layout.md` line are removed; `project-layout.md` already describes a layout.

### D4: Sync prunes, drift check detects orphans
`sync-skills.sh`: before copying, delete every `plugins/rf-agentskills/skills/<dir>` whose short name is not the mapping of an existing root skill, and every `plugins/rf-agentskills/scripts/*.py` that is not a non-symlink `*.py` under some root `skills/*/scripts/`. The script list becomes derived from root (`find skills/*/scripts -name '*.py' -not -type l`) instead of the hard-coded `for script in ...` list; the `.mjs` hook scripts in plugin `scripts/` are plugin-owned and are never pruned (only `*.py` is considered). `check-drift.sh`: derive `SCRIPT_MAP` the same way and add an orphan pass over plugin skill dirs, plugin `*.py` and VS Code skill dirs. Alternative: keep hard-coded lists and edit them by hand — rejected; that is exactly how orphans happen. `SHORT_NAMES` stays hand-kept (or is replaced by `align-skill-names-with-spec`; whichever lands second rebases).

### D5: Installer prunes stale files on re-install
In `_execute_plan`, before `upsert`, load the previous record for (agent, scope). Stale = previous files whose path is not a target of the new plan **and** whose category is in `opts.what`. For each stale file: skip if missing; if `is_user_modified` → report as skipped and drop from tracking; else unlink + `prune_empty_parents(stop_at=install root)`. Previous entries whose category is not in `opts.what` are carried into the new record unchanged (this also fixes the latent `--what` subset bug). Category comes from a new optional `FileEntry.category` field written from this version on; for older manifests without it, the category is derived from the path relative to the adapter's roots (`skills/`, `agents/`, `rf-agentskills-files/`, hook/MCP config files are merges, not files). `--dry-run` prints stale files as `remove` rows. Config merges are untouched by pruning (hooks/MCP entries are replaced by the existing idempotent merge).
Alternative: a hard-coded "known retired skill names" list the installer deletes — rejected: brittle, does not cover `merge-libdoc-skills` or future retirements, and could delete user-authored dirs of the same name. Manifest-driven pruning only ever touches files we recorded and whose hash still matches, so it inherits the uninstall safety rules.
Installs made before a manifest existed cannot be pruned; release notes tell those users to delete the three directories by hand.

### D6: Versioning
- Content channel: **1.2.0 → 2.0.0** (removal of skills, slash commands and MCP tools is a breaking change for anyone invoking them). `plugin.json`, `marketplace.json` (metadata + plugin entry), `vscode-extension/package.json` bump together; marketplace description drops "keyword/test/resource generation" and the stale "11 skills" count.
- Installer: **0.6.0 → 0.7.0** (new prune-on-reinstall behaviour; pre-1.0 so minor is correct per RELEASING.md) and it bundles content 2.0.0.
- If `merge-libdoc-skills` is ready, ship both in the same 2.0.0 so users take one breaking upgrade. CHANGELOG entries: `vscode-extension/CHANGELOG.md` (content) and `installer/CHANGELOG.md`.

### D7: Logic worth keeping — candidate content for the future guidance skills
Recorded here instead of keeping the scripts. Homes: every item below lands in `rf-language` (`add-rf-language-skill`): the embedded-style and resource-layout detection become its `rf_conventions` script, the test-side rules (control structures, test names, templates, fragments) its test guidance and gotchas, and the keyword rules (naming, typed arguments, `RETURN`, retry wrapper) its keyword guidance. Python library creation goes to `rf-python-library` (`add-rf-python-library-skill`).
- **Embedded-argument convention detection** (`keyword_builder._detect_embedded_style`): walk `*.robot`/`*.resource`, inside `*** Keywords ***` look at non-indented lines (keyword names) for `${`/`@{`/`&{`; if any exist, the project uses embedded-argument keywords → new keywords should follow that style. As guidance: "before adding keywords, grep the project's keyword names for `${` and match the existing style."
- **Keyword naming**: Title Case suggestion for keyword names.
- **Typed arguments**: RF ≥ 7.3 supports `${count: int}` in user-keyword `[Arguments]` (note: `${count}: int` is invalid syntax — verified on RF 7.4.2); the builder only wrote types into `[Documentation]`. Guidance should prefer native typed arguments on RF ≥ 7.3 and mention the doc fallback only for older versions.
- **RETURN**: use `RETURN` (RF 5+) with single or multiple values, not `[Return]`.
- **Retry wrapper**: "retry-aware" style wrapped one step in `Wait Until Keyword Succeeds  3x  1s`. Guidance should prefer the library's own waiting/assertion retry (e.g. Browser assertion engine, `Wait Until …` keywords) and use `Wait Until Keyword Succeeds` only for non-waiting keywords.
- **Control structures in tests** (`testcase_builder` `CONTROL_PREFIXES = FOR, IF, WHILE, TRY, EXCEPT, ELSE, END`): warn when test bodies contain control structures and move that logic into user keywords; an explicit opt-out existed (`--allow-control`) for data-driven edge cases.
- **Test names**: warn on wildcard characters (`*`, `?`) in test names (they break `--test` selection).
- **Templates**: data-driven tests via `[Template]` with data rows; `[Timeout]` per test; `[Setup]`/`[Teardown]` require a keyword name.
- **Fragment vs suite**: a section fragment must not be saved as a standalone file; always emit the section header when creating a new file.
- **Resource layout** (`resource_architect`): detect an existing resource dir (`resources`, `keywords`, `res`, default `resources`); a `common.resource` holding library imports; one `<domain>.resource` per domain importing `common.resource`; `variables/<env>.(resource|yaml|py)` per environment (YAML needs `pyyaml`); never overwrite existing files by default.

### D8: Eval assets
Delete `narrow-keyword-builder-01`, `narrow-testcase-builder-01`, `narrow-resource-architect-01`. `narrow-rf-mcp-execute-01` evaluates the external rf-mcp server, not the builder; set its `skill:` to `libdoc-search` → after `merge-libdoc-skills`, `libdoc` (it only needs some shipped skill to stage). `eval-smoke.sh` switches to `narrow-libdoc-search-01.yaml` (renamed by the merge change if it lands). Unit tests in `tests/eval/` that use `"keyword-builder"` as an arbitrary sample name are switched to `"results"` so the fixtures don't encode a retired skill. The sut-minimal fixture's duplicated setup blocks stay (useful for a future rf-language task); only comments naming the retired task change.

### D9: Coordination with sibling changes
`align-skill-names-with-spec` also proposes sync stale-dir removal (its D3) and installer prune-on-reinstall (its D6 and requirement "Installer upgrades migrate away from old skill directories"). It is ordered to land after this change, so this change owns both mechanisms: the prune requirement lives in `installer-uninstall-safety` (with the category scoping from D5, which align's version lacks), and the orphan rules live in `skill-catalog`. When align is implemented it should reuse them and keep only its own additions (rename of dirs, `doctor` legacy-dir hint). `merge-libdoc-skills` relies on the same prune to remove old `libdoc-search`/`libdoc-explain` installs.

## Risks / Trade-offs

- [Someone scripts against the generator JSON contract or MCP tools] → major version bump, CHANGELOG with migration text, older versions stay installable.
- [Quality drop: models write worse RF without the builders] → the builders added little beyond formatting; the validation hooks (`validate_robot*.mjs`) still check every written file; guidance skills follow. Before/after evals are not possible for a removed skill, which is accepted.
- [Prune deletes something a user relies on] → only manifest-recorded files with matching hashes, scoped to selected categories, with dry-run; same rules already accepted for uninstall.
- [Sync prune deletes a plugin-only file] → prune is restricted to `skills/<dir>` directories and `scripts/*.py`; plugin-owned `.mjs` scripts, `servers/`, `agents/`, `hooks/` are untouched.
- [Conflicts with `merge-libdoc-skills` / `align-skill-names-with-spec`] → all three touch companion tables, `SHORT_NAMES` and the hook text; land this first, rebase the others (see proposal Impact).

## Migration Plan

1. Implement on a branch; run sync, drift check, full pytest, installer tests.
2. Release content 2.0.0 (`v2.0.0` tag) and installer 0.7.0 (`rf-agentskills-v0.7.0`), cross-referenced per RELEASING.md.
3. Users: Claude Code plugin update and VS Code extension update replace the tree wholesale; installer users re-run `rf-agentskills install` (prunes); tarball users delete the three skill dirs by hand (release notes list them).
4. Rollback: revert the commit and release 2.0.1 restoring the skills; installer rollback is `pipx install rf-agentskills==0.6.0` + re-install.

## Implementation Notes

- **Release-cycle versioning (D6).** This change performs the single version bump for the whole unreleased cycle (the changes after it — merge-libdoc-skills … modernize-plugin-agents-and-hooks — ship in the same release and only add CHANGELOG entries): content 1.2.0 → 2.0.0 in `plugin.json`, `marketplace.json` (metadata + plugin entry), `vscode-extension/package.json`, plus the root `VERSION` file (read by `scripts/bump-version.sh`) and the `RELEASING.md` "current version" table; installer 0.6.0 → 0.7.0 in `installer/pyproject.toml` and `rf_agentskills/__init__.py`. `installer/CHANGELOG.md`'s former "## Unreleased" section became "## 0.7.0 — Unreleased" (its existing entries from earlier changes stay under it); `vscode-extension/CHANGELOG.md` got "## 2.0.0 (unreleased)". `uv.lock` records the workspace member's new version (uv updates it automatically).
- **Manifest category (D5).** No `category` field was added to `InstallTarget`; the category is derived from the destination path by `manifest.category_for_path()` (`rf-agentskills-files/…` → `support`, `.goosehints` → `hints`, nearest `skills`/`agents` component → `skills`/`agents`, Codex `hooks.json` → `hooks`, else `other`). New `FileEntry`s store it; old records without it use the same derivation (`entry_category`). One function for both cases means old and new records can never disagree, and no adapter had to change.
- **Prune scope.** A stale entry is pruned when its category is in `--what` **or** is a category the new plan writes. This covers the shared `support` tree (plugin scripts/servers/hooks, written whenever skills/hooks/mcp are selected), so a retired `scripts/*.py` is removed too. Previous config merges that were not re-performed (e.g. hooks/MCP during `--what skills`) are carried into the new record as well; before, they dropped out of it, which is the same latent bug as for files.
- **Prune stop directory.** Empty parents are pruned up to the adapter's `install_root` (exclusive). Codex and Goose put skills outside it (`~/.agents/skills`), so for those paths the walk stops at the nearest `skills` ancestor.
- **Installer tests** use neutral names (`skills/retired-generator/…`) for the planted "previous install" files instead of `keyword-builder`, so they do not depend on whether `_assets/` was rebuilt. The rebuilt `_assets/` (via `uv build installer/`) contains no generator skill or script.
- **Sync/drift.** `check-drift.sh` honours a `REPO_ROOT` env override so `tests/test_drift_detection.py` can run it against a scratch copy. It reads the expected plugin dir names from `SHORT_NAMES` in `sync-skills.sh` (one source) and expected VS Code dirs from the root `name:` fields. The sync prune runs before copying.
- **MCP test.** New `tests/test_rf_tools_server.py` lists tools and calls a retired tool through the MCP SDK request handlers (skipped when `mcp` is not installed).
- **Extra reference cleanup** not listed in the design inventory: `docs/ci/local-testing.md` (smoke task fallback), `eval/tasks/README.md` field description, `installer/README.md` (upgrade/prune note), README prerequisite text and skill counts (14 → 11), marketplace/plugin/extension descriptions (no skill count).
- **Reference scan scope (task 7.2).** Besides the exclusions in the spec, the scan skips `openspec/changes/` (active planning artifacts, including this change) and `openspec/specs/rf-script-output/spec.md` (its testcase_builder requirement is removed by this change's delta at archive time), and the CHANGELOG entries that describe the removal.
