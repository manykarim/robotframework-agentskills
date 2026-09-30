## Why

The agentskills.io spec says a skill's `name` MUST match its parent directory. VS Code documents that skills with a bad name "silently fail to load". Only one of our three channels meets this rule today. Root `skills/` uses `robotframework-browser-skill/` with `name: rf-browser`. The plugin channel uses `browser/` with a rewritten `name: browser`. Only `vscode-extension/skills/rf-*` matches. Two more problems follow from the plugin channel. The installer copies that channel's short, generic directory names (`browser`, `setup`, `results`) into shared, un-namespaced skill folders (`~/.claude/skills/`, `~/.agents/skills/`, `.cursor/skills/`), where they can collide with other skill packs. The subagent files refer to skills by a third spelling (`robotframework-results`) that exists in no channel. No skill declares its runtime needs (`compatibility`), and nothing in CI enforces the spec's frontmatter rules.

## What Changes

- **BREAKING (paths/identifiers)**: use one identifier per skill everywhere. The directory name equals the frontmatter `name`, which is `rf-<topic>`, in all three channels:
  - root `skills/robotframework-browser-skill/` → `skills/rf-browser/` (the same for every remaining skill);
  - plugin `plugins/rf-agentskills/skills/browser/` with `name: browser` → `plugins/rf-agentskills/skills/rf-browser/` with `name: rf-browser`. Claude Code then shows the plugin skill as `rf-agentskills:rf-browser`;
  - VS Code `vscode-extension/skills/rf-browser/` stays as it is.
- Drop the long→short name mapping in `scripts/sync-skills.sh` (`SHORT_NAMES`, the `name:` rewrite, the `rf-*`→short companion-table rewrite). Sync becomes a copy, plus the existing `python scripts/…` → `${CLAUDE_PLUGIN_ROOT}` path rewrite. Sync also deletes plugin/VS Code skill directories that no longer exist in root, so renamed and retired skills do not linger.
- Update everything that depends on the old names: `scripts/check-drift.sh`, `tests/test_drift_detection.py`, the per-skill tests (`SKILL_DIR` paths), the `robotframework-*` globs in `.github/workflows/ci.yml` and `release.yml` (Codex/Copilot packaging), the plugin subagent `.md` files, the skill list and regex in the `UserPromptSubmit` hook `maybe_inject_rf_context.mjs`, the eval task `skill:` fields, the README skill table and copy commands, and the existing specs that name the old paths.
- **Installer migration**: re-installing over an older bundle removes the files the previous manifest record owned that the new plan no longer writes (old `browser/`, `setup/`, … directories), using the same hash rule as uninstall. User-modified files are kept and reported. `rf-agentskills doctor` reports known legacy skill directories it does not own (for example from a manual tarball copy) with a hint to remove them. It never deletes them.
- Add spec-level frontmatter to every skill: `compatibility` (≤ 500 chars) naming the runtimes it needs (Python and Robot Framework floors, the library package, Node.js / Appium server / robotcode / uv as relevant), `license: Apache-2.0`, and `metadata` (`author`, `version` = bundle content version from `VERSION`, kept in step by `scripts/bump-version.sh`).
- Add a local validator `scripts/validate-skills.py`, stdlib-only and equivalent to `skills-ref validate`. For all three channels it checks: the name charset `[a-z0-9-]`, 1–64 chars, no leading, trailing or double hyphen; name == directory; description 1–1024 chars; compatibility ≤ 500 chars; no XML/HTML tags in name or description; only spec-known top-level keys; `metadata` is a string→string map. Run it in CI next to the drift check, and optionally cross-check with `skills-ref validate` when it is available.
- Ordering: implement **after** the retirement change (`retire-generator-skills`: rf-keyword-builder, rf-testcase-builder, rf-resource-architect) and the libdoc merge (`merge-libdoc-skills` → `rf-libdoc`), so that only the 10 remaining skills are renamed once. Implement **before** `sharpen-skill-descriptions`, which then edits the files at their new paths.

## Capabilities

### New Capabilities
- `skill-metadata-conformance`: every distributed skill conforms to the agentskills.io frontmatter spec (name/dir identity, charset, lengths, `compatibility`, `license`, `metadata`) in every channel. Sync, drift check, CI validation and installer upgrade keep it that way and migrate users off the old directory names.

### Modified Capabilities
- `platynui-skill`: the skill's location changes from `skills/robotframework-platynui-skill/` to `skills/rf-platynui/`, and the plugin copy changes from `plugins/rf-agentskills/skills/platynui/` to `.../rf-platynui/` with `name: rf-platynui`.
- `robotcode-skill`: location changes to `skills/rf-robotcode/`; the plugin copy changes to `plugins/rf-agentskills/skills/rf-robotcode/` with `name: rf-robotcode`.
- `setup-skill`: location changes to `skills/rf-setup/`; the plugin copy changes to `plugins/rf-agentskills/skills/rf-setup/` with `name: rf-setup`.

## Impact

- **Renamed (git mv)**: `skills/robotframework-{appium,browser,platynui,requests,restinstance,robotcode,selenium,setup}-skill/` → `skills/rf-{…}/`; `skills/robotframework-results/` → `skills/rf-results/`; the merged libdoc skill lands as `skills/rf-libdoc/` (created by `merge-libdoc-skills`, or renamed here if that change used a long name).
- **Regenerated**: `plugins/rf-agentskills/skills/*` (directories renamed to `rf-*`), `vscode-extension/skills/*`, `vscode-extension/package.json` `chatSkills`, and `installer/src/rf_agentskills/_assets/` (build hook mirror).
- **Edited**: `scripts/sync-skills.sh`, `scripts/check-drift.sh`, `scripts/bump-version.sh`, new `scripts/validate-skills.py`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `plugins/rf-agentskills/agents/*.md`, `plugins/rf-agentskills/scripts/maybe_inject_rf_context.mjs`, `installer/src/rf_agentskills/cli.py` (stale-file pruning on re-install; doctor legacy check), `eval/tasks/**/*.yaml` (`skill:`), `tests/` (drift, per-skill, hook, installer, new validator test), `README.md`, `installer/CHANGELOG.md`, `vscode-extension/CHANGELOG.md`.
- **Not touched**: the MCP server `_SCRIPT_PATHS`. It resolves the flat `plugins/rf-agentskills/scripts/` directory and does not depend on skill directory names. Only its entries for retired scripts go, and that belongs to the retirement change.
- **Users**: Claude Code plugin skills are now invoked as `/rf-agentskills:rf-browser` instead of `/rf-agentskills:browser`. Installer users are migrated on the next `install`. Users who copied tarball folders by hand get a doctor hint and a CHANGELOG note. VS Code users see no change.
