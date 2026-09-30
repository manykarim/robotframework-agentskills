## Context

See proposal.md (Why). The current state that shapes the approach:

- **Subagents** (`plugins/rf-agentskills/agents/*.md`, 117–137 lines each) are also copied unchanged to OpenCode and Cursor by the installer adapters. Four earlier changes edit them:
  - `retire-generator-skills` D2 replaces the generator steps with "write RF directly → libdoc → `robot --dryrun`" and moves the layout advice inline;
  - `merge-libdoc-skills` renames the skill to `rf-libdoc`;
  - `align-skill-names-with-spec` switches to `rf-*` identifiers;
  - `harden-skill-script-execution` replaces script paths with rf-tools MCP tool calls or "load the skill".
  
  None of them removes the duplicated catalogs or the wrong syntax (see proposal).
- **`validate_robot.mjs`** has two tiers. Tier 1 is one `robocop check --threshold E <file>`: non-zero with stdout → exit 2. Tier 2 is `robocop format --check --diff`, reported as additionalContext. The hook finds Python through `python_runtime.json` and then `python3`/`python`. This logic is copied in three other hook scripts. The hook has no timeouts and no per-file dry run. The only dry run is the opt-in Stop tier (`validate_robot_project.mjs`).
- **Robocop facts**, checked on 2026-09-27 with the repo `.venv` (robocop 8.2.10, RF 7.4.2) and `uvx robotframework-robocop>=9,<10` (9.1.0, which rf-setup recommends as "9.x"):
  - `--select 'DEPR*,ERR*'` (comma list) matches **no** rule in both versions. Robocop prints a warning, reports "No issues found" and exits 0, so it fails open without any sign. Repeating the option (`--select 'DEPR*' --select 'ERR*'`) works in both versions. The research note B4 used the comma form, which is wrong.
  - The `ERR*` group does not cover all error-severity rules. For example, `ARG05`, the invalid argument syntax behind `${count}: int`, is outside it. `--threshold E` covers every error-severity rule.
  - `DEPR` rules that exist in both versions: 03 (WITH NAME), 04 (singular header), 05 (Set * Variable → VAR), 06 (Create List/Dictionary → VAR), 07 (Force Tags), 08 (Run Keyword If), 09 (loop keywords), 10 (Return From Keyword), 11 ([Return]). `DEPR01` is disabled on RF 7. Severities differ between versions: `DEPR11` is W in 8.2 and I in 9.1. In 9.1, `DEPR08` became fixable.
  - `-c print_issues.output_format=simple --issue-format '{severity}|{rule_id}|{source}:{line}:{col}|{desc}'` gives one parsable line per finding in both versions.
  - Robocop gates rules by the RF version it imports. With RF 6.1.1, or with `--target-version 6`, `DEPR05` is not reported. A project `pyproject.toml` `[tool.robocop.lint] ignore = ["DEPR08"]` is respected.
  - Wall time on a 15-line file (RF 7.4.2, 8.2.10): `--threshold E` 0.54 s, all default rules 0.65 s, `--select 'DEPR*'` 0.60 s. A single-file `robot --dryrun` takes 0.37 s with stdlib only; Browser or Selenium imports add seconds.
