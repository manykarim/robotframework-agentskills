# rf-agentskills hooks

This plugin defines five Claude Code lifecycle hook scripts across four
events. Two (`SessionStart`, `PostToolUse`) run unconditionally; three
(`UserPromptSubmit`, and two on `Stop`) consult the session or an
environment flag before deciding to do anything.

All are **cross-platform Node.js** scripts (`.mjs`). They run
identically on Linux, macOS, and Windows — no `.sh`/`.ps1` parity to
maintain. This follows the cross-platform-hooks guidance at
<https://claudefa.st/blog/tools/hooks/cross-platform-hooks>:

> Invoke Node.js directly in your Claude Code hooks config. This works
> on Windows, Linux, and macOS. Claude Code requires Node.js, so `node`
> is always available.

The installer probes `node` on PATH at install time; if Node is not
present, the hooks block is skipped with a clear `post_install` note
rather than written-and-broken.

| Event | Script | Always fires? | Cost when no-op | Cost when active | Hook timeout |
|---|---|---|---|---|---|
| `SessionStart` | `scripts/check_rf_environment.mjs` | yes | — | ~0.5–1 s (import probes) | 15 s |
| `PostToolUse` (matcher: `Write\|Edit`) | `scripts/validate_robot.mjs` | only on Write/Edit | ~30ms (file extension check) | ~1–1.5 s on a 500-line file (one Robocop check + format check); +0.4 s or more with the opt-in dry run | 45 s |
| `PostToolUse` (matcher: `Bash`) | `scripts/rf_error_hints.mjs` | only on Bash | ~30 ms (text scan) | ~30 ms | 10 s |
| `UserPromptSubmit` | `scripts/maybe_inject_rf_context.mjs` | always invoked, conditional injection | ~30ms (regex over prompt) | same (≤ 450-character text) | 15 s |
| `Stop` | `scripts/maybe_remind_robot_tests.mjs` | always invoked, conditional reminder | ~30ms (chunked grep over transcript) | same | default |
| `Stop` | `scripts/validate_robot_project.mjs` | only when `RF_AGENTSKILLS_PROJECT_VALIDATION` is set | ~0ms (env-flag check) | project dry run + find-unused (120 s cap each) | default |

Every process a hook starts has a timeout (Robocop 10 s, per-file dry run
20 s, interpreter probes 5 s, project-wide checks 120 s). A timeout skips that
check silently. `scripts/_python_env.mjs` is a shared helper, not a hook.

## Validation hooks (what catches broken Robot Framework code)

Two scripts validate the Robot Framework files the agent writes, at two
different points in the lifecycle. Both are **optional** — they degrade
to a silent no-op when their underlying tools aren't installed. Install
the tooling into the project environment (see the rf-setup skill), or into
the installer's environment with the `validation` extra:

```bash
uv add --dev robotframework-robocop        # project environment (preferred)
uv tool install "rf-agentskills[validation]"   # installer env: robotframework-robocop + robotframework-find-unused
```

### Tier 1 + 2 — per file, on every write (`validate_robot.mjs`)

Fires from `PostToolUse` after a Write/Edit of a `.robot`/`.resource` file.

