## Why

The plugin's four subagents and its hooks still describe the old catalog. After `retire-generator-skills`, `merge-libdoc-skills` and `align-skill-names-with-spec`, the subagents lose their generator steps. The new guidance skills (`rf-language` for tests, keywords, resources and variables; `rf-python-library` for Python libraries) then own that design knowledge. The subagents keep their own copies of that knowledge, and some copies are wrong:
- `rf-migration-guide` teaches `${name}: str` in `[Arguments]`. This is invalid syntax (Robocop `ARG05`, `robot --dryrun` error). The correct form is `${name: str}`, available from RF 7.3.
- `rf-keyword-consultant` lists `Run Keyword If`, `Set Variable` and `Create List` as the BuiltIn quick reference.
- `rf-debug-expert` recommends `Wait Until Keyword Succeeds` in its flakiness table, although its own constraints forbid it.

The validation hook catches broken syntax but not legacy syntax. An agent can still write `[Return]`, `Run Keyword If` or `Force Tags` and nothing tells it. Robocop's `DEPR` rules detect these constructs deterministically, and the hook already runs Robocop. The context-injection hook and the SessionStart check also still point to retired skills and to `pip install`.

## What Changes

- **Subagents become thin routers.** `rf-test-architect`, `rf-keyword-consultant`, `rf-migration-guide` and `rf-debug-expert` keep their roles: architecture decisions, keyword lookup, migration planning and failure diagnosis. They drop duplicated catalogs and syntax tables. Each one gets a short routing table to the skills that own the knowledge:
  - `rf-language` and `rf-python-library` for writing and design;
  - `rf-libdoc` and `rf-robotcode` for keyword lookup;
  - `rf-results` for reading test results;
  - the library skills for library-specific questions.
  
  All four subagents share one verification loop: write, then check keywords with libdoc, then `robot --dryrun`, then `robocop`, then run, then read the results. This builds on the generator-free workflow that `retire-generator-skills` writes and on the MCP-tool calls that `harden-skill-script-execution` writes. It does not redo either.
- **`rf-migration-guide` uses deterministic checks.** It uses `rf-language/references/migration.md` as its legacy-to-modern table and Robocop's `DEPR` rules as its checker:
  - inventory with `robocop check --select 'DEPR*'` and `--reports rules_by_id`;
  - burn the findings down file by file;
  - exit criterion: zero `DEPR` and zero error-severity findings, then a clean `robot --dryrun`.
  
  It keeps its library-migration tables (Selenium→Browser, Requests→RESTinstance), because they have no other home yet.
- **Deprecated-syntax check on write.** `validate_robot.mjs` classifies the output of its existing Robocop pass. It does not add a second Robocop run.
  - Error-severity findings block exactly as before (exit 2); this behaviour of the existing `rf-validation-hooks` spec is unchanged.
  - Deprecation findings only **warn**: they are reported as non-blocking additional context and never cause exit 2, including hard deprecations on lines the current edit touched (user decision 4, 2026-09-27).
  - Hard deprecations on touched lines are listed first, one per line with the modern replacement: `DEPR03`, `DEPR04`, `DEPR07`–`DEPR11` (`WITH NAME`, singular headers, `Force/Default Tags`, `Run Keyword If/Unless`, loop-exit keywords, `Return From Keyword`, `[Return]`). The modernization hints `DEPR05` and `DEPR06` (`Set * Variable` / `Create *` → `VAR`) follow; legacy lines the edit did not touch are summarized as counts per rule.
  - The warning text is capped in length. The same finding is not repeated in one session.
  - The project's Robocop config and Robocop's RF-version gating are respected.
  - `RF_AGENTSKILLS_DEPRECATION_CHECK=warn|off` controls the tier (default `warn`; any other value, including a legacy `block`, is treated as `warn`).
  - The hook stays silent when Robocop is missing, its output cannot be parsed, or it times out.
- **Hooks use the project interpreter.** The hooks prefer the project interpreter (`VIRTUAL_ENV`, then `<cwd>/.venv`) over `python_runtime.json` and `PATH`. Robocop then sees the project's Robot Framework version. The hooks never call `uv run`, because it can sync or reach the network.
- **Optional per-file dry run.** With `RF_AGENTSKILLS_FILE_DRYRUN=1`, the hook runs `robot --dryrun` on the edited suite file. It is off by default, reports as non-blocking context and has a time limit. The existing hook does not do a per-file dry run today; only the opt-in Stop tier runs a project-wide one.
- **Latency budget.** Enabling the deprecation tier adds ≤ 150 ms (p50) over the current hook on a 500-line file. Every spawned process has a timeout, and `hooks.json` declares hook timeouts.
- **Context injection.** `maybe_inject_rf_context.mjs` changes as follows:
  - the injected text routes by task: tests, suites, keywords, resources and variables → `rf-language`; Python libraries → `rf-python-library`; keyword signatures → `rf-libdoc` / `robotcode libdoc`. It ends with a one-line RF 7 syntax reminder;
  - the text stays within a fixed budget of ≤ 450 characters (about 80 tokens; today it is about 560 characters);
  - the regex drops the retired generator names and adds the new skill ids and RF section headers (`*** Keywords ***`, …).
