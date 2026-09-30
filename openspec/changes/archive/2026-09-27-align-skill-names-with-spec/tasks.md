## 0. Preconditions

- [x] 0.1 Confirm `retire-generator-skills` and `merge-libdoc-skills` are merged. Verify: `ls skills/` lists exactly the 10 remaining skills (appium, browser, libdoc, platynui, requests, restinstance, results, robotcode, selenium, setup variants) and no keyword-builder/testcase-builder/resource-architect/libdoc-search/libdoc-explain directories

## 1. Validator first (red)

- [x] 1.1 Create `scripts/validate-skills.py` (stdlib-only, optional PyYAML) implementing the name/dir, charset/length, description ≤1024, compatibility ≤500, no-XML-tag, allowed-keys, metadata-map, `license` present and `metadata.version == VERSION` rules for `--channel root|plugin|vscode|all`. Verify: `python scripts/validate-skills.py --help` works and running it on the current tree fails with dir-mismatch errors for root and missing-field errors
- [x] 1.2 Add `tests/test_skill_validation.py`: tmp-dir fixtures for one valid skill and each failure rule (bad charset, double hyphen, >64 chars, dir mismatch, long description, long compatibility, `<tag>` in description, unknown key, non-string metadata, version mismatch), plus a test that runs the validator on the real tree for all channels. Verify: the fixture tests pass and the real-tree test fails until group 2–4 are done
- [x] 1.3 Make `tests/test_marketplace_validation.py::test_skill_md_frontmatter` delegate to the validator instead of its own shallow check. Verify: `uv run pytest tests/test_marketplace_validation.py` runs the shared rules

## 2. Rename root skills

- [x] 2.1 `git mv` each remaining root skill dir to its `name:` (`robotframework-browser-skill`→`rf-browser`, `…-selenium-skill`→`rf-selenium`, `…-appium-skill`→`rf-appium`, `…-requests-skill`→`rf-requests`, `…-restinstance-skill`→`rf-restinstance`, `…-platynui-skill`→`rf-platynui`, `…-robotcode-skill`→`rf-robotcode`, `…-setup-skill`→`rf-setup`, `robotframework-results`→`rf-results`, and the merged libdoc skill → `rf-libdoc` if it is not already there). Verify: `python scripts/validate-skills.py --channel root` reports no name/dir mismatch
- [x] 2.2 Fix intra-skill relative links and symlinks broken by the move (search `skills/` for `robotframework-`). Verify: `grep -rn "robotframework-[a-z-]*-skill\|robotframework-results\|robotframework-libdoc" skills/` returns nothing, and `find skills -xtype l` returns nothing

## 3. Sync and drift tooling

- [x] 3.1 Rewrite `scripts/sync-skills.sh` per design D3: drop `SHORT_NAMES`, the `name:` rewrite and the companion-table rewrites; copy the plugin skills to `plugins/rf-agentskills/skills/<name>/` with only the script-path rewrite; glob scripts from `skills/*/scripts/*.py`; delete channel skill dirs that have no root counterpart; keep the VS Code `package.json` `chatSkills` regeneration. Verify: after running it, `ls plugins/rf-agentskills/skills vscode-extension/skills` both show exactly the root `rf-*` set and no short-name dirs
- [x] 3.2 Update `scripts/check-drift.sh`: new root script paths, set-equality of skill dirs across the three channels, byte-equality for VS Code `SKILL.md`, transformed-equality for plugin `SKILL.md`; fail and name orphaned dirs. Verify: `bash scripts/check-drift.sh` passes after sync, and fails when a dummy `plugins/rf-agentskills/skills/rf-orphan/` is created (remove it afterwards)
- [x] 3.3 Update `tests/test_drift_detection.py` to the new paths and add the orphan-dir case. Verify: `uv run pytest tests/test_drift_detection.py` passes
- [x] 3.4 Run sync and keep (uncommitted; the release PR commits) the regenerated `plugins/rf-agentskills/skills/`, `vscode-extension/skills/` and `vscode-extension/package.json`. Verify: `python scripts/validate-skills.py --channel all` reports only the not-yet-added `license`/`compatibility`/`metadata` findings

## 4. Frontmatter additions

- [x] 4.1 Add `license: Apache-2.0`, `compatibility` (re-check the floors in design D5 against PyPI/npm on the day, keep each ≤500 chars) and `metadata: {author: manykarim, version: "<VERSION>"}` to all 10 root `SKILL.md` files. Verify: `python scripts/validate-skills.py --channel root` passes
- [x] 4.2 Extend `scripts/bump-version.sh` to rewrite `metadata.version` in every `skills/*/SKILL.md`. Also fix its stale `marketplace.json` path to `.claude-plugin/marketplace.json` if it still points at the root. Verify: running it in a scratch copy for `patch` updates `VERSION` and all 10 `SKILL.md` versions, and the validator passes
- [x] 4.3 Re-run sync. Verify: `python scripts/validate-skills.py --channel all` and `bash scripts/check-drift.sh` both pass

## 5. Consumers

