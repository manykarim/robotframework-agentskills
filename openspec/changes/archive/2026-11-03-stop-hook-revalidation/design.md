## Context

See proposal.md (Why). Evidence comes from the `marketplace-distribution` re-check: the OTel spans `execute_tool create_file` → `execute_hook PostToolUse` (exit 2, 0.73 s), with the next `chat` span starting 41 ms after the hook. In Copilot Chat 0.70.0, `executeStopHook` awaits the Stop hooks and collects both `hookSpecificOutput.decision: "block"` reasons and exit-2 stderr (`onError`) as reasons to continue. The prototype run confirmed it: Stop exit 2 → a new model turn → `apply_patch` adding `END` → silent Stop.

## Goals / Non-Goals

**Goals:**
- An error the agent left unfixed reaches the model before the turn ends, in every agent that runs Claude-format Stop hooks.
- No change in agents whose PostToolUse feedback already works, beyond one cheap no-op process at Stop.

**Non-Goals:**
- Fixing the VS Code race itself (an upstream issue).
- Re-checking files the agent never edited, or running project-wide checks (`validate_robot_project.mjs` stays opt-in).
- OpenCode: its plugin appends findings to the tool output synchronously.

## Decisions

### D1. Record failures at PostToolUse, re-validate at Stop
`validate_robot.mjs` writes a per-session JSON map `{path: {reported: sha1|null}}` to the OS temp dir (`rf-agentskills-pending-<session_id>.json`), using the same pattern as the deprecation dedupe marker. A file is added on real errors and removed on a passing run.
- **Alternative rejected:** scan the transcript for edited files at Stop. Transcript formats differ per agent (VS Code's doesn't record tool results), and every edited file would be re-validated even when nothing failed.
- **Alternative rejected:** report the recorded diagnostics without re-validating. A file fixed by a non-hook path (a terminal command, a user edit) would be reported stale.

### D2. Re-validate by running `validate_robot.mjs` as a child
The Stop hook runs the validator with a synthetic `Write` event per file, as `validateEach` already does for multi-file patches. One code path decides what counts as an error, and the child run updates the record itself.

### D3. Output contract = `validate_robot.mjs`'s
stderr + exit 2 for Claude Code, Codex and VS Code Local (whose `onError` collects stderr as a Stop reason), plus top-level `{"decision":"block","reason"}` on stdout for Copilot (`agentStop` block).
- **Alternative rejected:** `hookSpecificOutput.decision`. It's VS Code only, and Claude Code doesn't define it for Stop.

### D4. Loop safety
No-op on `stop_hook_active`, as `stop-hook-safety` requires. In addition, the content sha1 is stored as `reported`, and a file whose content hasn't changed since it was reported is skipped. Without that, a file the agent can't fix would block the stop of every later turn.

## Risks / Trade-offs

- [Feedback is late in VS Code Local: it arrives at the end of the turn, not right after the edit] → Still within the same request; documented in the README.
- [Stale temp files per session] → Tiny JSON files in the temp dir, like the existing markers. The OS cleans them up.
- [Session id missing in some agent's Stop or PostToolUse input] → Without a session id nothing is recorded and the hook is a no-op, the current behaviour.
- [Re-validation cost at Stop] → Only for files left failing; bounded by the validator's own timeouts and a 60 s hook timeout.
