## Context

Current state (see proposal.md for the problems):

- **Scripts.**
  - `rf_libdoc.py` (421 lines) and `rf_results.py` (418 lines) do `from robot import …` at module top. On `ImportError` they print a JSON error to **stderr** that says `pip install robotframework`, then `sys.exit(1)`. Because the import runs before argparse, `--help` fails without RF.
  - Usage errors use `raise SystemExit("…")` (exit 1).
  - `rf_libdoc.py` collects per-source `load_errors` into its JSON.
  - `rf_results.py` raises `RuntimeError` on parse failure (uncaught traceback, exit 1).
  - `rf_results.py --output` is the *input* file.
  - Neither script has an argparse epilog.
- **Copies.** The root copy lives in `skills/<dir>/scripts/`. `scripts/sync-skills.sh` copies scripts to the **flat** `plugins/rf-agentskills/scripts/` and rewrites `python scripts/x.py` to `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/x.py"` in plugin SKILL.md. That form is not expanded in SKILL.md (issue #9354), so the model sees the literal. VS Code copies dereference symlinks. The installer ships the plugin tree (`installer/src/rf_agentskills/_assets`), and `transforms.substitute_plugin_root` substitutes `${CLAUDE_PLUGIN_ROOT}` only in some files. It also pins a hook interpreter through `python_runtime.json`, which is a precedent for environment-aware execution.
- **MCP server.** `plugins/rf-agentskills/.mcp.json` launches `rf-tools-server.py` with `python3`. The server resolves `_SCRIPTS_DIR` `__file__`-relative (good), loads the scripts as modules and calls their functions in-process, catching `(Exception, SystemExit)`. In-process means library imports only see the server's interpreter.
- **Subagents** (`agents/*.md`) and `maybe_remind_robot_tests.mjs` embed `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/…"`.
- **Eval harness.** `ClaudeCodeRunner._rewrite_plugin_root` substitutes the absolute plugin path into staged files. That makes evals pass where real installs would not.
- **Sibling changes.**
  - `merge-libdoc-skills` removes the libdoc symlink and creates `skills/rf-libdoc/`, keeping `python scripts/rf_libdoc.py` so that this change can rewrite commands in one place.
  - `align-skill-names-with-spec` owns directory names, drops the short-name map and adds `compatibility`.
  - `retire-generator-skills` removes the other three scripts and the MCP tools for them.

## Goals / Non-Goals

**Goals:**
- One canonical, environment-correct command per script, rendered correctly for each channel and agent.
- A CLI contract for exit codes, stderr and help that agents can reason about without reading source.
- Output that is safe for context windows by default.

**Non-Goals:**
- Changing the JSON content schema of `rf_libdoc.py` (`rf-script-output` stays as is).
- Publishing the scripts as a pip package or console entry points. That is a separate, later decision (see project memory "next steps").
- New script features beyond bounding and file output.
- Windows-specific path handling beyond not relying on symlinks and using `pathlib`.

## Decisions

### D1. `uv run python <script>` in the project, not `uv run --script`
The scripts must import the *project's* Robot Framework and libraries. `rf_libdoc.py` inspects `Browser`, `SeleniumLibrary` and custom libraries at the project's versions. `rf_results.py` should parse `output.xml` with the RF version that wrote it.
- `uv run python path/to/script.py` runs in the project environment. It does not treat the file as a PEP 723 script: inline metadata is only honoured when the script is the direct target (`uv run script.py` / `uv run --script`). Implementation must verify this with a test.
- `uv run --script` would build an **isolated** environment with only `robotframework`, which silently loses the project's libraries. So PEP 723 metadata is kept for two purposes: declaring the requirement, and standalone use outside a project (e.g. `uv run --script rf_results.py --output ci/output.xml` on a CI artifact). SKILL.md mentions this only as a secondary example for rf-results.
- Fallback line: "Not using uv? Run with the project's interpreter: `.venv/bin/python …` or `poetry run python …` (see rf-setup)."
- *Alternative:* `python3` plus instructions to activate the venv. Rejected: activation does not persist across agent Bash calls, and it is the current failure mode.

### D2. Per-channel path rendering from one root source
The root SKILL.md is authored with `uv run python scripts/<name>.py` plus a note: "Paths are relative to this skill's directory." This follows agentskills.io, which says file references are relative to the skill root.
- **Plugin (Claude Code):** `sync-skills.sh` rewrites `scripts/<name>.py` → `"${CLAUDE_SKILL_DIR}/scripts/<name>.py"`. Claude Code substitutes `${CLAUDE_SKILL_DIR}` in skill content, unlike `${CLAUDE_PLUGIN_ROOT}`. Scripts are copied into `plugins/rf-agentskills/skills/<skill>/scripts/`. The flat `plugins/rf-agentskills/scripts/*.py` copies are removed; that directory keeps only the hook `.mjs` files.
- **VS Code:** the root form is kept (relative plus note), with scripts copied as regular files.
- **Installer:**
  - The `claude_code` adapter keeps `${CLAUDE_SKILL_DIR}`.
  - Adapters for agents that do not substitute it (codex, cursor, copilot, goose, opencode, claude_desktop) run a new `transforms.substitute_skill_dir(text, abs_skill_dir)`, which also converts relative `scripts/` in command lines to the absolute installed path.
  - The adapter capability flag (`expands_skill_dir: bool`) lives on each adapter.
- **Subagents and hooks:** subagent `.md` files stop embedding script paths and tell the agent to use the `rf-tools` MCP tools (`rf_libdoc_search`, `rf_libdoc_explain`, `rf_results_analyze`), or to load the `rf-libdoc`/`rf-results` skill. `maybe_remind_robot_tests.mjs` builds the absolute path at run time from its own location (`import.meta.url`) instead of printing a variable.
- *Alternative:* keep the flat plugin `scripts/` and put `${CLAUDE_PLUGIN_ROOT}` in SKILL.md. Rejected (#9354).
- *Alternative:* absolute paths everywhere at install time. Rejected for the plugin channel, which is not "installed" by us, and for the root channel, which must stay portable.
- **Verified (task 1.1/1.2, 2026-09-27, Claude Code 2.1.283):** the Claude Code skills reference (https://code.claude.com/docs/en/skills, "Available string substitutions") documents `${CLAUDE_SKILL_DIR}` as "the directory containing the skill's SKILL.md file. For plugin skills, this is the skill's subdirectory within the plugin, not the plugin root", substituted in the skill's markdown content and in `allowed-tools` Bash rules — also for personal/project skills (e.g. `~/.claude/skills/<name>/`). The plugin manifest reference ("Where each variable resolves") lists "Skill, command, and agent content — anywhere in the Markdown body" for `${CLAUDE_PLUGIN_ROOT}`, so it is substituted in plugin subagent bodies too (and, per the same docs, now also in plugin skill bodies; #9354 is outdated for current versions). The variables are NOT exported to Bash-tool commands. A live throwaway-plugin echo test was not run (it needs a model call; live LLM runs are out of scope for this implementation), so the rendering relies on the documented behaviour; the design fallback (relative form + note) stays in the root/VS Code channels and the note is also kept in the plugin copy.
- To check before implementation: that `${CLAUDE_SKILL_DIR}` is substituted in plugin-provided skills in current Claude Code, and whether `${CLAUDE_PLUGIN_ROOT}` is substituted in plugin subagent bodies. The first is gating (task 1.1). If it is not substituted, the fallback is the root form plus the "relative to this skill's directory" note, which works after one self-correction (#11011).

### D3. Dependency declaration and version check
Each script starts with:
```
# /// script
# requires-python = ">=3.10"
# dependencies = ["robotframework>=7"]
# ///
```
`requires-python` follows the floor that `align-skill-names-with-spec` uses in `compatibility`. The RF import moves into a `_require_robot()` helper that is called after argument parsing. It checks `robot.version.VERSION` ≥ 7, and on failure it exits 3 with the stderr hints from D5. The `compatibility` text itself is owned by `align-skill-names-with-spec`. This change adds a test asserting that script-bearing skills mention Python and `robotframework>=7`.

### D4. Exit codes
| Code | Meaning | Raised by |
|---|---|---|
| 0 | completed (including empty results or partial source failures) | normal path |
| 1 | internal error | top-level `except Exception` → `error: internal: …` + `hint: re-run with --debug for a traceback` |
| 2 | usage | argparse, plus `parser.error(...)` replacing the `SystemExit("…")` calls |
| 3 | environment | `_require_robot()` |
| 4 | input not found or unloadable | missing/unparseable `output.xml`, all libdoc sources failed |

The two scripts do not share code (D8), so each script carries a small inline `_fail(code, error, *hints)` helper of about 10 lines. A `--debug` flag prints tracebacks.

### D5. Diagnostics format
stderr lines take the forms `error: …`, `warning: …` and `hint: …`. On any non-zero exit, stdout is empty. The existing JSON-on-stderr error goes away. The MCP server reads exceptions, not stderr, and agents read plain text better. Environment hints name `sys.executable`, suggest `uv run python <this script path> …`, and suggest `uv add robotframework` (or `uv add <library package>` for a library import failure, using a small name→package map: Browser → `robotframework-browser`, SeleniumLibrary → `robotframework-seleniumlibrary`, AppiumLibrary → `robotframework-appiumlibrary`, RequestsLibrary → `robotframework-requests`, REST → `RESTinstance`).

### D6. Bounding and file output
- **`rf_libdoc.py`.** `--max-doc-chars` defaults to 4000. That keeps typical keyword docs whole while cutting the ~60 KB SeleniumLibrary outliers. The cut is at a paragraph or line boundary and appends `\n\n[… truncated N chars; rerun with --max-doc-chars 0 for full text]`. The marker goes inside the existing `doc` string, so no key changes. `--limit` stays at 20.
- **`rf_results.py`.** `--limit` defaults to 50 and applies to `details` test entries (failed first, then by suite order) and `errors` entries. Each capped section gets an `omitted` integer (0 when nothing was cut). This is additive and `rf_results.py` has no schema spec yet. `--max-slowest-*` is unchanged.
- **`--json-out FILE`** on both scripts. The flag name avoids `rf_results.py --output` (input) and argparse prefix ambiguity. After writing, stdout gets `{"written": "<path>", "bytes": N, "mode": "<mode>"}`.

### D7. MCP server execution strategy
- **Script lookup.** `_SCRIPT_PATHS` is resolved as `<plugin_root>/skills/<skill>/scripts/<name>.py` (`__file__`-relative, as today).
- **Per call, in-process when possible.** If `importlib.util.find_spec("robot")` succeeds, the RF version is ≥ 7, and every requested library imports, the call keeps the current in-process path (fast, cached modules).
- **Otherwise, a subprocess in the project environment.** The server detects the project interpreter from the MCP server's CWD (the project root in Claude Code):
  1. `uv.lock`/`pyproject.toml` with `uv` on PATH → `uv run --frozen python`
  2. otherwise `.venv/bin/python` (`Scripts\python.exe` on Windows)
  3. otherwise `$VIRTUAL_ENV/bin/python`
  It then runs the script with `--json-out <tmp>` or captures stdout, with a timeout of 120 s, and maps exit codes 3/4 to MCP errors that carry the stderr hints.
- **Launch command.** `.mcp.json` keeps `python3` (the server only needs the `mcp` package), because the environment problem is solved per call.
- *Alternative:* launch the server with `uv run --project ${CLAUDE_PROJECT_DIR}`. Rejected: it requires the `mcp` package in every user project.

### D8. No shared helper module, no symlinks
Each script stays a single self-contained file. The little duplicated code (`_fail`, `_require_robot`) is cheaper than a cross-skill import, which would break per-skill packaging and zip distribution. `check-drift.sh` adds `find skills plugins/rf-agentskills/skills vscode-extension/skills -type l`, and any hit fails. Removing the existing libdoc symlink is done by `merge-libdoc-skills`, and this check keeps it from coming back.

### D9. Tests
- `tests/test_script_execution.py`: parametrized over both scripts and all three channel copies. It covers exit codes 0/2/3/4, stderr prefixes, empty stdout on failure, `--help` examples, `--help` without RF, `--json-out`, truncation, and the `omitted` counts.
  - Exit 3 is tested with a throwaway `python -m venv --without-pip` interpreter that has no RF.
  - The partial-load case uses `BuiltIn` plus `NoSuchLib`.
- `tests/test_skill_commands.py`: extracts fenced shell blocks from every SKILL.md (all channels), `agents/*.md` and hook messages. It asserts:
  - no bare `python scripts/` or `python3 "${CLAUDE_PLUGIN_ROOT}`;
  - the channel-specific form;
  - no `pip install`;
  - a PEP 723 block in each script;
  - script-bearing skills mention `robotframework>=7` in `compatibility`.
- A uv integration test (skipped when `uv` is absent): create a temp uv project with `robotframework`, run `uv run python <script> --library BuiltIn --search log`, and assert exit 0. It also asserts that `uv run python script.py` does not create an isolated PEP 723 environment, for example by checking `sys.prefix` against the project `.venv`.
- MCP server test: monkeypatch the in-process capability check to False and point CWD at a temp `.venv` fixture, then assert that the subprocess path returns the same JSON.
- Installer transform test: `substitute_skill_dir` renders absolute paths for non-Claude adapters.

## Risks / Trade-offs

- [`${CLAUDE_SKILL_DIR}` might not be substituted for plugin skills in some Claude Code versions] → Verify first (task 1.1). The fallback is the relative form plus the note (one extra self-correction turn), and the eval harness stops rewriting SKILL.md so it measures the real behavior.
- [`uv run` in a non-uv project creates or syncs an environment unexpectedly] → SKILL.md tells the agent to use `uv run` only when `uv.lock` exists or rf-setup chose uv, and to use the fallback line otherwise. The MCP server applies the same detection order.
- [`uv run` may resync the project environment (slow, network)] → The MCP subprocess uses `--frozen`. SKILL.md does not add `--frozen`, because agents may legitimately need a sync after `uv add`.
- [Doc truncation hides information the agent needed] → The marker names the flag that shows the full text. The default of 4000 is tuned against the eval task `narrow-libdoc-search-01`.
- [Removing flat plugin `scripts/*.py` breaks users' copied commands and any external references] → Mention it in CHANGELOG and release notes. The installer's upgrade path deletes stale files (via the orphan pruning from `retire-generator-skills`).
- [Subprocess fallback adds latency to MCP calls] → It only happens when in-process import is impossible. A library-importability cache is kept per server process.

## Migration Plan

1. Land after `retire-generator-skills` and `merge-libdoc-skills` (only `rf_libdoc.py` and `rf_results.py` remain, with no symlink).
2. Script changes (D3–D6) and tests.
3. Sync/installer/MCP changes (D2, D7), and regenerate channels with `scripts/sync-skills.sh`. `scripts/check-drift.sh` must pass.
4. Remove `_rewrite_plugin_root` for SKILL.md in the eval runner (keep it for JSON configs), then run the eval narrow tier for rf-libdoc and rf-results to confirm first-attempt path resolution.

Rollback: revert the sync rewrite rule and restore the flat plugin scripts. The script CLI changes are backward compatible except for exit-code values and the `--help` text.

## Open Questions

- The exact default for `--max-doc-chars` (4000) and for `rf_results.py --limit` (50). Tune them against eval token metrics once `strengthen-skill-eval-harness` reports per-task tokens. Neither value changes the specs.

## Implementation Notes

Adaptations made before implementation (this change was planned before `retire-generator-skills`, `merge-libdoc-skills` and `align-skill-names-with-spec` landed):

- **Paths.** Skills live in `skills/rf-<topic>/` in root, plugin (`plugins/rf-agentskills/skills/rf-<topic>/`) and VS Code (`vscode-extension/skills/rf-<topic>/`); there is no short-name map. Remaining scripts: `skills/rf-libdoc/scripts/rf_libdoc.py`, `skills/rf-results/scripts/rf_results.py`. `tests/test_libdoc_search.py` is now `tests/test_rf_libdoc.py`.
- **MCP tool names.** The results tool is `rf_results_analyze` (not `rf_results`); tool names are unchanged by this change.
- **Symlink check** (D8, task 4.3 part 1) already exists in `scripts/check-drift.sh` (added by `merge-libdoc-skills`, covering root, plugin skills + scripts and VS Code trees). This change adds only the command-form checks.
- **`requires-python`.** The `compatibility` text authored by `align-skill-names-with-spec` says "Python 3.8+". The scripts use PEP 604 annotations (`str | None`), which need 3.10 at runtime unless annotations are postponed. To keep the declared floor consistent with `compatibility` (D3), the scripts get `from __future__ import annotations` and `requires-python = ">=3.8"`.
- **Plugin rewrite rule.** `sync-skills.sh` rewrites only command occurrences (`python scripts/<name>.py` and `--script scripts/<name>.py`) to `"${CLAUDE_SKILL_DIR}/scripts/<name>.py"`, so prose mentions of `scripts/` stay untouched. The `uv run python` / `.venv/bin/python` / `poetry run python` prefixes are kept.
- **Standalone and fallback examples are prose.** The spec says every fenced shell command running a bundled script starts with `uv run python`. So the non-uv fallback line and the `uv run --script` standalone example (rf-results) go in prose (inline code), not in fenced blocks.
- **Installer and MCP server layout.** The installer stages the plugin's `servers/` under `<root>/rf-agentskills-files/`, and the skills go to agent-specific skill dirs. D7 resolves scripts `__file__`-relative as `<plugin_root>/skills/<skill>/scripts/<name>.py`. So the installer now also stages every `skills/<skill>/scripts/*` file under `rf-agentskills-files/skills/<skill>/scripts/` (support category) for adapters that ship the server. Without this, the installed MCP server (including Claude Desktop, which gets no skills) could not find the scripts once the flat `scripts/*.py` copies are gone. This is not new scope: it implements D7's lookup for the installer channel.
- **Adapter capability.** `expands_skill_dir = True` for `claude-code` (documented: personal/project skills expand it). It is False for `copilot` (VS Code: not documented), `codex`, `cursor`, `goose`, `opencode` and `claude-desktop` (no skills installed). Non-expanding adapters run `transforms.substitute_skill_dir` on every text file of an installed skill.
- **Hook reminder.** `maybe_remind_robot_tests.mjs` locates `rf_results.py` from `import.meta.url`: `<plugin>/skills/rf-results/scripts/rf_results.py` (plugin/eval layout) or `<rf-agentskills-files>/skills/rf-results/scripts/…` (installer layout). Both are the same relative path from `scripts/`: `../skills/rf-results/scripts/rf_results.py`.
- **Task 6.4** (live eval `--runs 3`) is not run: live LLM runs are out of scope for this implementation cycle. It is left unchecked and annotated as DEFERRED.

Decisions and deviations made during implementation:

- **RF import (D3).** `rf_libdoc.py` imports Robot Framework lazily in `_require_robot()`. `rf_results.py` subclasses `ResultVisitor` at module level, so it uses a guarded top-level import (`ResultVisitor = object` when RF is missing) plus `_require_robot()` after argument parsing. The behaviour is the same: `--help` and usage errors work without RF, and RF missing or older than 7 exits 3. The MCP server can still import both modules without RF.
- **Usage errors.** Both scripts subclass `ArgumentParser.error` so that usage errors print `error: …` plus `hint: … --help` (exit 2) instead of argparse's `usage:` block. That keeps the "all stderr lines are error:/warning:/hint:" rule. Unknown `--sections` names, negative `--limit` and malformed `--weights` are now usage errors too.
- **`omitted` shape (D6).** The spec requires an omitted count *per capped list*, so `details.omitted` is `{tests, failed_tests}` and `errors.omitted` is `{execution_errors, failed_test_messages, keyword_errors}`. These are objects of integers, not one integer per section. `--limit 0` means unlimited. `--json-out` summary `mode` is the libdoc `mode` for `rf_libdoc.py` and `"results"` for `rf_results.py`.
- **Truncation test fixture.** In the installed SeleniumLibrary, `Input Text`'s doc is 964 characters, under the 4000 default. The default-truncation test uses `Open Browser` (≈8.2 KB) and checks `Input Text` with an explicit `--max-doc-chars 300`. The "no matches" test uses the query `zzzzqqqqxxxx`, because `zzzz-no-match` tokenises to `match`, which does match BuiltIn keywords.
- **MCP interpreter detection.** A uv project is recognised by `uv.lock` (and `uv` on PATH), because `uv run --frozen` needs a lock file. A `pyproject.toml` without `uv.lock` falls through to `.venv` / `$VIRTUAL_ENV`, so the server never creates or syncs an environment as a side effect. Tool errors are returned as `{"error", "hints", "exit_code"}` JSON. The results and libdoc tools gained optional `limit` / `max_doc_chars` inputs, which pass through to the script flags.
- **Hook messages.** Only the script-related hook (`maybe_remind_robot_tests.mjs`) was changed. It also now says `uv run robot …`. The `pip install` block in `check_rf_environment.mjs` (environment setup, not script invocation) is owned by `modernize-plugin-agents-and-hooks` task 6.2 and was left alone.
- **CI.** The lint job now lints `plugins/rf-agentskills/skills/*/scripts/*.py`. The flat glob no longer matches any files and would make ruff fail. The plugin validation step asserts there are per-skill scripts and no flat `scripts/*.py`.
- **Changelogs.** There is no root or plugin CHANGELOG file. Entries went to `installer/CHANGELOG.md` (0.7.0 — Unreleased: Added / Changed / Changed (BREAKING)) and `vscode-extension/CHANGELOG.md` (2.0.0), which is the content/plugin channel changelog. No version bump.