- [x] 5.1 `.github/workflows/ci.yml`: replace the `skills/robotframework-*/` globs with `skills/rf-*/` in the Codex/Copilot packaging; add a `validate-skills` job running `python scripts/validate-skills.py --channel all`; add a non-blocking (`continue-on-error: true`) step that installs and runs `skills-ref validate` on each root skill. Verify: `act`/workflow lint or a push to a branch shows the job green, and the packaged tarball lists `rf-*` dirs
- [x] 5.2 `.github/workflows/release.yml`: same glob fix; derive the skill count in the release notes table from the directory count instead of the hard-coded "11". Verify: the workflow YAML parses and a dry reading of the packaging steps yields `rf-*` dirs
- [x] 5.3 `plugins/rf-agentskills/agents/*.md`: replace every `robotframework-*` skill identifier with its `rf-*` id and remove references to retired skills. Verify: `grep -rn "robotframework-[a-z]*-skill\|robotframework-results\|robotframework-libdoc" plugins/rf-agentskills/agents` returns nothing
- [x] 5.4 `plugins/rf-agentskills/scripts/maybe_inject_rf_context.mjs`: list skills by `rf-*` id; add `rf-libdoc` to the regex (keep the legacy short ids matching). Update `tests/test_hook_scripts.py` expectations. Verify: `uv run pytest tests/test_hook_scripts.py` passes
- [x] 5.5 `eval/tasks/**/*.yaml` `skill:` fields and `eval/tasks/README.md` → `rf-*` ids. Verify: `rf-skill-eval` task loading (`uv run pytest tests/eval -k task` or `uv run rf-skill-eval doctor`) accepts all tasks, and `grep -rn "^skill: [a-z]" eval/tasks | grep -v "skill: rf-"` returns nothing
- [x] 5.6 Per-skill tests (`tests/test_setup_skill.py`, `test_robotcode_skill.py`, `test_platynui_skill.py`, `test_rf_results.py`, `test_libdoc_search.py` or its merged successor): update `SKILL_DIR`/paths and plugin-name assertions (`name: rf-setup` in the plugin copy). Verify: `uv run pytest tests/ --ignore=tests/eval --ignore=tests/installer` passes
- [x] 5.7 README: skill table invocations `/rf-agentskills:rf-*`, `cp -r skills/rf-browser …`, project-structure tree, and an old→new name table. Verify: `grep -n "robotframework-[a-z]*-skill\|rf-agentskills:[a-z]" README.md` shows only `rf-agentskills:rf-` forms and the rename table

- [x] 5.8 Other dir-name consumers found during adaptation: `scripts/check-skill-keywords.py` `skill_key()`, `tests/test_library_install_guidance.py`, `tests/test_libdoc_skill.py`, `docs/installer/docker/checks/*.sh`, eval unit-test sample names and `scripts/eval-smoke.sh`, `RELEASING.md`, `.gitignore` comment. Verify: `uv run python scripts/check-skill-keywords.py --require-all` (root and plugin) checks all 6 library skills, and the legacy grep of 7.3 has no hits in these files

## 6. Installer migration

- [x] 6.1 Confirm the prune-on-reinstall from `retire-generator-skills` (its design D9) is present in `installer/src/rf_agentskills/cli.py` `_execute_plan`, and reuse it as is. Do not re-implement it; if it is missing, stop and land that change first. Add the rename-case coverage. Verify: new test in `tests/installer/test_reinstall_prune.py` (where the prune tests live) installs a fake old bundle with `skills/browser/SKILL.md`, re-installs with `skills/rf-browser/SKILL.md`, and asserts the old dir is gone and the manifest lists only new files
- [x] 6.2 Add the user-modified case. Verify: a test edits the old `SKILL.md` before the upgrade and asserts the file survives and is reported as skipped
- [x] 6.3 Add the `LEGACY_SKILL_DIRS` constant and a doctor check that warns about unowned legacy dirs whose `SKILL.md` `name` is a known old name. Verify: a doctor test with an unowned `.claude/skills/robotframework-browser-skill/SKILL.md` prints a warning and leaves the dir, and an unrelated `.claude/skills/browser/` with a foreign `name:` produces no warning
- [x] 6.4 Update installer tests that assert short-name skill paths (`tests/installer/test_adapter_claude_code.py` and others). Verify: `uv run pytest tests/installer` passes
- [x] 6.5 End-to-end upgrade smoke test in a temporary HOME: build the current wheel from `main` (old names) and install it with `--scope user`, then build and install this branch's wheel. Verify: no `~/.claude/skills/{browser,setup,results,…}` remain, all `~/.claude/skills/rf-*` exist, and `rf-agentskills uninstall --agent claude-code --scope user` then leaves no rf-agentskills files

## 7. Specs, versions and changelogs

- [x] 7.1 Confirm the content version is already at the next major (2.0.0, set once for this release cycle by `retire-generator-skills`) in `VERSION`, `plugins/rf-agentskills/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` and `vscode-extension/package.json`, and the installer at its next minor (0.7.0); do not bump again. Verify: `rf-agentskills version` shows the new bundled content version, and the validator passes (metadata.version)
- [x] 7.2 Add CHANGELOG entries (`installer/CHANGELOG.md`, `vscode-extension/CHANGELOG.md`, release notes draft) with the old→new name table, the plugin slash-command change and the manual-copy cleanup hint. Verify: the entries exist and name every renamed skill
- [x] 7.3 Final gate: `bash scripts/sync-skills.sh && bash scripts/check-drift.sh && python scripts/validate-skills.py --channel all && uv run pytest tests/ --ignore=tests/eval`, plus a repository-wide legacy-identifier grep (excluding CHANGELOGs, `docs/`, `openspec/changes/archive/` and `LEGACY_SKILL_DIRS`). Verify: all commands succeed and the grep is empty
