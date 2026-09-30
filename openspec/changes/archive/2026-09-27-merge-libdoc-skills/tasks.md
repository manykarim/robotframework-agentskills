## 1. Merged skill

- [x] 1.1 `git mv skills/robotframework-libdoc-search/scripts/rf_libdoc.py skills/rf-libdoc/scripts/rf_libdoc.py` and delete `skills/robotframework-libdoc-search/` and `skills/robotframework-libdoc-explain/` (incl. symlink) (design D2). Verify: `find skills -type l` prints nothing and `python skills/rf-libdoc/scripts/rf_libdoc.py --help` works
- [x] 1.2 Write `skills/rf-libdoc/SKILL.md` per design D4: `name: rf-libdoc`, merged description, robotcode boundary line, command table for search / explain / explain+fallback / list, sources, output contract once, filters. Verify: description ≤ 1024 chars; every long option in its code blocks appears in `rf_libdoc.py --help`
- [x] 1.3 Add `tests/test_libdoc_skill.py`: frontmatter name == dir, description mentions both jobs, `rf-robotcode` boundary present, four modes shown, documented flags accepted by `--help`, no symlinks in any skill tree, old skill dirs absent in all channels. Verify: `uv run pytest tests/test_libdoc_skill.py` passes

## 2. Distribution

- [x] 2.1 In `scripts/sync-skills.sh` replace the two libdoc `SHORT_NAMES` entries with `["rf-libdoc"]="libdoc"` and the two sed rules with one `` `rf-libdoc` `` → `` `libdoc` `` rule (design D1). Verify: after sync, `plugins/rf-agentskills/skills/libdoc/SKILL.md` has `name: libdoc` and `vscode-extension/skills/rf-libdoc/` exists
- [x] 2.2 Add a no-symlink check to `scripts/check-drift.sh` covering root `skills/`, plugin `skills/` + `scripts/`, `vscode-extension/skills/`; also compare the VS Code `scripts/*.py` copies byte-for-byte with root (spec "Copies identical"); update `tests/test_drift_detection.py` for the new script path. Verify: planting a symlink makes the check exit 1; clean tree exits 0
- [x] 2.3 Run `scripts/sync-skills.sh`. Verify: `plugins/rf-agentskills/skills/{libdoc-search,libdoc-explain}` and `vscode-extension/skills/rf-libdoc-{search,explain}` are gone, `vscode-extension/package.json` lists `./skills/rf-libdoc/SKILL.md` once, and `plugins/rf-agentskills/scripts/rf_libdoc.py` is byte-identical to the root copy
- [x] 2.4 Update docstrings in `plugins/rf-agentskills/servers/rf-tools-server.py` that name the old skills; keep tool names and schemas (design D3). Verify: a test lists tools and finds `rf_libdoc_search` and `rf_libdoc_explain` with unchanged `required` fields

## 3. References

- [x] 3.1 Replace the two libdoc rows with one `rf-libdoc` row in the Companion Skills tables of appium, browser, platynui, requests, restinstance, selenium and robotcode; update `rf-robotcode`'s fallback wording and `skills/rf-libdoc` + `rf-results` link-back (design D5). Verify: grep of `skills/` for `libdoc-search|libdoc-explain` returns nothing; update `tests/test_robotcode_skill.py` lists and it passes
- [x] 3.2 Update `plugins/rf-agentskills/agents/{rf-debug-expert,rf-keyword-consultant,rf-migration-guide,rf-test-architect}.md` to name `rf-libdoc` (keep MCP tool names). Verify: grep of `plugins/rf-agentskills/agents/` for `libdoc-search|libdoc-explain` returns nothing
- [x] 3.3 Update `maybe_inject_rf_context.mjs` (comment, regex, injected list and "Prefer …" line) and `plugins/rf-agentskills/hooks/README.md`. Verify: `uv run pytest tests/test_hook_scripts.py` passes with the libdoc trigger prompts rewritten to the merged name, a prompt containing only "libdoc" still triggers, and the injected text names the merged skill and not the old ones
- [x] 3.4 Update `README.md` (skills table, requirements, tests, MCP section wording), `.claude-plugin/marketplace.json`, `plugins/rf-agentskills/.claude-plugin/plugin.json` and `vscode-extension/package.json` descriptions/counts. Verify: `uv run pytest tests/test_marketplace_validation.py` passes
- [x] 3.5a Update `.github/workflows/release.yml` and `.github/workflows/ci.yml` packaging loops from `skills/robotframework-*/` to `skills/*/` so the Codex/Copilot tarballs ship `rf-libdoc` (the new dir does not match the old glob). Verify: grep finds no `skills/robotframework-\*` glob in `.github/workflows/`
- [x] 3.5 Update `docs/installer/docker/checks/{claude-code,codex,copilot,cursor,goose,opencode}.sh` to expect `libdoc/SKILL.md` (and `need_no_file` for `libdoc-search` after upgrade). Verify: `bash -n` passes on each script

## 4. Evals and tests

- [x] 4.1 Set `skill:` to the merged plugin name and rewrite grader `input_pattern`s in `narrow-libdoc-search-01`, `narrow-libdoc-search-02-no-mcp`, `narrow-non-rf-control-01`, `narrow-rf-injection-positive-01` (and `narrow-rf-mcp-execute-01` if `retire-generator-skills` pointed it at `libdoc-search`) (design D5). Also update `scripts/eval-smoke.sh`, `eval/tasks/README.md`, `docs/ci/usage.md` and `docs/ci/local-testing.md` wording that names the old skills (task ids stay). Verify: a loader test asserts every task `skill:` is a plugin skill dir (exists: `tests/eval/test_task_yaml_loading.py`)
- [x] 4.2 Update `tests/installer/{test_adapter_claude_code,test_assets,test_transforms}.py`, `tests/test_rf_tools_server.py` and `tests/eval/{test_runner_workspace,test_scoring_session_based}.py` to use the merged name. Verify: `uv run pytest tests/installer tests/eval -q` passes
- [x] 4.3 Add an installer test (reuse the prune-on-reinstall machinery and `tests/installer/test_reinstall_prune.py` helpers from `retire-generator-skills`; no installer code change): a manifest from a 1.2.0-style install with `skills/libdoc-search/` and `skills/libdoc-explain/` is upgraded and both dirs are removed while `skills/libdoc/` is installed. Verify: `uv run pytest tests/installer -q` passes

## 5. Release and final checks

- [x] 5.1 Add the merge to the content 2.0.0 entry in `vscode-extension/CHANGELOG.md` and to `installer/CHANGELOG.md` (merged name, MCP tools unchanged, manual cleanup for tarball users). Verify: entries name both old skills and `rf-libdoc`
- [x] 5.2 Run `bash scripts/sync-skills.sh && bash scripts/check-drift.sh && uv run pytest -q && uv run pytest -q tests/ --ignore=tests/eval`, `check-skill-keywords.py --require-all` (root + plugin), rebuild installer assets (`uv build installer/`), `npm run compile` in vscode-extension and the reference scan from the `libdoc-skill` spec. Verify: no drift, all tests pass, scan finds no old names outside the allowed exclusions
