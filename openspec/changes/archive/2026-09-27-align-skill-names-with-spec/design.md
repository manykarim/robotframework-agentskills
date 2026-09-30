## Context

See proposal.md (Why). The current state that shapes this design:

- **Three spellings for each skill.** The root dir is `skills/robotframework-browser-skill/` with `name: rf-browser`. The plugin dir is `plugins/rf-agentskills/skills/browser/`, where `sync-skills.sh` rewrites `name:` to `browser` and rewrites backticked `rf-*` names in companion tables to short names. The VS Code dir is `vscode-extension/skills/rf-browser/` (already conformant). The plugin subagents (`plugins/rf-agentskills/agents/rf-debug-expert.md` and others) use a fourth form, `robotframework-results`, which matches no channel.
- **Installer.** `hatch_build.py` mirrors `plugins/rf-agentskills/` into `installer/src/rf_agentskills/_assets/`. Every adapter copies `_assets/skills/<dir>/` into un-namespaced skill folders: `.claude/skills/`, `~/.agents/skills/` (Codex, Goose), `.cursor/skills/`, `~/.config/opencode/skills/`. So today a user-scope install creates `~/.claude/skills/setup/` and `~/.claude/skills/results/`. `_execute_plan` upserts the manifest record with only the newly written files. Files from an earlier bundle that the new plan no longer writes drop out of the manifest, and nothing removes them. After a rename they would be orphaned.
- **CI/release.** `ci.yml` and `release.yml` build the Codex and Copilot tarballs with the glob `skills/robotframework-*/`, which matches nothing after a rename. `ci.yml` `validate-plugin` only checks that `SKILL.md` exists and has `name:` and `description:`. `scripts/validate-marketplace.py` and `tests/test_marketplace_validation.py` do the same shallow check.
- **Eval.** The `skill:` value in `eval/tasks/**/*.yaml` equals the plugin dir name. `ClaudeCodeRunner._provision_skills` copies plugin skill dirs by their dir name.
- **MCP server.** `_SCRIPT_PATHS` points at the flat `plugins/rf-agentskills/scripts/*.py`, not at skill dirs, so renaming skill dirs does not affect it.
- **Other changes this one sits between.** The retirement change (assumed name `retire-generator-skills`) deletes rf-keyword-builder, rf-testcase-builder and rf-resource-architect. `merge-libdoc-skills` replaces rf-libdoc-search and rf-libdoc-explain with `rf-libdoc`. This change covers the 10 skills left afterwards: rf-appium, rf-browser, rf-libdoc, rf-platynui, rf-requests, rf-restinstance, rf-results, rf-robotcode, rf-selenium, rf-setup.

## Goals / Non-Goals

**Goals:**
- One identifier per skill (`rf-<topic>`), equal to its directory name in every channel and every installed location.
- Deterministic, offline validation of the spec's frontmatter rules in CI and in the test suite.
- Existing installer users are migrated automatically on their next `install`.

**Non-Goals:**
- Rewriting descriptions. `sharpen-skill-descriptions` owns the `description` text. This change only checks its length and absence of tags.
- Retiring or merging skills (other changes).
- Changing the plugin name `rf-agentskills` or the subagent names.
- Moving scripts into per-skill `scripts/` inside the plugin channel. The plugin keeps its flat `scripts/` folder and the MCP server is unchanged.
- Cleaning up directories that users copied by hand. Doctor only warns about them.

## Decisions

### D1: Root directories are renamed to the `rf-*` name (not the other way round)

Options:
- (a) Rename root dirs to `rf-browser/` and so on. The frontmatter stays as it is.
- (b) Change `name:` to the long dir name (`robotframework-browser-skill`).
- (c) Keep root non-conformant and only fix the generated channels.

Chosen: **(a)**. `rf-*` names are already used in every companion table, in the VS Code channel, in the existing specs' frontmatter scenarios and in user-facing text. They are short (a 12–15 character prefix of the description budget matters less than invocation ergonomics) and carry the `rf-` prefix that prevents collisions. Option (b) would put the `-skill` suffix into every slash command and break every cross-reference. Option (c) leaves the canonical tree, which is also what the standalone tarball and `cp -r skills/<x>` users get, violating the spec.

### D2: Plugin directories are also `rf-*`, accepting `rf-agentskills:rf-browser`