- **Tier 1 — one Robocop pass, classified by rule ID.** Runs
  `robocop check --no-cache` once, with the **project's configured rule set**
  and a parsable issue format
  (`-c print_issues.output_format=simple --issue-format '{severity}|{rule_id}|{source}:{line}:{col}|{desc}'`).
  Each finding is sorted into one class; everything else (style rules such as
  `DOC03`) is dropped, as before:
  - **Errors** — error severity (`E`), not a `DEPR` rule: invalid
    `FOR`/`IF`/`TRY` syntax, argument errors, duplicate definitions, imports
    Robocop can see are broken. This is the set the former `--threshold E` run
    selected, and errors **block exactly as before**: the diagnostic goes to
    **stderr and the hook exits 2**, which feeds it back to the agent (see "the
    exit-2 exception" below).
  - **Hard deprecations** — `DEPR03` `WITH NAME`, `DEPR04` singular section
    headers, `DEPR07` `Force/Default Tags`, `DEPR08` `Run Keyword If/Unless`,
    `DEPR09` loop-exit keywords, `DEPR10` `Return From Keyword*`, `DEPR11`
    `[Return]`.
  - **Modernization hints** — `DEPR05` `Set Test/Suite/Global Variable` →
    `VAR`, `DEPR06` `Create List/Dictionary` → `VAR`, and any other `DEPR` rule.

  **Deprecations only warn.** They are reported as non-blocking
  `additionalContext` (exit 0) and never cause exit 2 — not even a hard
  deprecation on a line the current edit wrote. Classification uses the rule
  ID, not the severity (`DEPR11` is W in Robocop 8.2 and I in 9.1).
  - **Touched lines** are listed individually, hard deprecations first, each
    with file, line and the modern replacement (`WARN DEPR08 x.robot:12 —
    Run Keyword If → use IF/ELSE/END`). Touched lines come from
    `tool_response.structuredPatch` (the `+` lines of each hunk), else the
    lines where an Edit's `new_string` now occurs, else the whole file (Write
    create). Deprecations on other lines are summarized as a count per rule.
  - **Cap:** at most 10 listed findings plus "N more omitted", at most 2,000
    characters.
  - **Dedupe:** a finding listed once in a session (`session_id`; key = file,
    rule and trimmed line text) is only counted afterwards. The marker is
    `<tmpdir>/rf-agentskills-depr-<session_id>.json`; if it cannot be written,
    only the dedupe is lost. When an error exits 2, the deprecation warnings are
    neither written nor recorded, so they appear on the next clean edit.
  - Robocop's gating by Robot Framework version applies (a project on RF 6.1
    gets no `VAR` hint), and so does the project's Robocop config.
  - If Robocop is missing, times out (10 s), or prints nothing parsable while
    failing, the tier is silent — a tool failure is never a finding.
- **Tier 2 — formatting drift:** runs `robocop format --no-cache --check --diff`.
  Purely informational — surfaces the proposed reformat as `additionalContext`
  (exit 0). Formatting differences **never** cause exit 2.
- **Opt-in per-file dry run:** with `RF_AGENTSKILLS_FILE_DRYRUN=1`, a written
  `.robot` suite (not `.resource`, not `__init__.robot`) is also run through
  `robot --dryrun --output NONE --report NONE --log NONE` from the project
  directory (20 s timeout). `[ ERROR ]` lines and failures such as "No keyword
  with name" are reported as advisory context, capped like the deprecation
  warnings. It is off by default: a dry run imports libraries (import-time side
  effects, seconds for Browser/Selenium), and a keyword the agent writes next
  looks missing until it exists.

Advisory output (deprecations, formatting, dry run) is emitted only when no
exit-2 error diagnostic is written. Robocop is always called with
`--no-cache`, so no `.robocop_cache/` directory is left in your project.

#### Environment variables

| Variable | Values | Effect |
|---|---|---|
| `RF_AGENTSKILLS_DEPRECATION_CHECK` | `warn` (default), `off` | `off` drops all deprecation output. Any other value is treated as `warn`; no value makes a deprecation block (exit 2), and the variable never affects error findings. |
| `RF_AGENTSKILLS_FILE_DRYRUN` | unset (default), `1`/`true`/`yes`/`on` | Enables the per-file dry run above. |
| `RF_AGENTSKILLS_PROJECT_VALIDATION` | unset (default), `1`/`true`/`yes`/`on` | Enables the project-wide Stop tier below. |

#### Opting out per rule

Teams that keep a legacy construct on purpose ignore the rule in their Robocop
config; the hook reads the project's config automatically:

```toml
# pyproject.toml
[tool.robocop.lint]
ignore = ["DEPR08"]
```

**Selecting several rule groups on the command line:** repeat the option —
`robocop check --select "DEPR*" --select "ERR*"`. A comma list
(`--select 'DEPR*,ERR*'`) matches **no** rule in Robocop 8.2 and 9.1: Robocop
prints a warning, reports "No issues found" and exits 0.

This replaced an earlier `robot.api.get_model` check that was effectively a
no-op: `get_model` is a lenient tokenizer that returns "OK" for unterminated
`FOR` loops, undefined keywords, missing imports — even for a file of random
prose. It never raised, so it never caught anything. (It also read the
edited path from a `TOOL_INPUT` env var; the documented contract delivers it
as `tool_input.file_path` on stdin, so the new script reads stdin first and
treats `TOOL_INPUT` only as a legacy fallback.)

