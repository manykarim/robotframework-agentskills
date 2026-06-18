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

| Event | Script | Always fires? | Cost when no-op |
|---|---|---|---|
| `SessionStart` | `scripts/check_rf_environment.mjs` | yes | ~150ms (informational) |
| `PostToolUse` (matcher: `Write\|Edit`) | `scripts/validate_robot.mjs` | only on Write/Edit | ~30ms (file extension check) |
| `UserPromptSubmit` | `scripts/maybe_inject_rf_context.mjs` | always invoked, conditional injection | ~30ms (regex over prompt) |
| `Stop` | `scripts/maybe_remind_robot_tests.mjs` | always invoked, conditional reminder | ~30ms (chunked grep over transcript) |
| `Stop` | `scripts/validate_robot_project.mjs` | only when `RF_AGENTSKILLS_PROJECT_VALIDATION` is set | ~0ms (env-flag check) |

## Validation hooks (what catches broken Robot Framework code)

Two scripts validate the Robot Framework files the agent writes, at two
different points in the lifecycle. Both are **optional** — they degrade
to a silent no-op when their underlying tools aren't installed. Install
the tooling with the `validation` extra:

```bash
pip install "rf-agentskills[validation]"   # robotframework-robocop + robotframework-find-unused
```

### Tier 1 + 2 — per file, on every write (`validate_robot.mjs`)

Fires from `PostToolUse` after a Write/Edit of a `.robot`/`.resource` file.

- **Tier 1 — structural errors:** runs `robocop check --threshold E`. The
  `--threshold E` is deliberate: Robocop has 167 rules and the default set
  flags style nits (e.g. `DOC03 Missing documentation`) on *every* file,
  including perfectly valid ones — that noise would bury real problems and
  get the hook disabled. Error severity scopes to genuine problems:
  invalid `FOR`/`IF`/`TRY` syntax, argument errors, duplicate definitions,
  and imports Robocop can statically see are broken. On a finding the hook
  writes the diagnostic to **stderr and exits 2**, which feeds it back to
  the agent so it can self-correct (see "the exit-2 exception" below).
- **Tier 2 — formatting drift:** runs `robocop format --check --diff`. Purely
  informational — surfaces the proposed reformat as `additionalContext`
  (exit 0). Formatting differences **never** cause exit 2.

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
(tool missing, non-Robot file, no findings, formatting-only difference).

## Python interpreter resolution

`validate_robot.mjs`, `validate_robot_project.mjs`, and
`check_rf_environment.mjs` shell out to Python for the parts that need
Robot Framework tooling (`robocop` / `robot --dryrun` /
`robotframework_find_unused` for validation, `import robot` for the
version probe). They read `scripts/python_runtime.json` — written by the
installer from `sys.executable` — to find the interpreter that has
`robotframework` installed. This is necessary for pipx, uv tool install,
and venv installs where `python` on PATH is NOT the same Python
rf-agentskills was installed into.

If the recorded interpreter is unreachable (user moved their venv),
the hooks fall back to `python3` → `python` on PATH. If no candidate
interpreter has the required tool (`robotframework`, `robocop`,
`robotframework_find_unused`), the hooks exit silently — they're
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
    `AppiumLibrary`, `RequestsLibrary`, `RESTinstance`, plus
    space-separated forms (`Browser Library`, etc.)
  - rf-agentskills skill ids: `libdoc-search`, `libdoc-explain`,
    `keyword-builder`, `testcase-builder`, `resource-architect`,
    `rf-results`
  - rf-agentskills subagent ids: `rf-test-architect`, `rf-debug-expert`,
    `rf-keyword-consultant`, `rf-migration-guide`
  - tooling: `libdoc`, `robotidy`, `robocop`, `rfbrowser`
- On match: emits `{"hookSpecificOutput": {"hookEventName":
  "UserPromptSubmit", "additionalContext": "..."}}` summarising the
  available rf-agentskills and pointing the agent at libdoc-search /
  libdoc-explain for keyword lookups.
- On miss: stdout stays empty.

Deliberately **not** matched: bare `RF` (too ambiguous), bare `test`
(too generic), bare `library` / `keyword`. The parametrised cases in
`tests/test_hook_scripts.py` lock in both the positive trigger list
and the negative miss list.

## How `maybe_remind_robot_tests.mjs` decides

- Reads the Claude Code `Stop` event JSON on stdin.
- Extracts `.transcript_path` (path to the session JSONL). If missing
  or unreadable, exits 0.
- Scans the transcript in 64 KB chunks for `"file_path": "…something.robot"`
  or `"…something.resource"` (with bounded regex — `notes.robotic.md`
  does not count). Streaming chunking keeps memory bounded on
  long sessions.
- On hit: emits `additionalContext` reminding the user to run
  `robot --outputdir results tests/`, inspect with
  `scripts/rf_results.py`, and open `results/report.html`.
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
   (Robot Framework parsing), use `scripts/python_runtime.json` to
   target the install-time interpreter, not bare `python` on PATH.
5. **Keep the regex tight.** Adding a trigger that looks ergonomic
   ("test", "library") is a fast way to revive the
   `narrow-non-rf-control-01` regression. The unit-test parameter
   list is the canonical specification of what does and doesn't
   trigger; update it deliberately.
