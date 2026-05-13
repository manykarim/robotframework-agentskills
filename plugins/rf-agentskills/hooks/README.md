# rf-agentskills hooks

This plugin defines four Claude Code lifecycle hooks. Two of them
(`SessionStart`, `PostToolUse`) run unconditionally; two of them
(`UserPromptSubmit`, `Stop`) consult the session before deciding to
do anything.

All four are **cross-platform Node.js** scripts (`.mjs`). They run
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

## Python interpreter resolution

`validate_robot.mjs` and `check_rf_environment.mjs` shell out to Python
for the parts that need Robot Framework (`from robot.api import
get_model` for parsing, `import robot` for the version probe). They
read `scripts/python_runtime.json` — written by the installer from
`sys.executable` — to find the interpreter that has `robotframework`
installed. This is necessary for pipx, uv tool install, and venv
installs where `python` on PATH is NOT the same Python rf-agentskills
was installed into.

If the recorded interpreter is unreachable (user moved their venv),
the hooks fall back to `python3` → `python` on PATH. If neither has
`robotframework`, the hooks exit silently — they're non-blocking by
design.

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
2. **Hook scripts must always exit 0.** A non-zero exit is
   interpreted as a hook error and surfaced to the user. Wrap risky
   work in `try { … } catch { process.exit(0) }`.
3. **Stay Node-only when possible.** Shelling out to other runtimes
   (Python, bash) reintroduces the install-time dependency surface
   the Node migration eliminated. If a hook genuinely needs Python
   (Robot Framework parsing), use `scripts/python_runtime.json` to
   target the install-time interpreter, not bare `python` on PATH.
4. **Keep the regex tight.** Adding a trigger that looks ergonomic
   ("test", "library") is a fast way to revive the
   `narrow-non-rf-control-01` regression. The unit-test parameter
   list is the canonical specification of what does and doesn't
   trigger; update it deliberately.
