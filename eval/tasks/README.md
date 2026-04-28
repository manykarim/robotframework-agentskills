# Task Bank

Task definitions for the `robotframework-agentskills` evaluation harness.

Each task YAML is an input to the runner, which hands `prompt` to Claude Code
headlessly (`claude -p`) inside a fresh copy of the task's `fixture`. The
`grader_checks` are then applied to the fixture's end-state to decide whether
the run succeeded.

## Directory layout

```
eval/tasks/
  narrow/        # Single-skill, deterministic, <=5 min wall time
  realistic/     # Multi-step, multi-file, <=15 min wall time
  adversarial/   # Tempts known failure modes (reported only, not gating)
  README.md      # This file
```

## YAML schema

| Field | Required | Type | Description |
|---|---|---|---|
| `id` | yes | string | Unique task id. Convention: `<tier>-<skill>-<nn>`. |
| `skill` | yes | string | Matches a skill's `name:` in `skills/*/SKILL.md` (e.g. `rf-keyword-builder`). |
| `tier` | yes | enum | `narrow` \| `realistic` \| `adversarial`. |
| `description` | yes | string | Human-readable summary of the task. |
| `prompt` | yes | string | Exact text fed to `claude -p` on stdin. Should be ecologically realistic. |
| `model` | yes | enum | `claude-haiku-4-5` or `claude-sonnet-4-6`. Opus is **not** permitted. |
| `max_turns` | yes | int | Upper bound on agent turns. |
| `timeout_seconds` | yes | int | Wall-clock budget for the session. |
| `allowed_tools` | yes | list[string] | Claude Code tool allowlist (passed via `--allowedTools`). |
| `expected_files` | no | list[object] | Files the agent is expected to produce. Each has `path` and optional `must_contain` (list of substrings). Informational; does not gate. |
| `grader_checks` | yes | list[object] | Applied in order to the fixture end-state. See below. |
| `fixture` | yes | string | Fixture directory name under `eval/fixtures/`. |
| `primary_metric` | yes | string | Single grader-check `type` used for SHIP/ITERATE/HOLD gating (per ADR-004). |

## Grader check types

| Type | Fields | Semantics |
|---|---|---|
| `file_exists` | `path` | Path must exist inside the fixture. |
| `file_contains` | `path`, `regex` | File must contain at least one match for the regex. |
| `robot_pass` | `target` | `robot <target>` exits 0 in the fixture dir. Timeout 120s. |
| `no_deprecated_keywords` | `target` | Grader lint rejects known-deprecated SeleniumLibrary / BuiltIn keywords. |
| `lint_clean` | `tool`, `target` | `tool` (e.g. `robotidy`, `robocop`) reports no violations. |
| `import_resolves` | `path` | All `Library` / `Resource` imports in `path` resolve on dry-run. |

Checks are AND-composed. A task's `primary_metric` references the **type** of
the externally-grounded check that gates shipping (per ADR-004: must be
externally grounded, not self-reported).

## Tier definitions

- **narrow** — Exercise a single skill. Deterministic graders. Haiku is the
  default model; these are the cheap, high-volume tasks.
- **realistic** — Multi-step work that approximates a real user session.
  Multiple files, sometimes real execution (Browser library, API client).
  Sonnet is the default.
- **adversarial** — Deliberately tempts failure modes skills are meant to
  prevent (convention violations, deprecated keyword preference, "just make
  it pass" shortcuts). Per ADR-004, adversarial results are **reported only**
  in v1 and do not gate ship.

## Model policy

**Opus is not allowed in this harness.** Tasks MUST declare either
`claude-haiku-4-5` or `claude-sonnet-4-6` explicitly. The runner validates this
before dispatching. Rationale: cost control (haiku for narrow tier, sonnet for
realistic) and reproducibility of the scoring model across batches.

## Adding a new task

1. Pick a tier directory.
2. Create `<tier>-<skill>-<nn>.yaml` using an existing file as template.
3. Ensure the `fixture` exists under `eval/fixtures/` (or create one).
4. Run the task once by hand to confirm the prompt lands and the grader fires.
5. Add the task id to the suite manifest (runner auto-discovers by default).

## Resolved plugin regressions

Issues the eval has caught and that have since been fixed in the plugin.
Kept here as historical context — these are the behaviors the canary
tasks (`narrow-non-rf-control-01` plus `narrow-rf-injection-positive-01`)
guard against re-introducing.

### `narrow-non-rf-control-01` — non-RF prompt no-op under static UserPromptSubmit (RESOLVED)

- **Was**: With the static `type: "prompt"` UserPromptSubmit hook and
  `claude-haiku-4-5`, a plain JSON-authoring prompt completed with
  `num_turns=0` and zero tool calls. The model produced ~93 output
  tokens of text and exited cleanly (`is_error=false`).
- **Cause**: the plugin injected "*If this request involves Robot
  Framework test automation, load the relevant skill's SKILL.md before
  responding...*" into every prompt. Haiku read this as a permission
  gate ("is this RF?" → no → done).
- **First seen**: CI run `25057802426` on 2026-04-28.
- **Fix**: branch `fix/plugin-hooks` converted UserPromptSubmit (and
  Stop) to `type: "command"` hooks that read the prompt on stdin and
  only inject context when an RF signal is present. The negative
  control task and a new `narrow-rf-injection-positive-01` task lock
  in both halves of the conditional behavior.

### `PostToolUse` matcher false alarm (NOT actually broken)

- **Was assumed**: `PostToolUse` with `matcher: "Write|Edit"` doesn't
  fire because the artifact stream JSON shows no `hook_*` events for
  it. (Documented as a separate issue during the PR #2 post-mortem.)
- **Reality**: the matcher works correctly. Claude Code 2.1.121 emits
  `hook_started/progress/response` envelopes for `SessionStart`-class
  events but **not** for `PostToolUse`. Hooks fire silently — verifying
  them requires inspecting side effects (log files, file changes), not
  the stream JSON.
- **Status**: no fix needed. Documented in
  `plugins/rf-agentskills/hooks/README.md` so future debugging doesn't
  chase the same false trail.

## References

- `docs/ci/rf-agentskills-eval-implementation-plan.md` — overall plan.
- `docs/ci/architecture/adr/ADR-004-scoring-model.md` — scoring rubric and
  gating logic (primary metrics must be externally grounded).
