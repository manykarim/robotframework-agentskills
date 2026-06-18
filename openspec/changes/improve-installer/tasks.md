## 1. Granular, ownership-aware hooks merge (the core safety fix)

- [x] 1.1 Add `transforms.merge_hooks_block(settings_path, hooks_value, *, marker)` — append rf-agentskills matcher-groups per event without replacing siblings; idempotent (skip groups already owned by `marker`); return a record of touched events.
- [x] 1.2 Add `transforms.remove_owned_hook_entries(settings_path, *, marker, events)` — drop only matcher-groups whose commands contain `marker`; prune empty event lists; prune empty `hooks`; delete file only when it becomes `{}`.
- [x] 1.3 Introduce `ConfigMerge.kind = "json_hooks"` carrying the ownership `marker` (install dir) and touched `events`; wire it through `manifest` and the out-of-process uninstall reconstruction in `cli.py`.
- [x] 1.4 Switch `adapters/claude_code._hooks_merge_op` to the new merge/remove pair (the MCP per-server merge is unchanged — already granular).
- [x] 1.5 Confirm Cursor hooks rewrite path (`rewrite_hooks_for_cursor`) uses the same granular merge if/where it writes to a shared settings file.

## 2. Uninstall correctness tests

- [x] 2.1 New `tests/installer/test_uninstall_safety.py`, sandboxed via `HOME=<tmp>`/`--prefix`.
- [x] 2.2 Foreign-hook preservation: seed `settings.json` with a foreign `PostToolUse` group + user `Notification` hook; assert both survive install and uninstall.
- [x] 2.3 Our-own removal: assert all rf-agentskills hook events are added on install and fully removed on uninstall, with no command referencing the deleted install dir.
- [x] 2.4 Foreign-MCP preservation: seed `.mcp.json` with `some-other-server`; assert it coexists with `rf-tools` and survives uninstall.
- [x] 2.5 Idempotent re-install: install twice; assert no duplicate matcher-groups.
- [x] 2.6 Pruning vs retention: assert emptied `hooks` is pruned but the file is kept when `model`/foreign keys remain; deleted only when it would be `{}`.
- [x] 2.7 User-modified skip: edit an installed file, assert uninstall skips (not deletes) it.

## 3. Interactive wizard + non-interactive flags

- [x] 3.1 Add `questionary` as an optional `[interactive]` extra in `installer/pyproject.toml`; import it lazily.
- [x] 3.2 Implement the selection wizard (multi-select of known agents, detected pre-checked) with a stdlib `input()` numbered fallback when questionary/TTY is absent.
- [x] 3.3 Add `--agents all|none|detected|<csv>` and `--yes`; keep `--agent`/`--all` as back-compat. Detect non-TTY stdin → non-interactive automatically.
- [x] 3.4 Implement the decision tree (explicit → use; interactive → wizard; non-interactive → detected, else exit non-zero with valid-agent list + flag hint). Define exit codes (0 ok, 1 none-detected/none-selected, 2 usage).
- [x] 3.5 Show and confirm the resolved scope + target directory before writing (interactive only).

## 4. Project-scope default

- [x] 4.1 Flip `InstallOptions.scope` default to `"project"` and default `project_dir` to CWD; make `--scope user` the global opt-in.
- [x] 4.2 Update `cmd_install`/`cmd_uninstall` validation (no longer require `--project` for the default project scope; resolve to CWD).
- [x] 4.3 Update existing installer tests that assumed user-scope default.

## 5. Wizard / flag tests

- [x] 5.1 Headless: `--agents claude-code,cursor` with stdin `/dev/null` installs exactly those, exit 0, no prompt.
- [x] 5.2 `--agents all|none|detected` resolve correctly; `none` is a no-op exit 0.
- [x] 5.3 Non-TTY, no selection, nothing detected → non-zero exit + valid-agent list printed.
- [x] 5.4 Project-scope default writes under CWD; `--scope user` writes under home.

## 6. PyPI publish (zero-install entry point)

- [x] 6.1 Wire `twine upload` into the tooling release flow (token via CI secret); update `RELEASING.md` (remove the "future follow-up" caveat).
- [x] 6.2 Verify `uvx rf-agentskills install` / `pipx run rf-agentskills` works from the published package.

## 7. Docs + changelog

- [x] 7.1 `installer/README.md`: document the wizard, `--agents`/`--yes`, the project-scope default + `--scope user`, and `uvx` usage.
- [x] 7.2 `installer/CHANGELOG.md`: note the default-scope change, the hooks-merge safety fix, and the new entry point under the next installer version.
