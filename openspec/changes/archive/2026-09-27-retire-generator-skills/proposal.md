## Why

The three generator skills (`rf-keyword-builder`, `rf-testcase-builder`, `rf-resource-architect`) make the model write JSON, run a script, read JSON back and paste the `artifact` into a `.robot` file. That round trip costs more tokens and turns than the model writing Robot Framework directly, and the scripts lag the language: no RF 7 typed `[Arguments]`, a keyword-builder example that mixes Browser and SeleniumLibrary keywords, and a resource layout generator whose non-default modes are unimplemented. Skills that only close a capability gap lose value as models improve. The user has decided to retire all three from every channel now, before the replacement guidance skills are designed, so that the catalog stops recommending them.

## What Changes

- **BREAKING** Remove the skills `rf-keyword-builder`, `rf-testcase-builder`, `rf-resource-architect` from the root `skills/`, the Claude Code plugin (`plugins/rf-agentskills/skills/{keyword-builder,testcase-builder,resource-architect}`), the VS Code extension (`vscode-extension/skills/rf-*` and `package.json` `chatSkills`), and the installer's bundled assets.
- **BREAKING** Remove the scripts `keyword_builder.py`, `testcase_builder.py`, `resource_architect.py` (root, plugin `scripts/`, installer `_assets/`) and the MCP tools `rf_keyword_builder`, `rf_testcase_builder`, `rf_resource_architect` from `rf-tools-server.py`.
- Remove every reference to the retired skills: Companion Skills tables in the library skills, `rf-robotcode` and `rf-setup` (incl. `references/project-layout.md`); the subagents `rf-test-architect`, `rf-keyword-consultant`, `rf-migration-guide` (rewrite their workflow steps so the agent writes RF directly and verifies with libdoc / `robot --dryrun`); the context-injection hook text and its README; README, marketplace/plugin/extension descriptions; docs that describe current behaviour (installer docker checks, CI usage).
- Remove the eval tasks `narrow-keyword-builder-01`, `narrow-testcase-builder-01`, `narrow-resource-architect-01`; re-home `narrow-rf-mcp-execute-01` (its `skill:` field) and point `scripts/eval-smoke.sh` at a surviving task; update eval unit-test fixtures that use `keyword-builder` as a sample skill name.
- Remove `tests/test_keyword_builder.py`, `tests/test_testcase_builder.py`, `tests/test_resource_architect.py`; update `tests/test_drift_detection.py`, `tests/test_hook_scripts.py`.
- Harden distribution so a removed skill cannot linger: `scripts/sync-skills.sh` prunes plugin skill dirs and plugin scripts that have no root source, and `scripts/check-drift.sh` fails on such orphans.
- Installer upgrade path: re-installing over an older install removes previously installed files the new bundle no longer ships (hash-checked, user-modified files kept and reported), so old copies of the retired skills do not stay behind untracked.
- Record logic worth keeping (embedded-argument convention detection, control-structures-in-tests warning, keyword naming/RETURN/typed-arg notes) in `design.md` as input for the future guidance skills.
- Content channel version bump to **2.0.0** with CHANGELOG entries (content + installer); installer minor bump for the prune-on-reinstall behaviour.

Out of scope: the replacement guidance skills (test-writing styles, keyword design, Python library creation). They are proposed as follow-up changes: `add-rf-language-skill` (`rf-language`) and `add-rf-python-library-skill` (`rf-python-library`). Historical documents (`docs/*-plan.md`, reports, archived OpenSpec changes, `eval/runs/`) are not rewritten.

## Capabilities

### New Capabilities
- `skill-catalog`: which skills, scripts and MCP tools the project ships, the rule that a retired skill is gone from every channel with no dangling references, sync/drift enforcement against orphaned copies, and release notes/versioning for removals.

### Modified Capabilities
- `rf-script-output`: remove the requirement "testcase_builder can emit a runnable suite" (the script no longer exists).
- `installer-uninstall-safety`: add a requirement that re-install removes files from the previous install that the current bundle no longer ships, with the same hash-based safety as uninstall.

## Impact

- Deleted: `skills/robotframework-{keyword-builder,testcase-builder,resource-architect}/`, their plugin and VS Code copies, `plugins/rf-agentskills/scripts/{keyword_builder,testcase_builder,resource_architect}.py`, three eval tasks, three test files.
- Edited: `plugins/rf-agentskills/servers/rf-tools-server.py`, `plugins/rf-agentskills/agents/{rf-test-architect,rf-keyword-consultant,rf-migration-guide}.md`, `plugins/rf-agentskills/scripts/maybe_inject_rf_context.mjs`, `plugins/rf-agentskills/hooks/README.md`, 7 library/tool `SKILL.md` companion tables, `skills/robotframework-setup-skill/references/project-layout.md`, `scripts/sync-skills.sh`, `scripts/check-drift.sh`, `scripts/eval-smoke.sh`, `installer/src/rf_agentskills/cli.py` (+ manifest helpers), `vscode-extension/package.json`, `.claude-plugin/marketplace.json`, `plugins/rf-agentskills/.claude-plugin/plugin.json`, `README.md`, `docs/ci/usage.md`, `docs/installer/docker/checks/*.sh`, `eval/tasks/README.md`, `eval/fixtures/sut-minimal/` comments, tests listed above, CHANGELOGs.
- API: three MCP tools disappear from `rf-tools`; slash commands `/rf-agentskills:keyword-builder|testcase-builder|resource-architect` stop existing.
- Coordination: `merge-libdoc-skills` touches the same companion tables, hook text, sync map and installer prune path; land this change first (it introduces the prune behaviour) or together in one 2.0.0 release.