### Tier 3 — whole project, end of task, opt-in (`validate_robot_project.mjs`)

Fires from `Stop`, **only when `RF_AGENTSKILLS_PROJECT_VALIDATION` is set**
to a truthy value (`1`/`true`/`yes`/`on`). Runs two cross-file checks that
only make sense once the whole project is on disk:

- `robot --dryrun` over the project — resolves imports and keyword references
  without executing keyword bodies. Catches undefined keywords, argument
  errors, and broken imports. **Note:** dryrun's exit code does *not* reflect
  an import error when the broken import is never used by an executed keyword
  — those surface only as `[ ERROR ]` console lines, so the hook inspects
  both the exit code and the output.
- `robotframework-find-unused keywords` — reports dead (never-called)
  keywords across the project.

It is **off by default** for two reasons: (1) `robot --dryrun` *imports
libraries*, which runs their import-time code (a library import could open a
browser or connect to a database — a real side effect); and (2) both checks
scale with project size. Running them per-save would also false-alarm
constantly — a keyword you just wrote looks "unused" until something calls
it; a call into a not-yet-written resource looks "undefined". Deferring to
`Stop` (end of turn) avoids that. When findings exist the hook exits 2 so the
agent gets one more turn to fix before the turn ends.

### The exit-2 exception

These two validation scripts are the **deliberate exception** to authoring
guideline #2 below ("hook scripts must always exit 0"). The Claude Code
`PostToolUse`/`Stop` contract feeds a hook's stderr back to the agent only on
**exit 2** (exit 1 / other is shown to the user, not the model). Returning a
real error to the model is the entire point of validation — the
edit→validate→feed-back→self-correct loop. So they exit 2 *specifically and
only* on a confirmed Robot Framework error, and exit 0 in every other case
(tool missing, tool timeout or unparsable output, non-Robot file, no
findings, formatting-only difference, deprecation findings of any class).

## How `rf_error_hints.mjs` decides

After every Bash command it scans the output (first 20 000 characters) for Robot Framework error messages. The first time each kind appears in a session, it injects one hint of at most 400 characters, naming the skill to load and the fix:

| Error message | Hint |
|---|---|
| `No keyword with name '…' found` | embedded arguments (`Select team ${city} ${team:\S+}`; text between arguments is literal), rf-language; exact names via rf-libdoc |
| `Multiple keywords with name '…' found` | qualify the call or use `Set Library Search Order` (rf-language) |
| `Invalid argument syntax '…'` | typed arguments `${count: int}` need RF 7.3+ (rf-language) |
| `Resolving variable '…' failed` | scope, import order, `$var` in expressions (rf-language) |
| `Importing library '…' failed` | install into the project environment (rf-setup) |

It never blocks. It always exits 0, and unrelated or malformed input produces no output.

## Python interpreter resolution

`validate_robot.mjs`, `validate_robot_project.mjs`, and
`check_rf_environment.mjs` shell out to Python for the parts that need
Robot Framework tooling (`robocop`, `robot --dryrun`,
`robotframework_find_unused`, `import robot` for the version probe). They
share `scripts/_python_env.mjs`, which takes the first interpreter that can
import the needed tool, in this order:

1. the active virtual environment (`$VIRTUAL_ENV`);
2. the project's `.venv` under the event's `cwd`
   (`.venv/bin/python`, on Windows `.venv\Scripts\python.exe`);
3. the installer-recorded interpreter in `scripts/python_runtime.json`
   (written from `sys.executable`; needed for pipx / uv tool installs);
4. `python3`, then `python` on `PATH`.

The project environment wins so that Robocop sees the project's Robot
Framework version (version-gated rules such as the `VAR` hint follow it). If
the project environment has no Robocop, the search falls through to the
installer's interpreter, whose RF version may differ — a few version-gated
hints can then be off. The hooks never start `uv run` or another package
manager: that can create environments, sync dependencies or reach the network.
If no candidate has the required tool, the hooks exit silently — they're
non-blocking by design.

## Why two of these are conditional

The first version of this plugin used `type: "prompt"` for
`UserPromptSubmit` and `Stop` — Claude Code's way of statically
prepending a system note to the conversation. The text was:

> If this request involves Robot Framework test automation, load the
> relevant skill's SKILL.md before responding...

