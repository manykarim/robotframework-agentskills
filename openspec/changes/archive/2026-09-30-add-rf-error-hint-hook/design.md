## Context

See proposal.md.
- The existing hooks already use the patterns this hook reuses:
  - `hookSpecificOutput.additionalContext` for non-blocking context (`maybe_remind_robot_tests.mjs`, `validate_robot.mjs`);
  - a per-session marker file in `os.tmpdir()`, keyed by `session_id`, for "once per session" (`validate_robot.mjs`).
- The Bash PostToolUse payload carries `tool_response.stdout` and `tool_response.stderr`. Older shapes may use a plain string; both are handled.

## Decisions

- **D1. A separate hook, matcher `Bash`.** It is not merged into `validate_robot.mjs`, which validates edited files. It reacts to run output (`robot`, `pabot`, `robotcode robot`, and so on) whatever the command, because the error text is what matters.
- **D2. A fixed signature table.** Each entry has a regex, a kind and a hint template. Hints are at most 400 characters and include the offending name (truncated to 80 characters). Only the first 20000 characters of output are scanned.
- **D3. Once per kind per session.** Marker file: `rf-agentskills-hints-<session>.json`. Without a `session_id`, the hook emits the hint every time.

## Risks / Trade-offs

- The hints add tokens. They are bounded at one per kind per session, and each is at most 400 characters.
- A hint could appear for output from a non-RF tool that contains the same text. That is unlikely, given the RF-specific wording.

## Evidence (2026-09-30, `narrow-language-embedded-01`, local, Haiku 4.5 unless noted)

| Variant | Plugin | max_turns | Result | Notes |
|---|---|---|---|---|
| recipe only | yes | 14 | 5/6 | rf-language loaded in 2/6 |
| recipe + error hook | yes | 14 | 4/9 | hint delivered, often ignored; failures hit the turn limit |
| recipe + error hook | yes | 25 | **9/9** | 10–15 turns typical |
| same, no plugin (baseline) | no | 25 | 5/9 | workarounds or failure; the task still discriminates (+44 pts) |
| Sonnet 5 | yes | 14 | 9/9 | loads rf-language every time |
| Sonnet 5 | no | 14 | 9/9 | Sonnet does not need the skill here, so the task stays on Haiku |

**Conclusion.** The instability came from Haiku's detours meeting the 14-turn limit. The recipe and the error hook did not stabilize the task on their own. Raising `max_turns` to 25 did, and the skill effect remains measurable.

The recipe and the hook are kept as product improvements, because they are correct, cheap and bounded. Their isolated effect on pass rates is not established; measuring it would need a separate ablation.
