# rf-agentskills hooks

This plugin defines four Claude Code lifecycle hooks. Two of them
(`SessionStart`, `PostToolUse`) run unconditionally; two of them
(`UserPromptSubmit`, `Stop`) consult the session before deciding to
do anything.

| Event | Script | Always fires? | Cost when no-op |
|---|---|---|---|
| `SessionStart` | `scripts/check_rf_environment.sh` | yes | ~150ms (informational) |
| `PostToolUse` (matcher: `Write\|Edit`) | `scripts/validate_robot.sh` | only on Write/Edit | ~5ms (file extension check) |
| `UserPromptSubmit` | `scripts/maybe_inject_rf_context.sh` | always invoked, conditional injection | ~5ms (regex over prompt) |
| `Stop` | `scripts/maybe_remind_robot_tests.sh` | always invoked, conditional reminder | ~5ms (grep over transcript) |

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

Switching both hooks to `type: "command"` lets a small bash script
inspect the prompt / session and only inject context when there's a
genuine Robot Framework signal. Non-RF sessions are unaffected.

## How `maybe_inject_rf_context.sh` decides

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
(too generic), bare `library` / `keyword`. The 41 parametrised cases
in `tests/test_hook_scripts.py` lock in both the positive trigger list
and the negative miss list.

## How `maybe_remind_robot_tests.sh` decides

- Reads the Claude Code `Stop` event JSON on stdin.
- Extracts `.transcript_path` (path to the session JSONL). If missing
  or unreadable, exits 0.
- Greps the transcript for `"file_path": "...something.robot"` or
  `"...something.resource"` (with bounded regex — `notes.robotic.md`
  does not count).
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

```bash
# Prepend to any hook script for ad-hoc tracing:
echo "[$(date -Iseconds)] $(basename "$0") fired" >> "$PWD/.hook-trace.log"
```

Then check `.hook-trace.log` after the session. The `rf-skill-eval`
harness exposes the workspace as `$PWD` for the hook subprocess, so
this works under CI as well as in interactive use.

### Run the unit tests

`tests/test_hook_scripts.py` invokes both conditional scripts as
subprocesses with synthetic stdin payloads and asserts on the
(stdout, exit-code) pair. No live Claude session needed:

```bash
uv run pytest tests/test_hook_scripts.py -v
```

41 cases covering positive triggers, negative misses, malformed input,
and pathological transcripts.

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
   interpreted as a hook error and surfaced to the user. Use
   `set -uo pipefail` (note: not `-e` — let individual commands fail
   silently when their output isn't critical).
3. **Side-step jq dependency.** Both conditional scripts try `jq`
   first and fall back to `python3` so the plugin works on minimal
   images that ship one but not the other.
4. **Keep the regex tight.** Adding a trigger that looks ergonomic
   ("test", "library") is a fast way to revive the
   `narrow-non-rf-control-01` regression. The unit-test parameter
   list is the canonical specification of what does and doesn't
   trigger; update it deliberately.