That seems harmless, but in headless evals against haiku-4-5 it caused
non-RF prompts to no-op: the model read the static injection as a gate
("is this RF?" → "no" → "task done") rather than as guidance. The eval
task `narrow-non-rf-control-01` (a plain JSON-authoring prompt) caught
this regression in CI run `25057802426` — see
`docs/plugin/hooks-fix-proposal.md` for the full diagnosis.

Switching both hooks to `type: "command"` lets a small script inspect
the prompt / session and only inject context when there's a genuine
Robot Framework signal. Non-RF sessions are unaffected.

## How `maybe_inject_rf_context.mjs` decides

- Reads the Claude Code `UserPromptSubmit` event JSON on stdin.
- Extracts `.prompt` (the user's text). If empty / missing, exits 0
  silently.
- Tests the prompt against a case-insensitive regex covering:
  - direct mentions: `robot framework`, `robot-framework`
  - file extensions: `.robot`, `.resource`
  - Robot Framework libraries: `SeleniumLibrary`, `BrowserLibrary`,
    `AppiumLibrary`, `RequestsLibrary`, `RESTinstance`, `PlatynUI`, plus
    space-separated forms (`Browser Library`, etc.)
  - rf-agentskills skill ids: `rf-language`, `rf-python-library`,
    `rf-libdoc`, `rf-results`, `rf-robotcode`, `rf-setup` and the library
    skills `rf-browser`, `rf-selenium`, `rf-appium`, `rf-requests`,
    `rf-restinstance`, `rf-platynui`
  - rf-agentskills subagent ids: `rf-test-architect`, `rf-debug-expert`,
    `rf-keyword-consultant`, `rf-migration-guide`
  - RF section headers pasted into the prompt: `*** Settings ***`,
    `*** Variables ***`, `*** Test Cases ***`, `*** Tasks ***`,
    `*** Keywords ***`, `*** Comments ***`
  - tooling: `libdoc`, `robotidy`, `robocop`, `rfbrowser`, `robotcode`,
    `robot-debug`, `robot.toml`; Python library API terms (`@keyword`,
    `robot.api.deco`, `ROBOT_LIBRARY_*`, "robot listener")
- On match: emits one `{"hookSpecificOutput": {"hookEventName":
  "UserPromptSubmit", "additionalContext": "..."}}` with a routing text of
  at most 450 characters (about 80 tokens): tests, suites, keywords,
  resources and variables → `rf-language`; Python libraries and listeners →
  `rf-python-library`; library usage → the library skill (defaults
  `rf-browser` for web, `rf-requests` for API); installs → `rf-setup`;
  keyword names and arguments → `rf-libdoc` / `robotcode libdoc`, not
  memory; and a closing reminder to write RF 7 syntax (`RETURN`, `VAR`,
  `IF`, `Test Tags`). Skill descriptions and subagents are already listed
  by Claude Code, so the text only says which one to use when.
- On miss: stdout stays empty.

Deliberately **not** matched: bare `RF` (too ambiguous), bare `test`
(too generic), bare `library` / `keyword` / `listener`. The parametrised
cases in `tests/test_hook_scripts.py` lock in the positive trigger list,
the negative miss list, the budget and that every `rf-*` name in the text
is a shipped skill or subagent.

## What `check_rf_environment.mjs` reports

At `SessionStart` it reports the Robot Framework version and interpreter
(same resolution as above, from the event's `cwd`), whether Robocop is
available — without it, syntax and deprecation checks on edit are disabled —
and which library packages are importable. For missing packages it shows
project-environment commands (`uv add …`, `uv add --dev
robotframework-robocop`) and points to the rf-setup skill; it never
recommends `pip install` or `rfbrowser init`. A missing, empty or malformed
event produces no output; it always exits 0.

## How `maybe_remind_robot_tests.mjs` decides

- Reads the Claude Code `Stop` event JSON on stdin.
- Extracts `.transcript_path` (path to the session JSONL). If missing
  or unreadable, exits 0.
- Scans the transcript in 64 KB chunks for `"file_path": "…something.robot"`
  or `"…something.resource"` (with bounded regex — `notes.robotic.md`
  does not count). Streaming chunking keeps memory bounded on
  long sessions.
- On hit: emits `additionalContext` reminding the user to run
  `uv run robot --outputdir results tests/`, inspect with
  `uv run python "<abs path>/skills/rf-results/scripts/rf_results.py"`
  (path computed from the hook's own location), and open `results/report.html`.
- On miss: stdout stays empty.

## Verifying the hooks fire

Two patterns work, depending on what you can inspect:

### Inspect side effects (most reliable)

`stream-json` from `claude -p` includes
`hook_started/progress/response` events for `SessionStart` but **not**
for the other event types. To verify `PostToolUse` /
`UserPromptSubmit` / `Stop` fired, instrument the script itself:

```javascript
// Prepend to any hook script for ad-hoc tracing:
import { appendFileSync } from "node:fs";
appendFileSync(`${process.cwd()}/.hook-trace.log`,
  `[${new Date().toISOString()}] hook fired\n`);
```

Then check `.hook-trace.log` after the session. The `rf-skill-eval`
harness exposes the workspace as `process.cwd()` for the hook
subprocess, so this works under CI as well as in interactive use.

### Run the unit tests

`tests/test_hook_scripts.py` invokes each `.mjs` script via `node` as a
subprocess with synthetic stdin payloads and asserts on the
(stdout, exit-code) pair. No live Claude session needed:

```bash
uv run pytest tests/test_hook_scripts.py -v
```

Parametrised cases covering positive triggers, negative misses,
malformed input, and pathological transcripts.

## Running the eval suite

The `rf-skill-eval` harness includes two paired tasks for the
conditional injection:

- `eval/tasks/narrow/narrow-rf-injection-positive-01.yaml` — RF
  prompt, expects the agent to leverage an rf-agentskills lookup.
- `eval/tasks/narrow/narrow-non-rf-control-01.yaml` — non-RF prompt,
  expects the agent to write a plain JSON file with no rf tooling.

Both should pass green after this hooks fix. Run with:

```bash
uv run rf-skill-eval run \
  --task eval/tasks/narrow/narrow-rf-injection-positive-01.yaml \
  --output eval/runs/local-probe \
  --profile treatment
```

## Authoring guidelines for new hooks in this plugin

1. **Default to conditional injection.** Static `type: "prompt"`
   hooks bias the model on every turn — fine for project-specific
   plugins where the user opted in, lethal for general-purpose
   plugins like this one.
2. **Hook scripts must always exit 0** — *unless* they are intentional
   validation hooks. A stray non-zero exit is interpreted as a hook
   error and surfaced to the user, so wrap risky work in
   `try { … } catch { process.exit(0) }`. The sole deliberate exception
   is the validation tier (`validate_robot.mjs`,
   `validate_robot_project.mjs`), which exits **2** on a confirmed Robot
   Framework error to feed the diagnostic back to the agent — and still
   exits 0 in every non-error path (see "the exit-2 exception" above).
3. **Stop/SubagentStop hooks MUST short-circuit on `stop_hook_active`.**
   Add `if (event?.stop_hook_active) process.exit(0)` immediately after
   parsing the event. Claude Code sets this flag when a Stop fires as a
   continuation of a previous Stop-hook block; without the guard a hook
   that emits any model-facing output re-fires every time and traps the
   session until `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP` (default 9) overrides.
   **Note the trap in guideline #2:** for Stop hooks, *exit 0 is not
   sufficient to be non-blocking* — model-facing output (`additionalContext`
   **or** exit 2) re-invokes the model. `maybe_remind_robot_tests.mjs` once
   looped exactly this way (exit 0 + `additionalContext`, no guard); it now
   short-circuits on `stop_hook_active` and additionally reminds at most once
   per `session_id`.
4. **Stay Node-only when possible.** Shelling out to other runtimes
   (Python, bash) reintroduces the install-time dependency surface
   the Node migration eliminated. If a hook genuinely needs Python
   (Robot Framework parsing), resolve the interpreter with
   `scripts/_python_env.mjs` (project env, then `python_runtime.json`),
   not bare `python` on PATH, and give every spawned process a timeout
   (`spawnOptions(...)`).
5. **Keep the regex tight.** Adding a trigger that looks ergonomic
   ("test", "library") is a fast way to revive the
   `narrow-non-rf-control-01` regression. The unit-test parameter
   list is the canonical specification of what does and doesn't
   trigger; update it deliberately.