Options:
- (a) Keep short plugin dirs/names (`browser`). This is already dir==name inside the plugin, and Claude Code shows `rf-agentskills:browser`.
- (b) Use `rf-browser` in the plugin as well.

Chosen: **(b)**. Option (a) looks tidier inside Claude Code, but the plugin tree is also the installer's source (`hatch_build.py`), and the installer drops it into shared, un-namespaced folders. There, `browser`, `setup` and `results` are likely to collide with other packs, and it is unclear to users which pack they came from. One identifier also lets us delete the rename logic in `sync-skills.sh`, the companion-table rewrites and the `SHORT_NAMES` table, which are sources of drift, and makes the hook text and subagent references channel-independent. The cost is the slightly redundant `/rf-agentskills:rf-browser`. The README documents it. Auto-invocation is unaffected because it goes by description.

Rejected alternative: have the installer rename short plugin dirs to `rf-*` at install time. This keeps two identifiers alive and moves the problem into five adapters.

### D3: Sync becomes copy + one path rewrite + stale-dir removal

`sync-skills.sh` iterates root `skills/*/`. For each skill:
- the plugin copy gets `SKILL.md` with only the `python scripts/x.py` → `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/x.py"` rewrite, plus `references/` and `assets/`;
- the VS Code copy is a dereferenced full copy, as today.

Afterwards it deletes any `plugins/rf-agentskills/skills/*` or `vscode-extension/skills/*` directory that has no root counterpart. This orphan pruning is introduced by `retire-generator-skills`; here it is reused, and extended with the channel-set equality check. `check-drift.sh` gets a matching check: set equality of skill dir names across the three channels, and byte-equality of `SKILL.md` for VS Code and of the transformed `SKILL.md` for the plugin. It keeps its existing script-map check, updated to the new root paths. The script list in step 1 of sync becomes a glob over `skills/*/scripts/*.py` instead of a hard-coded list. The retirement change shrinks that list anyway.

### D4: Validator is a small stdlib script; `skills-ref` is an optional cross-check

`scripts/validate-skills.py [--channel root|plugin|vscode|all]` parses the frontmatter with a minimal YAML-subset reader. Our frontmatter is flat scalars plus the one-level `metadata` map; the script falls back to PyYAML when it is importable. It checks the rules in the spec requirement "Frontmatter conforms to the agentskills.io field rules", plus `metadata.version == VERSION` and `license` present. It prints `path: rule: detail` and exits 1 on any violation.

Why not `skills-ref validate` alone: it is a reference implementation that is not guaranteed stable or on PyPI, it would add a network dependency to CI, and it does not know our cross-channel and version rules. CI runs `skills-ref validate` as a separate, non-blocking (`continue-on-error`) step when it installs, so we notice if our reading of the spec diverges from the reference.

`tests/test_skill_validation.py` runs the validator on the real tree and on tmp-dir fixtures for each failure rule. `tests/test_marketplace_validation.py::test_skill_md_frontmatter` is replaced by a call into the validator so there is one rule set.

### D5: Frontmatter additions

```yaml
---
name: rf-browser
description: …               # unchanged here; owned by sharpen-skill-descriptions
license: Apache-2.0
compatibility: Requires Python 3.10+, robotframework>=7 and robotframework-browser in the project environment; Node.js 22+ LTS only when not using the robotframework-browser[bb] batteries extra. Needs network access for rfbrowser install.
metadata:
  author: manykarim
  version: "1.2.0"
---
```

Draft `compatibility` per skill. The floors come from the setup-skill design (checked 2026-09-26) and are re-checked at implementation time:

| Skill | compatibility (draft) |
|---|---|
| rf-browser | Python 3.10+, robotframework>=7, robotframework-browser; Node.js 22+ LTS unless the [bb] batteries extra is used. |
| rf-selenium | Python 3.10+, robotframework>=7, robotframework-seleniumlibrary 6.x, a local browser (drivers via Selenium Manager) or a Selenium Grid URL. |
| rf-appium | Python 3.8+, robotframework>=7, robotframework-appiumlibrary 3.x, Appium server 2+/3 (Node.js) with UiAutomator2/XCUITest drivers, Android SDK or Xcode, a device or emulator. |
| rf-requests | Python 3.8+, robotframework>=7, robotframework-requests. |
| rf-restinstance | Python 3.11+, robotframework>=7, RESTinstance. |
| rf-platynui | Python 3.12+, robotframework>=7, PlatynUI new_core pre-release (robotframework-PlatynUI); Windows (UIA) or Linux desktop with AT-SPI2; macOS unsupported. |
| rf-robotcode | Python 3.10+, robotcode[all] 2.x installed in the project environment next to robotframework>=7. |
| rf-setup | One of uv (preferred), Python 3.10+ with venv + pip, or Poetry ≥1.8; network access to PyPI. |
| rf-libdoc | Python 3.8+ with robotframework>=7 installed in the environment that runs the bundled script; the libraries to inspect must be importable. |
| rf-results | Python 3.8+ with robotframework>=7 (for rebot/ExecutionResult) in the environment that runs the bundled script. |

`metadata.version` is the bundle content version (`VERSION`, currently 1.2.0). Skills are released as a bundle, so a per-skill version would drift and mean nothing. `scripts/bump-version.sh` rewrites the `version:` line under `metadata:` in every `skills/*/SKILL.md`, and the validator enforces equality. `allowed-tools` is not added (experimental, agent-specific).

### D6: Installer migration: prune the previous record, then warn about the unowned

> **Ownership (cross-change reconciliation):** `retire-generator-skills` (design D9) owns the prune-on-reinstall mechanism, including `--what` category scoping, and the orphan pruning in `sync-skills.sh`/`check-drift.sh`. It lands first. This change reuses both unchanged. It adds only (a) a rename-case test (old short-name dir → `rf-*` dir) and (b) the `doctor` legacy-directory hint below. The prune description that follows documents the behaviour this change relies on. It is not a second implementation.

In `_execute_plan`, before the manifest upsert, load the previous `Installation` for (agent, scope). For each `FileEntry` whose path is not among the new targets:
- if the hash still matches, delete it and call `prune_empty_parents(path, stop_at=<install root>)`;
- if the hash differs, keep it and add it to a "skipped (user-modified)" list that is printed in the summary table.

This reuses `files_to_remove` / `is_user_modified`, the uninstall rules from the `installer-uninstall-safety` spec. `--dry-run` lists the files that would be pruned.

`cmd_doctor` gains a legacy check. For each detected adapter's skill folder, it looks for directories named in a constant `LEGACY_SKILL_DIRS`:
- the 14 old plugin short names: `appium`, `browser`, `keyword-builder`, `libdoc-explain`, `libdoc-search`, `platynui`, `requests`, `resource-architect`, `restinstance`, `results`, `robotcode`, `selenium`, `setup`, `testcase-builder`;
- the 14 old root long names (`robotframework-*-skill`, `robotframework-results`, `robotframework-libdoc-*`, …).

A directory is reported only if it contains a `SKILL.md` whose frontmatter `name` is one of our old names, which avoids false positives for someone else's `browser` skill, and only if it is not in the manifest. Doctor prints the path and suggests `rm -r`. It never deletes.

Rejected alternative: have the installer delete legacy dirs by name. That violates the "removes exactly what rf-agentskills added" requirement for dirs we did not record.

### D7: Consumers updated in the same PR

| Consumer | Change |
|---|---|
| `.github/workflows/ci.yml`, `release.yml` | `skills/robotframework-*/` → `skills/rf-*/`. Add a `validate-skills` job (all channels) next to `check-drift`, plus a non-blocking `skills-ref` step. `release.yml` changelog loop unchanged (uses `basename`). Fix the hard-coded "11 skills" text to use the counted value. |
| `plugins/rf-agentskills/agents/*.md` | Replace `robotframework-*` identifiers with `rf-*`. Drop retired skills if the retirement change missed them. |
| `maybe_inject_rf_context.mjs` | List skills by `rf-*` id. The regex keeps matching the old short ids for one release (harmless) and adds `rf-libdoc`. `tests/test_hook_scripts.py` asserts the new text. |
| `eval/tasks/**/*.yaml` | `skill: browser` → `skill: rf-browser` and so on. `eval/tasks/README.md` example updated. |
| `tests/` | `SKILL_DIR` constants in the per-skill tests; `test_drift_detection.py` map; installer tests that assert `skills/browser/...` paths. |
| `README.md` | Skill table invocations (`/rf-agentskills:rf-browser`), `cp -r skills/rf-browser …`, project-structure tree, and a "Renamed in 2.0" note. |
| Existing specs | platynui-, robotcode- and setup-skill path requirements (delta specs in this change). |
| `docs/`, archived changes | Not rewritten (historical). |

