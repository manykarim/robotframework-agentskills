## 1. Distribution tooling (do first so deletions propagate)

- [x] 1.1 Change `scripts/sync-skills.sh` to derive the script list from `skills/*/scripts/*.py` (non-symlink) and to delete plugin `skills/<dir>` without a root source and plugin `scripts/*.py` without a root source (leave `.mjs`, `servers/`, `agents/`, `hooks/` alone) (design D4). Verify: in a scratch copy, delete a root skill, run sync, and the plugin + VS Code copies and its plugin script are gone
- [x] 1.2 Change `scripts/check-drift.sh` to derive `SCRIPT_MAP` from root and add an orphan pass over plugin skill dirs, plugin `*.py` and `vscode-extension/skills/*`. Verify: planting an orphan dir makes it exit 1 naming the orphan; a clean tree exits 0
- [x] 1.3 Update `tests/test_drift_detection.py` for the derived map and add an orphan-detection case. Verify: `uv run pytest tests/test_drift_detection.py` passes

## 2. Remove skills, scripts and MCP tools

- [x] 2.1 Delete `skills/robotframework-keyword-builder/`, `skills/robotframework-testcase-builder/`, `skills/robotframework-resource-architect/` and their `SHORT_NAMES` entries and `rf-*` sed rules in `sync-skills.sh`. Verify: `ls skills/` shows none of the three
- [x] 2.2 Remove `tool_keyword_builder`, `tool_testcase_builder`, `tool_resource_architect`, their `_SCRIPT_PATHS` entries, `list_tools` entries, `call_tool` branches and module docstring mentions from `plugins/rf-agentskills/servers/rf-tools-server.py`. Verify: a test lists tools and gets only `rf_libdoc_search`, `rf_libdoc_explain`, `rf_results_analyze`, and calling `rf_keyword_builder` returns `{"error": "Unknown tool: ..."}`
- [x] 2.3 Run `scripts/sync-skills.sh`. Verify: `plugins/rf-agentskills/skills/{keyword-builder,testcase-builder,resource-architect}`, `plugins/rf-agentskills/scripts/{keyword_builder,testcase_builder,resource_architect}.py` and `vscode-extension/skills/rf-{keyword-builder,testcase-builder,resource-architect}` no longer exist, and `vscode-extension/package.json` no longer lists them
- [x] 2.4 Delete `tests/test_keyword_builder.py`, `tests/test_testcase_builder.py`, `tests/test_resource_architect.py`. Verify: `uv run pytest tests/ -q` collects no generator tests

## 3. Remove references in shipped content

- [x] 3.1 Remove the three generator rows from the Companion Skills tables of `rf-appium`, `rf-browser`, `rf-platynui`, `rf-requests`, `rf-restinstance`, `rf-selenium`, `rf-robotcode` and `rf-setup`, and the resource-architect line in `skills/robotframework-setup-skill/references/project-layout.md` (design D3). Verify: grep of `skills/` for the six names returns nothing; `tests/test_robotcode_skill.py` and `tests/test_setup_skill.py` still pass
- [x] 3.2 Rewrite the generator steps in `plugins/rf-agentskills/agents/rf-test-architect.md`, `rf-keyword-consultant.md`, `rf-migration-guide.md`: write RF directly, verify with the libdoc skill / `robotcode libdoc`, then `robot --dryrun`; move the resource-layout advice inline (design D2). Verify: grep of `plugins/rf-agentskills/agents/` for the six names returns nothing
- [x] 3.3 Update `plugins/rf-agentskills/scripts/maybe_inject_rf_context.mjs` (comment block and injected "Script-based tools" list) and `plugins/rf-agentskills/hooks/README.md`. Verify: `uv run pytest tests/test_hook_scripts.py` passes after replacing the two generator-named trigger prompts with equivalent prompts that do not name retired skills, and a new assertion checks the injected text names none of the retired skills
- [x] 3.4 Update `README.md` (skills table, requirements paragraph, test commands, MCP tools table, skill count), `.claude-plugin/marketplace.json` and `plugins/rf-agentskills/.claude-plugin/plugin.json` descriptions, and `vscode-extension/package.json` description. Verify: `uv run pytest tests/test_marketplace_validation.py` passes and grep finds no generator names in these files
- [x] 3.5 Update current-behaviour docs: `docs/ci/usage.md` (smoke task, sample output), `docs/installer/docker/checks/{claude-code,codex,goose,opencode}.sh` (expected files; add a `need_no_file` for a retired skill after upgrade). Verify: `bash -n` on each check script succeeds and grep finds no generator names except intentional `need_no_file` assertions