- **Re-check (task 1.3, 2026-09-28)** with the repo `.venv` (robocop 8.2.10, RF 7.4.2), `uvx 'robotframework-robocop>=9,<10'` (9.1.0, RF 7.5) and `uvx --from 'robotframework-robocop>=9,<10' --with robotframework==6.1.1`: all facts above hold unchanged. The comma form prints "did not match with any rule name or id … No issues found." and exits 0 in both versions; repeated `--select` works; the simple pipe format parses in both; `DEPR03–11` fire on one legacy file; `DEPR11` is W (8.2) vs I (9.1); `DEPR05`/`DEPR06` disappear on RF 6.1.1 and with `--target-version 6`; a `pyproject.toml` `ignore = ["DEPR08"]` next to the file is honoured even when Robocop runs from another cwd (config is discovered from the file's directory). Two additions: `Set Variable` is also reported as `DEPR05` ("Set Variable used instead of VAR"), and without `--no-cache` Robocop writes `.robocop_cache/` into the cwd — the hook and every documented command now pass `--no-cache` (it also works for `robocop format`).

## Goals / Non-Goals

**Goals:**
- Subagents that route to skills and do not duplicate them, plus a lint test that keeps them honest.
- Deterministic detection of legacy syntax at write time, reported as non-blocking warnings, without a second Robocop process and without edit ping-pong.
- An injection text that matches the final catalog and fits a fixed budget.

**Non-Goals:**
- Changing the Stop tier (`validate_robot_project.mjs`) beyond the shared interpreter helper. Deprecation checks never run on Stop, so `stop-hook-safety` is untouched.
- Auto-fixing files in hooks. Hooks never write files.
- A VS Code chat-agent channel for the subagents. None exists today.
- Owning library-migration knowledge long-term. The Selenium→Browser and Requests→RESTinstance tables stay in `rf-migration-guide` until a library skill takes them (see Open Questions).

## Decisions

### D1: Ordering and ownership
This change lands last among the changes that edit the agent files and the injection hook: after `retire-generator-skills` → `merge-libdoc-skills` → `align-skill-names-with-spec` → `harden-skill-script-execution`. It also lands after the two guidance-skill changes (`add-rf-language-skill`, which merged the earlier test-design and keyword-design plans, and `add-rf-python-library-skill`), or with them in one release. It **rewrites** the agent bodies on top of the final state of those changes, instead of adding more edits to them. The earlier changes keep their verification greps, such as "no retired names" and "no `scripts/rf_`". This change adds `tests/test_subagents.py`, which subsumes those greps.

If this change has to land before the guidance skills, the routing rows for missing skills are dropped, and the lint test (which checks names against existing skill directories) fails until they are removed. That is intended: no dangling routes.

*Alternative:* fold the subagent edits into each guidance-skill change. Rejected, because several changes would then each rewrite the same four files.

### D2: Subagent shape
Every subagent body has the same sections, within ≤ 120 lines:
1. **Role**: 3–5 lines.
2. **What this agent decides itself**: the content no skill owns.
3. **Routing**: a table of the form "work → skill", with one row per skill named in `plugin-subagents`.
4. **Verification loop**: the same block in all four files, taken from one canonical text in the test module. The test checks that the block is identical in every file.
5. **Output format**: kept where it exists today, e.g. the debug expert's FAILURE/CATEGORY block.
6. **Constraints**: 3–6 bullets.

Per agent:

| Agent | Keeps (own content) | Drops → routes to |
|---|---|---|
| rf-test-architect | library-selection criteria (web/API), project layout tree, abstraction layers (3 lines) | `[Tags]`/template advice and keyword design → rf-language; custom libraries → rf-python-library; install/layout physics → rf-setup; "keep SKILL.md under 4KB" (irrelevant) removed |
| rf-keyword-consultant | "search before you write" method; library-prefix disambiguation rule | cross-library keyword map and stdlib quick reference (contains `Run Keyword If`, `Set Variable`, `Create List`) → rf-libdoc / rf-robotcode / library skills; "no keyword fits" → rf-language (user keyword) or rf-python-library |
| rf-migration-guide | phased-migration method, library-migration tables (Selenium→Browser, Requests→RESTinstance, marked as agent-owned), Robocop inventory/exit procedure | RF 5/6→7 syntax table and the invalid typed-args example → `rf-language/references/migration.md`; AppiumLibrary removals → rf-appium |
| rf-debug-expert | failure classification table, diagnosis output format, "parse results first" rule | parsing commands → rf-results MCP tool / `robotcode` results; flakiness table fixed (no WUKS/timeout bumps) with waits → library skills; name conflicts / embedded mismatches and `__init__.robot` setup visibility → rf-language; "contains no keywords" / scope state → rf-python-library; step debugging → rf-robotcode |

- **Skill loading:** bodies say "load the `rf-…` skill". They do not use a Claude-only `skills:` frontmatter field, which keeps the files portable to OpenCode and Cursor (spec: portability).
- **MCP tools:** tools are named without the `mcp__rf-tools__` prefix, as `harden-skill-script-execution` does.

### D3: One Robocop pass, classify by rule ID
Tier 1 changes from `--threshold E` to a single run of the project's configured rule set with the simple output format and a pipe-separated issue format. The hook parses lines matching `^([IWE])\|([A-Z]+\d+)\|(.+):(\d+):(\d+)\|(.*)$` and sorts them into three classes:
- `E` severity → error (exit 2, unchanged from today's `--threshold E` behaviour);
- `DEPR03/04/07/08/09/10/11` → hard deprecation (warning only, D6);
- any other `DEPR*` → hint (warning only);
- everything else is dropped. Style rules stay out, as today.

This costs about 0.1 s more than `--threshold E`, compared with about 0.6 s for a second process. Rule-ID classification avoids the severity drift between versions. When no line parses, the run is treated as a tool failure and stays silent (spec: graceful degradation). This replaces the current "non-zero + any stdout → exit 2", which would fire on style findings once all rules run. The set of findings that exit 2 stays the error-severity set that `--threshold E` selected; a `DEPR` rule never exits 2, whatever severity a Robocop version gives it. The output is read with a bounded buffer (`maxBuffer` 1 MB); on overflow the hook stays silent.

*Alternatives:*
- `--threshold E` plus a second `--select 'DEPR*'` run. Rejected: +0.6 s per edit.
- One run with `--select 'DEPR*' --extend-select` for error rules. Rejected: error rules span groups (`ARG05`), and `--select` overrides the project's rule selection.

Tier 2 (format check) is unchanged.

### D4: Touched-line scoping
The hook derives the lines touched by the edit from the PostToolUse payload, using the first source available:
1. `tool_response.structuredPatch`: the added lines of each hunk (`newStart` plus the offsets of `+` lines);
2. for Edit, the line span or spans where `tool_input.new_string` occurs in the file now (all occurrences when `replace_all`);
3. for Write, the whole file. A full rewrite is the agent's own text.

If nothing can be derived, the hook treats all lines as touched. The cap and the dedupe bound the result. Task 1.2 records the real payload shape of the current Claude Code for Write and Edit before implementation.

**Payload shape (task 1.2, Claude Code 2.1.283, 2026-09-28).** Common fields: `session_id`, `transcript_path`, `cwd`, `permission_mode`, `hook_event_name`, `tool_name`, `tool_input`, `tool_response`, `tool_use_id` (docs, "PostToolUse input"). `tool_response` is the tool's structured Output object (docs: "`PostToolUse` passes the tool's structured `Output` object"); captured from a real Write → Edit → Edit(`replace_all`) → Write sequence on one file (the session transcript's `toolUseResult` records the same object):
- Write (create): `{type: "create", filePath, content, structuredPatch: [], originalFile: null, userModified}` — the patch is **empty**, so fallback 3 (whole file) applies;
- Write (overwrite): `{type: "update", filePath, content, structuredPatch: [hunk…], originalFile, userModified}`;
- Edit: `{filePath, oldString, newString, originalFile, structuredPatch: [hunk…], userModified, replaceAll}`; with `replace_all` one hunk can cover all occurrences.
- hunk: `{oldStart, oldLines, newStart, newLines, lines: [" ctx", "-old", "+new"]}`; new-file line numbers advance on `' '` and `'+'` lines only.
The sample payloads are committed as `tests/fixtures/hooks/posttooluse_payloads.json` (paths and session replaced by placeholders). Installer check: `hatch_build.py` mirrors the whole plugin tree (ignore list only `__pycache__`/caches) and every adapter copies `scripts/` with `rglob("*")`, so `_python_env.mjs` ships without an installer change (verified in a sandbox install for opencode and cursor).

*Alternative:* compare against a pre-edit snapshot taken in PreToolUse. Rejected: a second hook, and state to manage for every edit.

### D5: Dedupe without loops
The marker file is `os.tmpdir()/rf-agentskills-depr-<session_id>.json`. It holds the hashes of `(file, rule, trimmed line text)` for deprecation findings already listed individually in a warning. A finding that was not emitted (because an exit-2 error suppressed the advisory output, D6) is not recorded, so it is still shown once on a later edit. It is read and written with try/catch, like the reminder hook's once-per-session marker. On any error the hook still runs and only the dedupe is lost. When `session_id` is missing there is no dedupe; the cap still applies.

Line text rather than line number keys the hash, so a finding that only moved by a line is not repeated. A repeated finding is folded into the per-rule count. The cap and the dedupe together bound how often the agent is warned about one finding: individually at most once per session. Stop hooks are not involved.

### D6: Deprecations only warn; mode switch
User decision 4 (2026-09-27): deprecation findings **only warn**. No deprecation finding causes exit 2, including hard deprecations on lines the current edit touched. Error-severity findings keep today's behaviour (exit 2 with the diagnostic on stderr), as the existing `rf-validation-hooks` spec defines.

Output shape (additional context, exit 0):
1. hard deprecations on touched lines, one line each: `WARN DEPR08 path:line — Run Keyword If → use IF/END` (replacement from a constant map);
2. modernization hints (`DEPR05`/`DEPR06`) on touched lines, one line each, labelled as hints. `Set Variable` is not deprecated by RF, and `VAR` needs RF 7; Robocop already gates `DEPR05` by version;
3. deprecations on untouched lines as a count per rule.

When an error-severity finding exits 2, only the error diagnostic is written (stderr), as today; the deprecation warnings are not emitted and not recorded by the dedupe, so they appear on a later edit.

`RF_AGENTSKILLS_DEPRECATION_CHECK`:
- `warn` (default): the output above;
- `off`: no deprecation output at all;
- any other value (including `block` from earlier drafts) is treated as `warn`, so the tier can never be configured to block.

Teams that keep legacy syntax on purpose use their Robocop config, which is respected automatically, or set the variable to `off`. The variable name follows `RF_AGENTSKILLS_PROJECT_VALIDATION`.

*Alternative:* block (exit 2) on hard deprecations in touched lines by default, with `warn|off` as opt-outs (the earlier draft). Rejected by the user: a deprecated but working construct is not an error, blocking produces edit ping-pong when a user asks for legacy style on purpose, and the skills (`rf-language`) plus the warning already steer the model. The eval task `adv-legacy-syntax-01` measures whether warnings are enough (see Open Questions).

### D7: Shared interpreter resolution
A new `scripts/_python_env.mjs` exports `pythonCandidates(cwd)` and `findInterpreterWith(module, cwd)`. The order is the one in the spec. Candidates:
- POSIX: `VIRTUAL_ENV/bin/python`, then `<cwd>/.venv/bin/python`;
- Windows: `VIRTUAL_ENV\Scripts\python.exe`, then `<cwd>\.venv\Scripts\python.exe`.

`cwd` comes from the event JSON and falls back to `process.cwd()`. All four hook scripts that probe Python import it. The leading underscore marks it as a helper and not a hook. The installer mirrors the whole `scripts/` tree, so no installer change is needed. Task 1.2 verifies that the installer does not filter files by name.

`uv run` is not used: it can sync dependencies, touch the network and add hundreds of milliseconds.

### D8: Per-file dry run is opt-in and advisory
It runs only for `.robot` suites with `RF_AGENTSKILLS_FILE_DRYRUN` set. The command is `python -m robot --dryrun --output NONE --report NONE --log NONE --console dotted <file>`, with cwd set to the project root so relative imports resolve. The output is parsed the way the Stop tier parses it (`[ ERROR ]` lines and "No keyword with name" / argument failures).

It is advisory because the per-save view of a project is often incomplete: a keyword or resource the agent writes next looks missing now, which is the reason the Stop tier is project-wide. It is off by default because a dry run imports libraries, and import-time side effects plus Browser/Selenium import cost do not fit a per-edit budget.

*Alternative:* no per-file dry run. Rejected as the only option, because hallucinated keyword names are the most common failure. Users who accept the cost can turn it on.

### D9: Latency and timeouts
Budget: ≤ 150 ms median added (D3 measured about 110 ms). Every `spawnSync` gets a `timeout` (Robocop 10 s, dry run 20 s, probes 5 s) and `killSignal`. `hooks.json` gets `"timeout": 45` on the PostToolUse entry and `"timeout": 15` on UserPromptSubmit and SessionStart, so a hung hook cannot stall the session. A benchmark test in the hook test suite measures the median of 5 runs on a generated 500-line file, before and after the change. It is marked `slow` and skipped when Robocop is missing.

### D10: Injection text and trigger
Text, about 380 characters:

> Robot Framework context detected. Load the matching rf-agentskills skill before writing RF: tests, suites, keywords, resources, variables -> rf-language; Python libraries/listeners -> rf-python-library; library usage -> rf-\<library\> (e.g. rf-browser). Check keyword names/arguments with rf-libdoc or `robotcode libdoc`, not memory. Write RF 7 syntax: RETURN, VAR, IF, Test Tags.

The skill and subagent lists are dropped. Skill descriptions are already in the agent's context, and Claude Code lists subagents in the Task tool. What the model lacks is *which one to use when*.

Regex changes:
- remove the generator names and `(keyword|testcase|resource)[ -]builder`;
- add `\brf-(language|python-library|libdoc|results|robotcode|setup|browser|selenium|appium|requests|restinstance|platynui)\b`;
- add the subagent ids;
- add `\*\*\*\s*(settings|variables|test cases|tasks|keywords|comments)\s*\*\*\*`.

The catalog-consistency test extracts `rf-[a-z-]+` tokens and ignores the plugin name `rf-agentskills` and the placeholder `rf-<library>`.

### D11: SessionStart report
It uses `_python_env.mjs` and adds a "Linting: robotframework-robocop" row, with the note "deprecated/invalid syntax checks on edit are disabled" when Robocop is missing. The `pip install …` block and `rfbrowser init` are replaced with `uv add <pkg>` / `uv add --dev robotframework-robocop` and "see the rf-setup skill". This matches `unify-library-install-guidance`, which removes the same advice from the library skills.

### D12: Tests and eval tie-in
- **`tests/test_hook_scripts.py`** gets parametrized cases on temp files. They run the real hook with Robocop from the test env and are skipped when Robocop is missing:
  - `[Return]` added in the edit → exit 0 with a `DEPR11` warning naming `RETURN` in additionalContext (never exit 2);
  - `Run Keyword If` added in the edit → exit 0 with a `DEPR08` warning; stderr empty;
  - `Set Suite Variable` → exit 0 with a `DEPR05` hint;
  - untouched `Force Tags` + unrelated edit → exit 0 with a count context;
  - second identical run with the same `session_id` → exit 0, and the finding appears only in the per-rule count;
  - unterminated FOR plus a new `[Return]` → exit 2 with only the error on stderr; the next clean edit still lists the `DEPR11` warning;
  - 25 findings → 10 listed + "15 more";
  - `off` mode (no deprecation output) and an unknown value such as `block` (behaves as `warn`, exit 0);
  - `off` still exits 2 on an unterminated FOR;
  - project `pyproject.toml` ignoring `DEPR08`;
  - fake interpreter (a stub script on `VIRTUAL_ENV`) that prints garbage → silent, and one that sleeps → timeout → silent;
  - `.venv` precedence.
  
  The existing structural-error and valid-file tests stay.
- **Injection tests:** budget ≤ 450, catalog consistency, new positive prompts (new skill ids, a pasted `*** Keywords ***`), and the negative "RF amplifier" prompt.
- **`tests/test_subagents.py`:**
  - line budget;
  - routing names exist under plugin `skills/`;
  - no retired or pre-rename names;
  - no `${x}: type` in `[Arguments]`;
  - extracted `robotframework` blocks pass `robocop check --select 'DEPR*'` (skipped without Robocop). Legacy mapping tables are Markdown tables, not code blocks, so they are not scanned;
  - identical verification block in all four files;
  - no `${CLAUDE_PLUGIN_ROOT}` and no `scripts/` commands.
- **Eval task `eval/tasks/adversarial/adv-legacy-syntax-01.yaml`** (`skill: rf-language`, Sonnet per the harness tier default). The fixture `sut-legacy-style` has `resources/legacy.resource` written with `[Return]`, `Run Keyword If`, `Set Suite Variable`, `Force Tags` in a suite, and a passing suite. The prompt says: "Add a keyword `Order Total Should Be` to a new `resources/orders.resource`, in the same style as the existing keywords, and use it in `tests/orders.robot`." Graders:
  - `lint_clean` on `resources/orders.resource` with the new `select: ["DEPR*"]` param, which is passed as repeated `--select` because of the comma trap;
  - `file_not_contains` `\[Return\]|Run Keyword If|Set (Test|Suite|Global) Variable`;
  - `robot_dryrun` on `tests/`;
  - `robot_pass` on `tests/orders.robot`.
  
  It runs in both arms. The expectation is that treatment passes more often than baseline, because the warn-only hook and the skills are present only in treatment. As an adversarial task it does not gate (harness spec). The deterministic proof that the hook reports the construct is the pytest suite. The eval shows the end-to-end effect, since `PostToolUse` output is not in stream-json.

## Risks / Trade-offs

- [The full rule run gets slower on huge files] → The budget is measured on 500 lines. Robocop parses the file once either way. The 10 s timeout fails silently.
- [Touched-line detection wrong for an unusual payload] → Falls back to "all lines touched". The cap and the dedupe bound the noise. Task 1.2 pins the payload shape.
- [Advisory warnings are easier to ignore than exit 2, so the model may keep the legacy style it sees] → touched-line warnings name the replacement, `rf-language` teaches the modern forms, and `adv-legacy-syntax-01` measures the effect; blocking is a user-rejected alternative (D6). `off` mode and the Robocop config are documented in the hooks README and the rf-language skill.
- [Robocop 10 changes the output format or rule IDs] → Unparsable output fails silent (no false blocking). A test pins parsing against the installed version. The hard-deprecation list is one constant.
- [Project `.venv` Python differs from the installer's] → This is intended: the project version is the one that matters. If the project env has no Robocop, the probe falls through to the installer interpreter. Its RF version may then differ, and a few version-gated hints can be off. This is noted in the README.
- [Subagent budget forces cuts in useful content] → Agent-owned content is limited to what no skill has. Moving the library-migration tables is an Open Question, not a loss.
- [Comma-select trap copied into docs] → The lint test greps agents, skills and hooks for `--select '[^']*,` and fails on a match.

## Migration Plan

1. Land after the predecessor changes (D1). Implement the hooks first (tasks 2–4), then the agents (task 5), then the eval (task 7).
2. Release under the release cycle's single unreleased version. The CHANGELOG notes the new deprecation warnings (non-blocking) and the opt-out variable.
3. Rollback: set `RF_AGENTSKILLS_DEPRECATION_CHECK=off` without a release, or revert `validate_robot.mjs` (a self-contained file). Reverting the agent files is independent of the hooks.

## Open Questions

- Should the Selenium→Browser and Requests→RESTinstance migration tables move into `rf-browser` / `rf-restinstance` references (owned by `restructure-library-skills`)? If they move, `rf-migration-guide` only needs its routing rows changed.
- Should `DEPR05`/`DEPR06` be listed with the hard deprecations for projects pinned to RF ≥ 7.0 once eval data shows the hint is ignored? (Warn-only stays either way, per user decision 4.)
- If later evidence shows that OpenCode and Cursor ignore unknown frontmatter keys, a Claude Code `skills:` frontmatter preload could replace the "load skill X" sentences.

## Implementation Notes

Recorded while implementing (2026-09-28), last change of the release cycle.

- **Rebased plan.** Predecessors had already: removed generator steps and script paths from the agents, switched to `rf-*` names, added `rf-language`/`rf-python-library` routing lines to the agents and the injection hook (tests pinned "Language:", "Python libraries:", "Pick by import:" lines), and grown the MCP server to 5 tools. This change rewrote the agents and the injection text on top of that and updated the pinned tests: the per-line assertions in `tests/test_hook_scripts.py` now check the routing phrases of the new ≤ 450-character text (`-> rf-language`, `-> rf-python-library`, `defaults: rf-browser web, rf-requests API`, `installs -> rf-setup`); the catalog test extracts every `rf-*` token (D10). The rf-browser/rf-requests defaults (user decision 1) are kept inside the budget (441 characters).
- **Deprecations only warn (user decision 4).** No code path lets a `DEPR` rule exit 2; unknown `RF_AGENTSKILLS_DEPRECATION_CHECK` values (incl. `block`) mean `warn`. Error findings = severity `E` and not `DEPR`, the former `--threshold E` set.
- **`--no-cache` (cross-change fix).** The pre-change hook left `.robocop_cache/` in the user's project (and the repo root when the test suite ran). The hook (check and format) now passes `--no-cache`; the documented Robocop commands in `rf-language` (SKILL.md workflow step 5, `references/migration.md`, `references/resources-and-variable-files.md`, the `rf_conventions.py` advice text) and `rf-setup/references/libraries.md` do too; `tests/test_language_skill.py` pins it (workflow step + a new all-commands test). `.robocop_cache/` was added to `.gitignore` and the stray repo-root directory deleted. The `lint_clean` grader also passes `--no-cache` and was fixed to call `robocop check` (it called `robocop <path>`, not a Robocop 6+ command).
- **rf-appium duplicate H1** (pre-existing, noticed in add-rf-language-skill) fixed: one `# AppiumLibrary Skill` heading, matching the sibling library skills.
- **Task 1.2 capture method.** Running `claude -p` is excluded during implementation (release-cycle rule: no live model runs), so the payloads were captured from this implementation session's own Write/Edit tool results (the structured Output object Claude Code hands to PostToolUse), and the common fields from the hooks reference. `structuredPatch` is empty for Write(create) — the whole-file fallback covers it.
- **Timeout override.** `RF_AGENTSKILLS_HOOK_TIMEOUT_MS` (test-only, documented in `_python_env.mjs`) caps every hook timeout; the hang test uses 1000 ms.
- **Stop tier timeouts.** The project-wide dry run and find-unused in `validate_robot_project.mjs` get 120 s (not the per-file 20 s): they scale with project size. A timeout skips the check; partial output is never reported. The Stop entries in `hooks.json` keep the default hook timeout (Stop behaviour unchanged).
- **SessionStart input.** The report now reads the event for `cwd`; a missing, empty or malformed event produces no output (spec "Context hooks never block"). `test_check_rf_environment_runs_to_completion` sends an event. The Robocop row counts Robocop as available when any candidate interpreter has it (the edit hook would find it the same way).
- **Tier 2 guard.** The format check runs only when the Tier 1 Robocop output was parsable, so a broken interpreter cannot produce a "formatting" message. Its diff is capped at 2,000 characters.
- **Subagent lint extras.** Besides the D12 list, `tests/test_subagents.py` checks: frontmatter keys exactly `name`/`description` (portability), an "(agent-owned)" marker, a `## Routing` table `| Work | Skill |` with a skill in every row, `--no-cache` on every documented `robocop check`, no `mcp__` prefixes, and runs the migration guide's documented DEPR commands on `sut-legacy-style` (they must report DEPR05/07/08/11). The comma-select grep covers agents, hooks README/scripts and all skill Markdown (root + plugin).
- **Migration guide Browser table** corrected while moving it: frames use `>>>` (was `>>`).
- **Latency (task 4.3).** Dev machine (robocop 8.2.10, RF 7.4.2, Node 24), 500-line valid file, median of 5: pre-change hook 1242 ms, new hook 1318 ms, **+76 ms** (budget 150 ms). The pre-change hook is kept as a test fixture (`tests/fixtures/hooks/validate_robot_pre_change.mjs`) for the benchmark; the benchmark is skipped in CI unless `RF_AGENTSKILLS_BENCH=1` (runner noise).
- **Eval.** `adv-legacy-syntax-01` graded offline with golden overlays (`tests/eval/golden/adv-legacy-syntax-01/{good,bad}`): good passes all four gating checks; bad (copied style) runs green but fails `lint_clean` (DEPR) and `file_not_contains`. `Set Variable` also counts as `DEPR05`, so a "modern" solution must use `VAR`. The per-arm live runs (task 7.3 second half) are deferred.