### D8: Version bump

Renaming changes plugin slash-command names and installed paths. That is breaking for anyone who scripted `/rf-agentskills:browser`, so the content version is bumped to the next major (2.0.0) in plugin.json, marketplace.json, VS Code package.json and `VERSION`, and the installer gets a minor bump. The release PR decides the exact numbers per RELEASING.md.

## Risks / Trade-offs

- [Users or docs invoke `/rf-agentskills:browser`] → README and CHANGELOG list old → new names. The major version bump signals the break. Auto-triggering by description is unaffected.
- [Rename during a period when other changes are editing the same files, which leads to merge conflicts] → strict ordering (after retire + merge, before sharpen-descriptions and restructure-library-skills where possible). Use `git mv` so blame and diffs follow. The rename commit is kept separate from content edits.
- [A user's other skill pack also has an `rf-browser` directory] → unlikely, given the `rf-` prefix. The installer already refuses to overwrite unowned files without `--force`.
- [The minimal YAML reader misparses a valid but unusual frontmatter] → frontmatter style is constrained by the validator itself (flat scalars, one `metadata` map). Use PyYAML when available. Tests cover folded/quoted descriptions.
- [Pruning on upgrade deletes something the user wanted] → only hash-matching files that we recorded are deleted. Modified files are kept and reported. `--dry-run` shows the prune list.
- [Codex/Goose read `~/.agents/skills/`, which is shared with other vendors' packs] → exactly why the `rf-` identifiers are needed. No further action.

## Migration Plan

1. Land after `retire-generator-skills` and `merge-libdoc-skills` are merged.
2. One PR, several commits: (a) `git mv` of root dirs; (b) sync/drift/validator rewrite + regenerate channels; (c) consumers (CI, agents, hook, eval, tests, README); (d) frontmatter additions + bump script; (e) installer prune + doctor check + tests; (f) version bumps + CHANGELOGs.
3. Verify: `bash scripts/sync-skills.sh && bash scripts/check-drift.sh && python scripts/validate-skills.py --channel all && uv run pytest tests/ --ignore=tests/eval`. Also an installer smoke test in a tmp HOME: install the old wheel, then the new one, and assert no `skills/browser/` remains.
4. Rollback: revert the PR. Installer users who already upgraded would re-install the old names on downgrade. The prune logic in the reverted code does not exist, so the new `rf-*` dirs would linger until `uninstall`. This is acceptable and documented in the CHANGELOG.

## Open Questions

- Is `skills-ref` installable from PyPI in CI, or does it need a git URL pin? This only affects the non-blocking cross-check step.
- Should the hook regex drop the legacy short ids after one release? Decide at the next major.

## Implementation Notes (2026-09-27, adapted to the repository state after the earlier changes)

- **Preconditions met.** `retire-generator-skills` and `merge-libdoc-skills` are archived. Root has exactly 10 skills; the merged libdoc skill already lives at `skills/rf-libdoc/` (plugin short name `libdoc`), so only 9 root dirs are `git mv`'d and the plugin `libdoc` dir becomes `rf-libdoc`.
- **Versions already bumped (D8 / task 7.1).** `retire-generator-skills` set content 2.0.0 and installer 0.7.0 once for the whole unreleased cycle. This change does NOT bump again; task 7.1 is reduced to verifying the versions and `metadata.version == VERSION` (2.0.0). CHANGELOG entries go under `installer/CHANGELOG.md` "## 0.7.0 — Unreleased" and `vscode-extension/CHANGELOG.md` "## 2.0.0 (unreleased)". The D5 example `version: "1.2.0"` becomes `"2.0.0"`.
- **Pruning is reused (D3, D6).** `sync-skills.sh` already prunes orphan plugin skill dirs/scripts and regenerates `vscode-extension/skills/` from scratch; the scripts list is already derived from `skills/*/scripts/*.py`. This change only drops `SHORT_NAMES` / name rewrite / companion rewrites, keys the plugin dir on the root dir name, and makes sync fail if a root dir's `name:` differs from its dir. `check-drift.sh` no longer parses `SHORT_NAMES` (expected plugin set = root dir names) and gains per-skill content checks: plugin `SKILL.md` == transformed root, VS Code `SKILL.md` byte-equal, `references/`/`assets/` recursively equal in both channels, missing channel dirs reported. Installer prune-on-reinstall (`cli._execute_plan`, `_partition_previous`/`_remove_stale`) is reused unchanged; its tests live in `tests/installer/test_reinstall_prune.py`, so the rename-case and user-modified tests (6.1, 6.2) are added there rather than in `test_cli_install.py`.
- **CI/release globs.** CI and release packaging loops were already switched to `skills/*/` by `merge-libdoc-skills`; they are narrowed to `skills/rf-*/` as designed. `validate-plugin` also runs the validator.
- **Extra consumers not listed in D7** (all depend on dir names and are updated here): `scripts/check-skill-keywords.py` `skill_key()` (now strips `rf-` as well as the legacy prefix/suffix), `tests/test_library_install_guidance.py` (SKILL_DIRS, SETUP_SKILL_MD, plugin companion name now `rf-setup`), `tests/test_libdoc_skill.py`, `tests/test_drift_detection.py`, `docs/installer/docker/checks/*.sh` (post-install `need_file` paths/names), installer tests (`test_adapter_claude_code`, `test_assets`, `test_reinstall_prune`), eval unit tests' sample skill names (`results`/`libdoc` → `rf-results`/`rf-libdoc`), `scripts/eval-smoke.sh`, `RELEASING.md` example path, `.gitignore` comment, `README.md`. `tests/test_libdoc_search.py` no longer exists (renamed to `tests/test_rf_libdoc.py`, which only tests the flat plugin script and needs no change).
- **Validator (D4).** `scripts/validate-skills.py` is stdlib-only (PyYAML used when importable). It also checks cross-channel set equality when `--channel all` (the spec's "Same identifier in every channel") and that every name starts with `rf-`. `validate-marketplace.py` keeps its structural checks; `tests/test_marketplace_validation.py::test_skill_md_frontmatter` delegates to the validator.
- **Doctor legacy check (D6).** `LEGACY_SKILL_DIRS` holds the old plugin short names and old root long names; doctor scans each detected adapter's skill folders for both scopes it can resolve, reports unowned dirs whose SKILL.md `name:` is a legacy name (or `rf-*` name of a skill we ship, under a legacy dir), and never deletes.
- **E2E smoke (6.5).** Run against a temporary HOME using a wheel built from `git stash`-free `HEAD` (via `git worktree add` into the scratchpad) and a wheel from the working tree.
- **Legacy grep (7.3).** Allowed hits: CHANGELOGs, README rename table, `docs/`, `openspec/` (other active changes, main specs untouched until archive), the installer's `LEGACY_SKILL_DIRS` and tests that assert legacy names are absent/flagged, and the gitignored `eval/runs/` output.
- **As implemented (deviations / choices).** Doctor scans the skills folders of *all* adapters (derived from each adapter's own `plan()` for user and project scope), not only detected ones — a superset, so hand-copied folders are found even when the agent is not detected; it additionally requires the legacy `SKILL.md` to mention "robot" to avoid flagging a foreign `setup`/`browser` skill with the same `name`. The validator also enforces the `rf-` prefix (`name-prefix`) and `compatibility` presence. `check-drift.sh` diffs `references/`/`assets/` as well as `SKILL.md`; `sync-skills.sh` now also clears plugin `references/`/`assets/` when the root skill drops them, and fails fast on a root name/dir mismatch. The "release notes draft" of 7.2 is the generated body in `release.yml` (skill/agent counts now derived); the old→new table lives in `README.md` ("Renamed in 2.0") and both CHANGELOGs. Unreleased CHANGELOG entries of this cycle that named `/rf-agentskills:robotcode|setup|libdoc` were updated to the `rf-` forms. README "Versioning" was stale (1.2.0/0.4.0) and now shows 2.0.0/0.7.0. `skills-ref` is on PyPI (0.1.1, CLI `agentskills`); all 10 skills pass `agentskills validate` locally, and CI runs it non-blocking over all three channels (answers Open Question 1).
