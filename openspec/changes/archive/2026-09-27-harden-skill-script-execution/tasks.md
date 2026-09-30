## 1. Preconditions and verification spikes

- [x] 1.1 (verified against the official Claude Code docs for 2.1.283; a live throwaway-plugin echo run needs a model call and was not run — see design D2) Verify in current Claude Code that `${CLAUDE_SKILL_DIR}` is substituted in a plugin-provided SKILL.md body. Test a throwaway plugin skill whose bash block echoes the path, and record the Claude Code version and result in design.md D2. If it is not substituted, switch the plugin rendering to the relative-with-note form before continuing
- [x] 1.2 Check whether `${CLAUDE_PLUGIN_ROOT}` is substituted in plugin subagent bodies and record the result; verify the note is added to design.md
- [x] 1.3 Confirm that `retire-generator-skills` and `merge-libdoc-skills` are merged (only `rf_libdoc.py` and `rf_results.py` remain, `skills/rf-libdoc/` exists, no libdoc symlink); verify with `find skills -name '*.py' -path '*scripts*'` and `find skills -type l`

## 2. Script CLI contract

- [x] 2.1 Add PEP 723 `# /// script` blocks (`requires-python`, `robotframework>=7`) to `rf_libdoc.py` and `rf_results.py`; verify with a regex test in `tests/test_skill_commands.py`
- [x] 2.2 Move the Robot Framework import behind a `_require_robot()` check after argument parsing, with a ≥7 version check and exit 3; verify that `--help` exits 0 under an interpreter without RF, and that RF missing gives exit 3 (`tests/test_script_execution.py`)
- [x] 2.3 Add a `_fail(code, error, *hints)` helper and replace `SystemExit("…")` with `parser.error` (exit 2). Map missing or unparseable inputs and all-sources-failed to exit 4, partial load failures to exit 0 plus a stderr warning, and unexpected exceptions to exit 1 (`--debug` for the traceback); verify each case in `tests/test_script_execution.py`
- [x] 2.4 Rewrite diagnostics as `error:`/`warning:`/`hint:` stderr lines with empty stdout on failure. Hints name `sys.executable`, `uv run python …`, `uv add robotframework` and the library→package map, and never mention `pip install`; verify with assertions on stderr text
- [x] 2.5 Add argparse epilogs with ≥3 `uv run python scripts/<name>.py …` examples per script; verify with a test parsing `--help` output
- [x] 2.6 Add `--max-doc-chars` (default 4000, 0 = unlimited, in-string truncation marker) to `rf_libdoc.py`; verify with the SeleniumLibrary `Input Text` case and `--max-doc-chars 0`, and check that the JSON keys are unchanged against the `rf-script-output` tests
- [x] 2.7 Add `--limit` (default 50, failed first) with `omitted` counts to `rf_results.py` `details`/`errors`; verify with a generated large `output.xml` fixture
- [x] 2.8 Add `--json-out FILE` to both scripts (creates parent dirs, prints a `{written, bytes, mode}` summary); verify with a temp-dir test, including that `rf_results.py --output` still means the input

## 3. SKILL.md, subagents and hook messages