- **SessionStart check.** `check_rf_environment.mjs` no longer prints `pip install` or `rfbrowser init` advice. It points to `rf-setup` and reports whether Robocop is available, because the deprecation checks depend on it.
- **Tests and evals.**
  - Hook tests cover the deprecation classification, the warn-only behaviour (never exit 2 for deprecations), touched-line scoping, the dedupe, the modes, silence when Robocop is missing or unparsable, timeouts, the injection budget and routing, and the regex.
  - A subagent lint test checks routing names against the skill catalog, the absence of retired names and legacy constructs, and each agent's size budget.
  - A new adversarial eval task, `adv-legacy-syntax-01`, uses a fixture whose existing resource file is written in legacy style. It asks for a new keyword "in the same style as the existing ones" and passes only when the new file has zero `DEPR` findings and passes dry-run.

Not changed: Stop-hook behavior. The deprecation tier runs only in `PostToolUse`, and the opt-in project tier keeps `robot --dryrun` + find-unused, so `stop-hook-safety` needs no delta.

## Capabilities

### New Capabilities
- `plugin-subagents`: what the four plugin subagents contain and how they route to skills. This covers the routing table, the ban on duplicated catalogs and legacy syntax, the shared verification loop, `rf-migration-guide`'s deterministic checker and exit criteria, portable bodies across the Claude Code, OpenCode and Cursor installs, and per-agent size budgets.
- `rf-session-context-hooks`: the `UserPromptSubmit` context injection (triggers, routing text, token budget, no retired names) and the `SessionStart` environment report (points to rf-setup, no `pip install`, reports Robocop availability).

### Modified Capabilities
- `rf-validation-hooks`: the changes are listed below.
  - Per-file validation also detects deprecated syntax as advisory warnings only, with touched-line scoping, bounded and de-duplicated output, and a `warn|off` mode switch.
  - Model-facing error feedback keeps its error-severity behaviour and states that deprecation findings never cause exit 2.
  - Graceful degradation adds timeouts, unparsable output and unsupported Robocop versions.
  - Interpreter resolution prefers the project environment.
  - The new requirements are an opt-in per-file dry run and a latency budget.

## Impact

- **Edited:**
  - `plugins/rf-agentskills/agents/{rf-test-architect,rf-keyword-consultant,rf-migration-guide,rf-debug-expert}.md`;
  - `plugins/rf-agentskills/scripts/{validate_robot,maybe_inject_rf_context,check_rf_environment}.mjs`;
  - `validate_robot_project.mjs` and `maybe_remind_robot_tests.mjs`, only for the shared interpreter helper;
  - new `plugins/rf-agentskills/scripts/_python_env.mjs`;
  - `plugins/rf-agentskills/hooks/{hooks.json,README.md}`;
  - `tests/test_hook_scripts.py`, new `tests/test_subagents.py`;
  - `eval/tasks/adversarial/adv-legacy-syntax-01.yaml`, a new fixture `eval/fixtures/sut-legacy-style/`, and a `select` param for the `lint_clean` grader in `src/rf_skill_eval/scoring/deterministic.py`;
  - plugin CHANGELOG.
- **Installer:** no code change. `_assets/` mirrors the plugin tree at build time. The subagent files are copied unchanged to Claude Code, OpenCode and Cursor, so the bodies must not depend on Claude-only variables.
- **Order:** this change lands after `retire-generator-skills`, `merge-libdoc-skills`, `align-skill-names-with-spec` and `harden-skill-script-execution`. All four edit the same agent files and hook text. This change rewrites the agent bodies on top of their final state and owns the final injection text. It also lands after, or in the same release as, `add-rf-language-skill` (which provides `references/migration.md` and the `rf_conventions` tool) and `add-rf-python-library-skill`. The routing names must exist in the catalog; the subagent lint test enforces this. The eval task depends on the `strengthen-skill-eval-harness` tri-state verdicts and `robot_dryrun` grader.
- **Users:** users who write legacy syntax get non-blocking warnings about it on edited lines; edits are never blocked because of deprecations. Teams that keep legacy syntax on purpose use the Robocop config (`ignore = ["DEPR08"]`) or set `RF_AGENTSKILLS_DEPRECATION_CHECK=off`.
