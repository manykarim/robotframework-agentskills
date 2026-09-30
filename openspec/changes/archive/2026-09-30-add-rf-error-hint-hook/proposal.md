## Why

`narrow-language-embedded-01` flips between 1/3 and 3/3 in CI (PR #13). In every failing run the agent wrote `Select team` with `[Arguments]`/`@{args}`, ran `robot`, got `No keyword with name 'Select team Los Angeles Lakers' found. Did you try … enough whitespace`, chased whitespace, and ran out of turns.
- rf-language holds the fix, but Haiku loaded it in only 2 of 6 local runs.
- The description and the UserPromptSubmit routing hook ("Load the matching rf-agentskills skill before writing RF … keywords -> rf-language") were both visible, yet the agent went on without the skill.

The moment the agent reliably reads is the Robot Framework error itself, so that is where the pointer to the right skill belongs.

## What Changes

- **New PostToolUse hook `rf_error_hints.mjs` on `Bash`.** It recognises a small set of Robot Framework error messages in the command output and injects one short, non-blocking hint per error kind per session. Each hint names the skill to load and the concrete fix. The error kinds are:
  - No keyword with name
  - Multiple keywords with name
  - Invalid argument syntax
  - failing variable resolution
  - failed library import
- **rf-language gotchas** now spell out the embedded-argument recipe (`${team:\S+}`), with the warning that the text between arguments is literal, not a regex. They also cover the "No keyword with name … for an `[Arguments]` keyword" case. These were already applied while investigating.

- **Eval task `narrow-language-embedded-01`:** `max_turns` 14 → 25 and `timeout_seconds` 300 → 600, with the stored narrow baseline entry refreshed. Most Haiku runs need 10–15 turns, so the 14-turn limit turned ordinary detours into failures; see design.md "Evidence".

## Capabilities

### New Capabilities
<!-- none -->

### Modified Capabilities
- `rf-session-context-hooks`: ADDED requirement "Robot Framework errors in command output point to the right skill".

## Impact

- **Plugin:**
  - new `plugins/rf-agentskills/scripts/rf_error_hints.mjs`
  - `plugins/rf-agentskills/hooks/hooks.json` (new PostToolUse `Bash` entry)
  - hooks README
- **Tests:** `tests/test_hook_scripts.py`.
- **Installer:** assets rebuilt.
- **CHANGELOG:** entries.
- **Eval:** `narrow-language-embedded-01` re-measured locally (≥ 9 runs) and in CI.