- [x] 3.1 Rewrite every script command in the root `rf-libdoc` and `rf-results` SKILL.md to `uv run python scripts/<name>.py …`. Add the "paths are relative to this skill's directory" note and the single non-uv fallback line pointing to rf-setup, and update the rf-results standalone `uv run --script` example; verify with `tests/test_skill_commands.py`
- [x] 3.2 Update fallback mentions of the scripts in other skills (rf-robotcode, library skills' companion text) to the canonical form; verify with a `grep -rn "python scripts/\|pip install" skills/` that finds no script-related hits
- [x] 3.3 Replace script paths in `plugins/rf-agentskills/agents/{rf-debug-expert,rf-keyword-consultant,rf-migration-guide}.md` with instructions to use the `rf-tools` MCP tools or load the skill; verify that `grep -n "scripts/rf_" plugins/rf-agentskills/agents` is empty
- [x] 3.4 Make `maybe_remind_robot_tests.mjs` compute the absolute `rf_results.py` path from `import.meta.url` and print `uv run python "<abs path>" …`; verify with `tests/test_hook_scripts.py`
- [x] 3.5 Add a test asserting that each script-bearing skill's `compatibility` mentions Python and `robotframework>=7` (field authored by `align-skill-names-with-spec`); verify the test passes

## 4. Distribution channels

- [x] 4.1 Change `scripts/sync-skills.sh`: copy each skill's `scripts/` into `plugins/rf-agentskills/skills/<skill>/scripts/` and `vscode-extension/skills/<skill>/scripts/` as regular files, rewrite `scripts/<name>.py` → `"${CLAUDE_SKILL_DIR}/scripts/<name>.py"` for the plugin only, and stop copying to the flat `plugins/rf-agentskills/scripts/*.py`; verify by running sync and inspecting the generated plugin SKILL.md
- [x] 4.2 Delete `plugins/rf-agentskills/scripts/{rf_libdoc,rf_results}.py`; verify that `ls plugins/rf-agentskills/scripts` lists only `.mjs` hook files
- [x] 4.3 Extend `scripts/check-drift.sh` (symlink check already present since `merge-libdoc-skills`; keep it) to fail on `${CLAUDE_PLUGIN_ROOT}` in any SKILL.md, and on bare `python scripts/` in any channel; verify with `tests/test_drift_detection.py` cases that add each violation to a temp copy
- [x] 4.4 Add `expands_skill_dir` to installer adapters and `transforms.substitute_skill_dir(text, abs_skill_dir)`, and apply it for adapters that do not expand the variable; update `_assets` to the per-skill scripts layout and stage `skills/<skill>/scripts/` under `rf-agentskills-files/` for the MCP server; verify with `tests/installer/test_transforms.py` and an adapter install test asserting that the absolute script path exists
- [x] 4.5 Run `bash scripts/sync-skills.sh && bash scripts/check-drift.sh`; both succeed with no drift

## 5. MCP server

- [x] 5.1 Point `_SCRIPT_PATHS` in `rf-tools-server.py` at `<plugin_root>/skills/<skill>/scripts/<name>.py`; verify that the existing MCP server tests pass
- [x] 5.2 Add the in-process capability check (RF ≥7 and requested libraries importable, cached per process) and the subprocess fallback with project-interpreter detection (uv project → `uv run --frozen python`, `.venv`, `VIRTUAL_ENV`), 120 s timeout, and exit 3/4 mapped to MCP errors with hints; verify with a test using a temp `.venv` fixture and a forced-false capability check
- [x] 5.3 Confirm that the server stays alive after script errors in both paths; verify with a test issuing a failing call followed by a successful call

## 6. Eval harness alignment and final checks

- [x] 6.1 Limit `ClaudeCodeRunner._rewrite_plugin_root` to JSON config files (hooks, `.mcp.json`) so that SKILL.md paths are exercised as users see them; verify with `tests/eval/test_runner_workspace.py`
- [x] 6.2 Add a uv integration test (skipped without `uv`): a temp uv project with robotframework runs `uv run python <script> --library BuiltIn --search log` with exit 0, using the project `.venv` interpreter rather than a PEP 723 isolated environment; verify locally
- [x] 6.3 Run `uv run pytest tests/ --ignore=tests/eval` and `uv run pytest tests/eval`; all pass
- [ ] 6.4 (DEFERRED: live eval run — tracked in follow-up) Run the eval narrow tasks for rf-libdoc and rf-results (`--runs 3`) and confirm that no run shows a failed first script invocation caused by a wrong path or interpreter (inspect `stdout.stream.jsonl` for Bash tool results with "No such file" or `ModuleNotFoundError: robot`)
- [x] 6.5 Add CHANGELOG entries (root, plugin, installer) describing the new command form, the exit codes and the removed flat plugin scripts; verify the entries exist
