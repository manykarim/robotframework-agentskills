# rf-agentskills hooks: investigation and fix proposal

**Status:** Proposal — no code changes yet. Reviewing for direction before implementation.

**Branch:** `fix/plugin-hooks` (off `main` at PR #2 merge).

**Author:** drafted from CI run `25057802426` (PR #2) plus follow-up local experiments and ecosystem research.

## TL;DR

1. The CI artifact scan that suggested **`PostToolUse` with `matcher: "Write|Edit"` doesn't fire was wrong**. Local experiments against Claude Code 2.1.121 (same version as CI) confirm the matcher works; it just doesn't emit `hook_started/progress/response` events to `stream-json` the way `SessionStart` does. The hook IS running — its side effects (`stderr`, log writes) are simply not surfaced in the stream we were inspecting.

2. **The real regression** is `UserPromptSubmit` of `type: "prompt"` injecting *"If this involves Robot Framework, load a SKILL.md..."* on **every** prompt. Haiku reads the injection as an evaluation gate ("is this RF? → no → done") and no-ops on plain non-RF prompts. This is what `narrow-non-rf-control-01` caught.

3. **Recommended fix scope**: convert `UserPromptSubmit` from a static prompt injection into a conditional command hook that reads the user prompt on stdin and only injects RF guidance when the prompt contains RF-related signals. Leave `PostToolUse` matcher alone (or expand it slightly for clarity). Document the verification pattern so future debugging doesn't chase the same false trail.

## What the experiment proved

A 9-variant probe was run locally against `claude 2.1.121` (the same CI version) using `--permission-mode bypassPermissions`. Each variant ran `claude -p "Write a small file..."` against an isolated workspace whose `.claude/settings.json` registered:
- A `SessionStart` hook (`matcher: ""`) — to confirm hook-event visibility in the stream
- A `PostToolUse` hook with the matcher under test

Both hooks invoked the same Bash script which read the event JSON from stdin (per Claude Code spec), extracted `tool_name`, and appended to a log file.

| Matcher | PostToolUse fired (log) | Tool seen | SessionStart fired | Stream `hook_*` events |
|---|---|---|---|---|
| `Write\|Edit` | yes | `Write` | yes | 1 (SessionStart only) |
| `(Write\|Edit)` | yes | `Write` | yes | 1 |
| `Write` | yes | `Write` | yes | 1 |
| `.*` | yes | `Write` | yes | 1 |
| `*` | yes | `Write` | yes | 1 |
| `""` (empty) | yes | `Write` | yes | 1 |
| `^Write$` | yes | `Write` | yes | 1 |
| `NotARealTool` | **no** | — | yes | 1 |
| `mcp__rf-mcp__.*` | **no** | — | yes | 1 |

Conclusions:
- **`Write|Edit` matches `Write` correctly.** The current plugin syntax is fine.
- **PostToolUse fires silently in `stream-json`.** Only `SessionStart` (and similar event-loop hooks) emit `hook_started/progress/response` envelopes. PostToolUse runs the script and discards its output unless we deliberately capture it.
- **All five "regex / alternation / glob / empty" forms behave equivalently** for the Write tool. This contradicts one claim from the documentation that matchers are restricted to `[A-Za-z0-9_|]` — in practice, Claude Code 2.1.121 falls through to standard regex for any value, and `""` / `*` / `.*` are all catch-alls.
- **Specific patterns correctly miss.** `NotARealTool` and `mcp__rf-mcp__.*` (no rf-mcp tool used in the run) registered zero PostToolUse fires, confirming the matcher is consulted, not just ignored.

The probe scaffold lives at `/tmp/hook-probe-v2/` (transient — see "Reproduce locally" below for the script).

## Why CI looked broken

The post-mortem on run `25057802426` checked two things and concluded "PostToolUse doesn't fire":

1. `stderr.log` was 0 bytes → assumed `validate_robot.sh` never ran.
2. `grep "hook_" stream.jsonl` only found `SessionStart` events → assumed PostToolUse silently failed.

Both signals were consistent with "didn't fire" but neither actually proves it. The truth:

- `validate_robot.sh` *did* run after every Write/Edit — but it short-circuits to `exit 0` for non-`.robot`/`.resource` files (the vast majority of writes in the eval) and writes nothing to stderr in that path. The one task that wrote `.resource` files (`narrow-keyword-builder-01`) probably also fired the hook, but its stderr was either lost in pipe handling or only emitted on failure.
- Claude Code does not emit `hook_*` stream events for `PostToolUse` the way it does for `SessionStart`. Lack of stream events ≠ hook didn't fire.

**Verification recipe that actually works** (use this in future eval runs):

```bash
# In a copy of the plugin's hook script, prepend:
echo "[$(date -Iseconds)] event=$0 tool=$(echo "$STDIN_JSON" | jq -r '.tool_name')" \
    >> "$WORKSPACE/.hook-trace.log"
```

Then check `<workspace>/.hook-trace.log` after the run — every PostToolUse invocation leaves a row. This is more reliable than scanning `stream-json` for `hook_*` events.

## Cross-agent context (informs the fix design)

Claude Code's hook system is the most expressive among comparable agents and is becoming the de facto standard:

| Agent | Hook system | Tool matcher | Conditional prompt injection |
|---|---|---|---|
| Claude Code 2.1 | yes — `hooks.json` schema | regex on tool name | only via `type: "command"` (read stdin, conditional stdout) |
| Cursor 1.7+ | yes — `.cursor/hooks.json` | regex; namespaced (`Shell`, `MCP:<name>`) | `beforeSubmitPrompt` with structured JSON response |
| GitHub Copilot (VS Code 2026.1) | yes — adopted Claude's `hooks.json` schema | parsed but ignored; filter inside script | `UserPromptSubmit` exists |
| Cline | yes | none — filter on `toolName` in script | yes |
| Roo Code / Continue.dev / Aider | partial / none | n/a | n/a |

Implication for rf-agentskills: **don't invent a new schema or matcher syntax**. Claude Code's matcher (regex on tool name) is the cross-agent standard; Cursor and Copilot already accept it. Spend the effort making the existing schema work well rather than diverging.

## Proposed fix

Two changes to `plugins/rf-agentskills/hooks/hooks.json`, one optional script tweak, and one doc update.

### 1. Convert `UserPromptSubmit` to a conditional command hook (mandatory)

**Current:**
```json
"UserPromptSubmit": [
  {
    "matcher": "",
    "hooks": [
      {
        "type": "prompt",
        "prompt": "If this request involves Robot Framework test automation, load the relevant skill's SKILL.md before responding. Available skills: ..."
      }
    ]
  }
]
```

This is unconditional — Haiku sees it on every prompt and treats it as a gate.

**Proposed:**
```json
"UserPromptSubmit": [
  {
    "matcher": "",
    "hooks": [
      {
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/scripts/maybe_inject_rf_context.sh"
      }
    ]
  }
]
```

The new script reads the event JSON on stdin, inspects `.prompt`, and only emits an `additionalContext` injection when the prompt contains an RF signal. Sketch (not implemented yet):

```bash
#!/usr/bin/env bash
set -euo pipefail
INPUT=$(cat)
PROMPT=$(jq -r '.prompt // ""' <<<"$INPUT")

# RF-related signals (case-insensitive). Conservative set — better to
# under-inject than over-inject; the user can always say "use the rf
# skills" and trigger discovery the normal way.
if printf '%s' "$PROMPT" | grep -iqE \
   '(robot[ -]?framework|\.robot|\.resource|libdoc|browser library|seleniumlibrary|appiumlibrary|\brequestslibrary|restinstance|\bRF[ -]?test|keyword[- ]driven)'; then
    cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Robot Framework context detected. Available rf-agentskills: browser, selenium, appium, requests, restinstance (library refs); keyword-builder, testcase-builder, resource-architect, libdoc-search, libdoc-explain, results (script tools). Available subagents: rf-test-architect, rf-debug-expert, rf-keyword-consultant, rf-migration-guide. Load the relevant SKILL.md when needed."
  }
}
JSON
fi
exit 0
```

Why this works:
- **Conservative regex** — matches only on RF-specific signals. A request like "write a JSON file with these colors" gets nothing injected.
- **Per Claude Code docs**, command hooks under `UserPromptSubmit` can return `hookSpecificOutput.additionalContext` to inject system context. Empty stdout = no injection. Exit 0 in both cases.
- **No model-side gate** — when no injection happens, Haiku just sees the user's prompt and acts on it. The `narrow-non-rf-control-01` failure mode goes away.
- **Backward compatible** — when the prompt does mention RF, the injected context is the same advice the old prompt-hook gave.

Verification: `narrow-non-rf-control-01` should pass at 100% after this change; the seven RF-themed tasks should still pass; a new task could explicitly assert that `additionalContext` was injected for an RF prompt by reading stream events for `hookSpecificOutput`.

### 2. Make `Stop` hook conditional too (mandatory, same reason)

The `Stop` hook currently injects a "remind the user to run robot tests" prompt unconditionally on every session end:

```json
"Stop": [
  {
    "matcher": "",
    "hooks": [
      {
        "type": "prompt",
        "prompt": "If you generated or modified any .robot or .resource files during this session, remind the user to: ..."
      }
    ]
  }
]
```

For non-RF sessions this injection is noise that may also bias Haiku's final response. Same conversion: replace with a `type: "command"` hook that scans the session's tool_use_results for `.robot`/`.resource` writes and only emits the reminder when at least one is found. Sketch:

```bash
#!/usr/bin/env bash
INPUT=$(cat)
# Stop-event input contains stop_hook_active, transcript_path, etc.
TRANSCRIPT=$(jq -r '.transcript_path // ""' <<<"$INPUT")
[ -f "$TRANSCRIPT" ] || exit 0
if grep -qE '"file_path":[^,]*\.(robot|resource)' "$TRANSCRIPT"; then
    cat <<'JSON'
{ "hookSpecificOutput": { "hookEventName": "Stop", "additionalContext": "Reminder: run `robot --outputdir results tests/` and inspect `results/report.html`." } }
JSON
fi
exit 0
```

### 3. Keep `PostToolUse` matcher as-is (no change)

The probe confirms `Write|Edit` matches both `Write` and `Edit`. Don't touch this. Optional cosmetic improvement: split into two entries for readability, both pointing at the same script — cleaner diff against the docs but functionally identical.

### 4. Optional: make `validate_robot.sh` quieter on success

Current behavior: prints `Robot Framework syntax OK: <path>` to stderr after every successful validation. In a multi-write session this noisily clutters hook output. Switch to: silent on success, only print on validation failure. One-liner change in the script.

### 5. Documentation

Add a short section to `plugins/rf-agentskills/hooks/README.md` (currently does not exist) covering:
- Hook event flow with this plugin
- How to verify each hook fires (the `.hook-trace.log` recipe above)
- Why `UserPromptSubmit` is conditional and what regex triggers injection — so future contributors don't re-introduce unconditional injection

## Reproduce locally

The probe script lives in this proposal — not committed because it's transient. Save the contents below as `/tmp/run-probe.sh`, `chmod +x`, and run. Requires `claude` 2.1+ on PATH and `jq`.

```bash
# /tmp/run-probe.sh — see the artifact in /tmp/hook-probe-v2/results.tsv after running.
# (full script body redacted from the proposal — see scratch file or rerun with the
# inline shell heredoc from the original investigation)
```

> If you want this committed as a real test, it can become an `eval/tasks/diagnostic/`-tier task (a tier we don't currently have but could add for "sanity probes that don't gate ship").

## Risks and open questions

- **Conditional `UserPromptSubmit` may under-trigger** if the user describes an RF task without using any of the matched keywords (e.g. "I have a test that's flaky"). Mitigation: the existing skills are still discoverable through the normal Claude Code skill-search mechanism — the hook injection is an *accelerator*, not a gate. Worst case: agent doesn't immediately know about the skills, asks a clarifying question, finds them.
- **JSON output schema for `additionalContext`** — the `hookSpecificOutput.additionalContext` field is documented but I haven't experimentally confirmed it's honoured by Claude Code 2.1 *for `UserPromptSubmit`* (only for `PreToolUse`). Worth a quick probe before implementing — falls back to `printf '%s' "$context"` on stdout if not, which is a documented alternative.
- **Plugin-side `.mcp.json`** for the rf-tools MCP server is currently untracked in git. Not addressed by this fix; flagging as a related item that should be committed separately so CI can exercise the rf-tools server too.

## What this is NOT proposing

- No matcher syntax change for `PostToolUse` (the existing one works).
- No change to `SessionStart` hook (works correctly — emits visible events and runs the env-check script).
- No change to skills, agents, scripts, or settings.json shape.
- No change to the eval harness side. The harness already provisions hooks correctly; the issue is purely in the plugin's hook definitions.

## Decision points for the reviewer

Before implementing:

1. **Do you agree the real bug is `UserPromptSubmit` (not the matcher)?** If yes, proceed to design.
2. **Conditional injection regex** — is the proposed RF-signal list (`robot framework`, `.robot`, `.resource`, library names...) the right scope, or should it be tighter/looser?
3. **Should `Stop` hook conversion ship together** with `UserPromptSubmit`, or land separately?
4. **Does `narrow-non-rf-control-01` need to be the verification?** It's the canary that caught this; passing it should be the merge gate. Consider also adding a positive task that explicitly asserts the `additionalContext` injection fired for an RF prompt.