## 4. Evaluation assets

- [x] 4.1 Delete `eval/tasks/narrow/narrow-{keyword-builder,testcase-builder,resource-architect}-01.yaml`; set `skill:` of `narrow-rf-mcp-execute-01.yaml` to a shipped skill (design D8); update `eval/tasks/README.md` example and `eval/fixtures/sut-minimal` comments. Verify: a test loads every task YAML and asserts its `skill:` is a directory in `plugins/rf-agentskills/skills/`
- [x] 4.2 Point `scripts/eval-smoke.sh` at `eval/tasks/narrow/narrow-libdoc-search-01.yaml` (or its renamed successor). Verify: the path in the script exists
- [x] 4.3 Replace `keyword-builder` sample skill names in `tests/eval/conftest.py`, `tests/eval/test_domain_task.py`, `tests/eval/test_cli_score_batch.py`, `tests/eval/test_runner_workspace.py` with a shipped skill name. Verify: `uv run pytest tests/eval -q` passes

## 5. Installer prune-on-reinstall

- [x] 5.1 Add optional `category` to the manifest `FileEntry` (written on install, derived from path for older records) and a stale-file computation in `installer/src/rf_agentskills/cli.py` `_execute_plan`: remove hash-matching stale files in selected categories, prune empty parents up to the install root, keep and report user-modified ones, carry over unselected-category entries (design D5). Verify: task 5.3 tests pass
- [x] 5.2 Show stale files as `remove` rows in the `--dry-run` plan table and report the stale-removed count in the install summary. Verify: dry-run test in 5.3 sees the rows and no deletion
- [x] 5.3 Add sandboxed installer tests: upgrade removes a retired skill dir, user-modified stale file kept and untracked, `--what skills` re-install keeps agents/hooks tracked, dry run lists removals, old-format manifest without `category`. Verify: `uv run pytest tests/installer -q` passes, including existing uninstall-safety tests
- [x] 5.4 Rebuild the installer assets (`uv build installer/` or editable install). Verify: `installer/src/rf_agentskills/_assets/` contains no generator skill or script

## 6. Release metadata

- [x] 6.1 Bump content version to 2.0.0 in `plugins/rf-agentskills/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` (metadata + plugin entry) and `vscode-extension/package.json`; bump installer to 0.7.0 in `installer/pyproject.toml` (design D6). Verify: `uv run pytest tests/test_marketplace_validation.py` passes and `rf-agentskills version` prints `bundled content: 2.0.0`
- [x] 6.2 Add a 2.0.0 entry to `vscode-extension/CHANGELOG.md` and an installer entry to `installer/CHANGELOG.md`: removed skills, removed MCP tools, replacement guidance (write RF directly; verify with libdoc and `robot --dryrun`), upgrade notes per channel (tarball users delete dirs by hand). Verify: both entries name all three skills and all three MCP tools

## 7. Final verification

- [x] 7.1 Run `bash scripts/sync-skills.sh && bash scripts/check-drift.sh && uv run pytest -q`. Verify: no drift, all tests pass
- [x] 7.2 Run the reference scan from the `skill-catalog` spec (`grep -rn "keyword-builder\|keyword_builder\|testcase-builder\|testcase_builder\|resource-architect\|resource_architect"` excluding archive, `eval/runs/`, historical docs, CHANGELOG history and dependency dirs). Verify: no matches
