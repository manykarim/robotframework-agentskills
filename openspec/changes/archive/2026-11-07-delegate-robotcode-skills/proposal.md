## Why

The RobotCode project now publishes its own agent plugin (`robotcode@robotframework-agent-plugins`, robotcode 2.8.0). Its single `robotcode` skill covers discovery, runs, `doc` keyword lookup, `results` (summary/show/log/stats/diff), `analyze code`, `robot.toml`/profiles, the REPL and `robot-debug`. That overlaps about 85-95% with our `rf-robotcode`, `rf-libdoc` and `rf-results`. The bundled `rf_libdoc.py` and `rf_results.py` scripts existed only because older robotcode lacked these commands.

Shipping both makes two skills compete for the same prompts, and they give conflicting advice: we say "pipe the REPL", upstream says "drive it in a terminal". It also doubles maintenance. The goal is a focused rf-agentskills plugin that sits next to the robotcode plugin: robotcode owns everything about driving the CLI, and we own Robot Framework syntax, Python libraries, the test libraries, setup, validation hooks and the design and diagnosis subagents.

## What Changes

- **BREAKING** Remove the skills `rf-robotcode`, `rf-libdoc` and `rf-results` from every channel: root `skills/`, the plugin, installer assets, Claude Desktop archives, eval tasks, triggers and baselines. Remove their scripts `rf_libdoc.py` and `rf_results.py`. The catalog goes from 12 to 9 skills.
- **BREAKING** Require the robotcode CLI as a documented prerequisite: `robotcode[all]>=2.8` in the project's Python environment. This is documented only, with no plugin dependency in any agent:
  - `rf-setup` states it as a prerequisite step and installs it.
  - Every skill's `compatibility` field names it.
  - README and plugin README point to the robotcode plugin as the recommended companion, with per-agent install commands.
  - `[all]` is chosen because it alone bundles `runner` (run, discover, results, libdoc), `analyze`, `repl` (`doc`, `robot-debug`) and Robocop, which our hooks use.
- Skills and subagents call robotcode commands inline (`robotcode doc keyword …`, `robotcode results …`, `robotcode analyze code …`), so they work whether or not the robotcode plugin is installed. Companion Skills tables point to the robotcode plugin's `robotcode` skill for CLI mechanics instead of to the removed skills.
- Per-file validation hook: the blocking error tier moves from Robocop error severity to `robotcode analyze code`. It blocks on syntax, model and argument errors. Unresolved keywords and variables are advisory on edit and blocking when re-checked at Stop. Robocop stays for the advisory deprecation and formatting tiers. The opt-in project tier uses `robotcode analyze code --collect-unused` instead of `robot --dryrun` plus `robotframework-find-unused`.
- Context hooks:
  - SessionStart checks for robotcode, not only Robocop, and suggests the robotcode plugin when it is missing.
  - UserPromptSubmit and the Bash error hints stop naming the removed skills.
- **BREAKING** Remove the `rf-keyword-consultant` subagent. `robotcode doc` answers its job directly.
- Rewrite `rf-debug-expert` as a read-only diagnostician:
  - It follows the robotcode skill's failing-test workflows.
  - It keeps its failure taxonomy, flakiness table, report format and rules.
  - It adds "never weaken an assertion, expected value or tag" and "one debugger at a time".
  - It has read-only tools and returns a report instead of editing.
- Tighten `rf-test-architect` and `rf-migration-guide`:
  - Descriptions name situations.
  - The shared verification loop uses `robotcode analyze code` and longname-scoped runs (`-bl`).
  - Tool lists are explicit where the agent format supports them.
- Before `rf-robotcode` is deleted, re-check its gotchas that upstream does not document on robotcode 2.8.0, and file the ones that still reproduce with the robotcode plugin repo.
- Content version 3.0.0 (plugin and marketplace), installer 0.8.0. The changelogs carry migration notes.

## Capabilities

