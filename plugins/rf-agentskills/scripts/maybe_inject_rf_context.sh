#!/usr/bin/env bash
# maybe_inject_rf_context.sh - Conditional UserPromptSubmit hook.
#
# Reads the Claude Code UserPromptSubmit event JSON on stdin, inspects
# the user's prompt for Robot Framework signals, and only emits an
# additionalContext injection when at least one signal is present. On
# non-RF prompts it exits cleanly with no output so Claude Code does
# not prepend any system context to the conversation.
#
# Why this exists:
#   The previous incarnation of this hook used type: "prompt" and
#   injected rf-agentskills guidance into every prompt. Haiku read the
#   "If this is RF, load a SKILL.md..." text as a permission gate and
#   no-op'd on plain non-RF prompts (e.g. "write data/colors.json").
#   Eval task narrow-non-rf-control-01 caught this regression. See
#   docs/plugin/hooks-fix-proposal.md for the full diagnosis.
#
# Schema:
#   stdin  - Claude Code UserPromptSubmit event JSON.
#   stdout - Either empty (no injection) or a single JSON object of the
#            form {"hookSpecificOutput": {"hookEventName":
#            "UserPromptSubmit", "additionalContext": "..."}}.
#   exit   - Always 0. The hook is non-blocking by design.
#
# Tested against Claude Code 2.1.121.

set -uo pipefail

# Read the event JSON from stdin. Drop empty/missing input on the floor.
INPUT="$(cat)"
[ -z "$INPUT" ] && exit 0

# Extract just the user's prompt. jq is preferred (we use it elsewhere
# in the plugin); fall back to a python3 one-liner if jq is unavailable
# so the hook still works on minimal images.
PROMPT=""
if command -v jq >/dev/null 2>&1; then
    PROMPT="$(jq -r '.prompt // ""' <<<"$INPUT" 2>/dev/null || true)"
elif command -v python3 >/dev/null 2>&1; then
    PROMPT="$(python3 -c "import json,sys
try:
    d = json.loads(sys.stdin.read())
    print(d.get('prompt',''))
except Exception:
    pass" <<<"$INPUT" 2>/dev/null || true)"
fi

# No prompt → nothing to inspect → no injection.
[ -z "$PROMPT" ] && exit 0

# Robot Framework signal regex (case-insensitive). Conservative on
# purpose — better to under-inject than over-inject. The user can
# always invoke a skill explicitly to recover.
#
# Categories covered:
#   - Direct RF mentions: "robot framework", "robot-framework"
#   - File extensions: .robot, .resource
#   - Library names (with or without space): SeleniumLibrary, Browser
#     Library, AppiumLibrary, RequestsLibrary, RESTinstance, etc.
#   - rf-agentskills skill ids: libdoc-search, libdoc-explain,
#     keyword-builder, testcase-builder, resource-architect
#   - rf-agentskills subagent ids: rf-test-architect, rf-debug-expert,
#     rf-keyword-consultant, rf-migration-guide
#   - Tooling: libdoc, robotidy, robocop, rfbrowser
#
# Things deliberately NOT matched: the bare word "test" (too noisy),
# bare "RF" (ambiguous - could mean radio frequency).
RF_REGEX='robot[ -]?framework|\.robot\b|\.resource\b|\b(selenium|browser|appium|requests)library\b|\brestinstance\b|\b(selenium|browser|appium|requests) library\b|\blibdoc\b|\b(robotidy|robocop|rfbrowser)\b|\b(keyword|testcase|resource)[ -]builder\b|\b(libdoc-search|libdoc-explain|keyword-builder|testcase-builder|resource-architect|rf-results)\b|\brf-(test-architect|debug-expert|keyword-consultant|migration-guide)\b'

if ! grep -qiE "$RF_REGEX" <<<"$PROMPT"; then
    # Non-RF prompt → no injection. The agent sees the user prompt
    # untouched and acts on it.
    exit 0
fi

# RF signal present → emit additionalContext so the agent knows about
# the rf-agentskills it can reach for.
cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Robot Framework context detected. Available rf-agentskills (load the relevant SKILL.md when needed):\n  - Library references: browser, selenium, appium, requests, restinstance\n  - Script-based tools: keyword-builder, testcase-builder, resource-architect, libdoc-search, libdoc-explain, results\n  - Subagents: rf-test-architect, rf-debug-expert, rf-keyword-consultant, rf-migration-guide\nPrefer libdoc-search / libdoc-explain over guessing keyword signatures from memory."
  }
}
JSON
exit 0
