#!/usr/bin/env bash
# maybe_remind_robot_tests.sh - Conditional Stop hook.
#
# Reads the Claude Code Stop event JSON on stdin, inspects the
# session transcript for any tool result that wrote a .robot or
# .resource file, and only emits an additionalContext reminder
# ("run robot, inspect report.html") when at least one such file
# was touched. Sessions that produced only non-RF artifacts get
# no injection.
#
# Why this exists: the previous version of this hook used type:
# "prompt" and unconditionally injected the reminder into every
# session-end. For non-RF sessions this added noise that biased
# the agent's final response. Companion to
# maybe_inject_rf_context.sh; same conversion pattern.
#
# Schema:
#   stdin  - Claude Code Stop event JSON. Includes transcript_path.
#   stdout - Either empty (no reminder) or a single JSON object with
#            hookSpecificOutput.additionalContext.
#   exit   - Always 0.
#
# Tested against Claude Code 2.1.121.

set -uo pipefail

INPUT="$(cat)"
[ -z "$INPUT" ] && exit 0

# Locate the transcript JSONL. Required: cannot scan tool results
# without it.
TRANSCRIPT=""
if command -v jq >/dev/null 2>&1; then
    TRANSCRIPT="$(jq -r '.transcript_path // ""' <<<"$INPUT" 2>/dev/null || true)"
elif command -v python3 >/dev/null 2>&1; then
    TRANSCRIPT="$(python3 -c "import json,sys
try:
    d = json.loads(sys.stdin.read())
    print(d.get('transcript_path',''))
except Exception:
    pass" <<<"$INPUT" 2>/dev/null || true)"
fi

[ -z "$TRANSCRIPT" ] && exit 0
[ -f "$TRANSCRIPT" ] || exit 0

# Look for any tool-call or tool-result whose file_path ends in .robot
# or .resource. We match on the JSON literal "file_path":"...whatever..."
# without trying to parse the whole transcript — a single grep keeps
# this fast on long sessions.
if ! grep -qE '"file_path"[[:space:]]*:[[:space:]]*"[^"]*\.(robot|resource)"' "$TRANSCRIPT"; then
    exit 0
fi

# At least one .robot/.resource file was touched → emit reminder.
# Note: ${CLAUDE_PLUGIN_ROOT} is substituted by the plugin loader (or
# by the rf-skill-eval harness during staging) into an absolute path.
cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "Stop",
    "additionalContext": "Robot Framework artifacts detected this session. Recommended next steps:\n  1. Run the suite: robot --outputdir results tests/\n  2. Programmatic inspection: python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/rf_results.py\" --output results/output.xml --sections summary,errors --pretty\n  3. Open results/report.html for the rendered report."
  }
}
JSON
exit 0
