## Why

After the generator skills are retired, two scripts remain: `rf_libdoc.py` (rf-libdoc) and `rf_results.py` (rf-results). Both are invoked in a way that breaks in real projects:

- SKILL.md says `python scripts/x.py`. That runs whatever `python` is on PATH, not the project environment that holds Robot Framework and the project's libraries. It contradicts rf-setup ("run tools through the project environment: `uv run …`"), and `rf_libdoc.py` then cannot import the project's `Browser`/`SeleniumLibrary`/custom libraries.
- The relative `scripts/` path resolves from the project CWD in Claude Code (issue #11011), and the plugin's `${CLAUDE_PLUGIN_ROOT}` rewrite is not expanded in SKILL.md (issue #9354). The eval harness hides this because it rewrites the plugin root itself.
- The `robotframework>=7` dependency is not declared anywhere in the scripts.
- On a missing dependency the scripts tell users to run `pip install robotframework`, which contradicts rf-setup.
- Exit codes are inconsistent (`SystemExit("…")` exits 1 for both usage and data errors).
- `--help` has no examples.
- Some outputs are unbounded: `rf_results.py` `details`, and a single long keyword doc from `rf_libdoc.py` (~60 KB for SeleniumLibrary keywords, see `eval/tasks/narrow/narrow-libdoc-search-01.yaml`).
- The rf-tools MCP server runs under `python3` from PATH, so it has the same environment problem.

## What Changes

- **Project-environment invocation.** Every SKILL.md, subagent, hook message and doc that runs a skill script uses one canonical default, `uv run python <skill-dir>/scripts/<script>.py …`, followed by a one-line fallback that points to rf-setup (`.venv/bin/python`, `poetry run python`). No bare `python scripts/…`, no `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/…"` in SKILL.md, and no `pip install` advice. **BREAKING** (docs/commands) for users who copy the old commands.
- **Portable path resolution per channel.**
  - Root and VS Code SKILL.md use skill-root-relative `scripts/…` and state that paths are relative to the skill directory.
  - The Claude Code plugin channel is rewritten at sync to `${CLAUDE_SKILL_DIR}/scripts/…`, and each plugin skill ships its own `scripts/`.
  - The installer substitutes the absolute installed skill path for agents that expand neither variable.
  - Subagents stop running script paths and use the rf-tools MCP tools, or load the skill.
- **Declared dependencies.** Each script carries PEP 723 inline metadata (`requires-python`, `robotframework>=7`) and a runtime version check. Skills with scripts state the need in `compatibility` (field owned by `align-skill-names-with-spec`).
- **Consistent CLI contract.**
  - Exit codes: 0 ok, 1 internal error, 2 usage, 3 environment/dependency, 4 input not found/unloadable.
  - JSON only on stdout, and diagnostics only on stderr as `error:` or `hint:` lines that name the interpreter and the fix (e.g. `uv add robotframework`).
  - `--help` ends with runnable examples.
- **Bounded output.**
  - `rf_libdoc.py` gets `--max-doc-chars` (default bounded) with an in-text truncation marker.
  - `rf_results.py` gets `--limit` for `details`/`errors` items, with omitted counts.
  - Both scripts get `--json-out FILE`. The name `--output` is avoided because `rf_results.py --output` already names the input `output.xml`.
- **MCP server uses the project environment.** `rf-tools` runs the scripts in-process when its own interpreter can import the requested library. Otherwise it runs the same script in a subprocess with the project interpreter it finds (uv project / `.venv` / `VIRTUAL_ENV`). It resolves scripts `__file__`-relative from the per-skill `scripts/` directories.
- **No symlinks in skill script trees.** Every shipped script is a regular, self-contained file. Removing the libdoc symlink itself is done by `merge-libdoc-skills`. This change adds the general rule and its check.
- **Tests** for exit codes, stderr hints, `--help` examples, truncation and `--json-out`, PEP 723 metadata, SKILL.md command form per channel, a missing-robotframework interpreter, and MCP subprocess fallback.

## Capabilities

### New Capabilities
- `skill-script-execution`: how skill scripts are invoked and behave as CLIs across agents and channels. It covers interpreter/environment selection, path resolution, dependency declaration, exit codes and diagnostics, help examples, output bounding and file output, MCP server execution, and the absence of symlinks.

### Modified Capabilities
<!-- None. `rf-script-output` specifies the JSON *content* contract of rf_libdoc.py (mode/results schema, minimal library refs, usage breakdown). That stays unchanged. Its requirements are already being edited by `retire-generator-skills` (testcase_builder) and `merge-libdoc-skills` (in-repo consumers), so execution concerns go in a separate capability to avoid conflicting deltas. The truncation marker is placed inside the existing `doc` string, and no rf_libdoc schema key is added. -->

## Impact

- **Scripts**: `skills/rf-libdoc/scripts/rf_libdoc.py` and `skills/rf-results/scripts/rf_results.py`, plus their synced plugin, VS Code and installer copies.
- **Skill docs**: `SKILL.md` of rf-libdoc and rf-results, and the fallback mentions in rf-robotcode and the library skills.
- **Plugin**:
  - `plugins/rf-agentskills/servers/rf-tools-server.py` (script location, interpreter fallback)
  - `plugins/rf-agentskills/.mcp.json`
  - `plugins/rf-agentskills/agents/{rf-debug-expert,rf-keyword-consultant,rf-migration-guide}.md`
  - `plugins/rf-agentskills/scripts/maybe_remind_robot_tests.mjs` (message text)
  - The flat `plugins/rf-agentskills/scripts/*.py` copies are removed in favor of per-skill `scripts/`.
- **Distribution**: `scripts/sync-skills.sh` (rewrite rule `scripts/` → `${CLAUDE_SKILL_DIR}/scripts/`, per-skill scripts copy), `scripts/check-drift.sh` (symlink and command-form checks), and the installer (`installer/src/rf_agentskills/transforms.py` substitution for non-Claude adapters, `_assets` layout).
- **Eval harness**: `ClaudeCodeRunner._rewrite_plugin_root` no longer needs to paper over SKILL.md paths. The harness may keep the rewrite for hooks and MCP JSON only.
- **Tests**: new `tests/test_script_execution.py` and `tests/test_skill_commands.py`; updates to `tests/test_rf_libdoc.py`, `tests/test_rf_results.py`, `tests/test_drift_detection.py`, `tests/test_hook_scripts.py` and installer transform tests.
- **Ordering**: after `retire-generator-skills` and `merge-libdoc-skills`. `align-skill-names-with-spec` (already implemented) made every skill dir `rf-<topic>` in all channels, removed the sync name map and authored the `compatibility` text. This change owns only the command form and the script-path rewrite.