### New Capabilities
- `robotcode-prerequisite`: the documented robotcode CLI requirement (package, extras, version floor, where it is stated), the recommended-companion relationship with the robotcode plugin, the no-plugin-dependency rule, and handing robotcode traps upstream.

### Modified Capabilities
- `robotcode-skill`: retired. All requirements are removed because the skill is no longer shipped.
- `libdoc-skill`: retired. All requirements are removed.
- `rf-script-output`: retired. Its requirements describe the `rf_libdoc.py`/`rf_results.py` output contract.
- `skill-catalog`: the removed skills join the retired list. The retirement is released as a breaking change, and keyword lookup and results reading point to robotcode.
- `setup-skill`: robotcode is a prerequisite step with `robotcode[all]>=2.8`. Library rows no longer name `rf-robotcode`, and the companion section points to the robotcode plugin.
- `rf-validation-hooks`:
  - The per-file error tier uses `robotcode analyze code`.
  - Degradation and the interpreter rules cover robotcode.
  - The project tier uses `analyze code --collect-unused`.
  - The latency budget is updated.
- `rf-session-context-hooks`:
  - The injection routes keyword lookup and results to robotcode commands.
  - The trigger list drops the removed skills.
  - The environment report checks robotcode.
- `plugin-subagents`:
  - Three subagents remain.
  - The verification loop uses robotcode.
  - `rf-debug-expert` is read-only and returns a report.
  - Tool restrictions are set per agent format.
- `agent-variants`: Codex and OpenCode receive three subagents.
- `skill-triggering`: the rf-robotcode/rf-libdoc/rf-results boundary and its cues are removed, and the trigger sets are re-baselined with the robotcode plugin installed alongside ours.
- `library-skill-structure`:
  - The agent workflow and the libdoc rule use `robotcode doc`.
  - The workflow has no script-skill fallback.
- `language-skill`:
  - The workflow uses `robotcode doc` and `robotcode analyze code`.
  - The companion rows and trigger near-misses no longer name the removed skills.
- `python-library-skill`: the workflow lists keywords with `robotcode doc keywords`.
- `skill-script-execution`: drops the rf-libdoc/rf-results examples. The rules still apply to the remaining bundled scripts.
- `skill-metadata-conformance`: the compatibility rule names robotcode, and examples refer to remaining skills.
- `claude-desktop-distribution`: the archive examples use a remaining skill.

## Impact

- **Content:**
  - `skills/`: 3 skill trees removed; the other 9 skills' SKILL.md, compatibility and Companion tables updated.
  - `plugins/rf-agentskills/`: skills, agents, hooks and README updated.
  - The `variants/` subagents are regenerated.
  - `installer/src/rf_agentskills/_assets/` is resynced.
- **Hooks:** `validate_robot.mjs`, `validate_robot_project.mjs`, `check_rf_environment.mjs`, `maybe_inject_rf_context.mjs`, `rf_error_hints.mjs`, `_python_env.mjs` (robotcode resolution) and `hooks/README.md`.
- **Installer:**
  - Upgrades remove the retired skill directories.
  - The hooks README's `rf-agentskills[validation]` install line is dropped: no such extra exists, and the validation tools belong in the project environment.
  - The Claude Desktop archive list shrinks.
- **Tests:** skill, script and subagent tests for the removed components are deleted or adjusted; hook tests are rewritten for the robotcode error tier; drift and sync tests are updated.
- **Eval:**
  - Removed: the narrow tasks for the removed skills, their trigger sets and their baseline entries.
  - Re-measured: trigger baselines for the remaining skills, with the robotcode plugin installed alongside ours.
- **Docs:** README, RELEASING, both CHANGELOGs, and `docs/installer/docker/checks/claude-code.sh`.
- **Dependencies:** users need `robotcode[all]>=2.8` in their project environment. That extra also pulls in Robocop, so Robocop is no longer a separate install recommendation.
- **External:** issues or PRs to `robotcodedev/robotframework-agent-plugins` for the gotchas that still reproduce. No changes to their repo are required for this change to ship.
