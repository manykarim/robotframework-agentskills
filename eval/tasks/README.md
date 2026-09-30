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
| `id` | yes | string | Unique task id. Convention: `<tier>-<skill>-<nn>` (adversarial: `adv-<topic>`). |
| `skill` | yes | string | The `name` of a shipped skill under `skills/*/SKILL.md` (e.g. `rf-libdoc`), or `plugin` for bundle-level canaries (hooks, "don't cheat" behaviour). Retired skills are rejected. |
| `tier` | yes | enum | `narrow` \| `realistic` \| `adversarial`; must match the directory. |
| `description` | yes | string | Human-readable summary of the task. |
| `prompt` | yes | string | Exact text fed to `claude -p`. Should be ecologically realistic. |
| `model` | no | enum | `claude-haiku-4-5-20251001` or `claude-sonnet-5`. Defaults by tier (narrow → Haiku, realistic/adversarial → Sonnet). `claude-opus-5-5` is **never** allowed in YAML — see *Model policy*. |
| `max_turns` | yes | int | Upper bound on agent turns. |
| `timeout_seconds` | yes | int | Wall-clock budget for the session. |
| `allowed_tools` | yes | list[string] | Claude Code tool allowlist (passed via `--allowedTools`). |
| `mcp_servers` | no | list[string] | Per-task MCP servers (`rf-mcp`), provisioned identically in **both** arms. Required when `allowed_tools` contains `mcp__rf-mcp__*`. Plugin MCP servers (`rf-tools`) come with the treatment arm only. |
| `expected_files` | no | list[object] | Files the agent is expected to produce (`path`, optional `must_contain`). Informational; does not gate. |
| `grader_checks` | yes | list[object] | Applied to the workspace end-state / transcript. See below. |
| `fixture` | yes | string | Fixture directory name under `eval/fixtures/`. |
| `primary_metric` | yes | string | Grader-check `type` whose checks are **gating** (per ADR-004). |

Every task needs at least one gating check. `rf-skill-eval validate-tasks eval/tasks`
enforces all of the above (it also runs when a batch starts).

## Grader check types

Every check may also set `gating: true|false` (default: `type == primary_metric`)
and `category: outcome|process` (default: `process` for the `tool_*` checks,
`outcome` otherwise). Process checks describe *how* the agent worked (e.g. "the
skill was invoked"); they are reported for the treatment arm but excluded from
arm deltas, so the baseline arm is never penalised for not using a skill it
does not have.

| Type | Fields | Semantics |
|---|---|---|
| `file_exists` | `path` | Path must exist inside the workspace. |
| `file_contains` | `path`, `regex` | File must contain a match (MULTILINE). Missing file → `failed`. |
| `file_not_contains` | `path` (glob allowed), `regex` | No file may match. Missing file → `failed`. |
| `robot_pass` | `target`, opt. `args`, `expected_tests`, `expected_tests_exact`, `requires` | `robot <target>` (cwd = workspace) exits 0 with ≥ 1 test; `expected_tests` = minimum number of **passed** tests (catches skipped tests); with `expected_tests_exact: true` exactly that many tests must exist and pass (a mismatch names expected and actual counts); `requires` = modules that must be importable, else `skipped`. |
| `robot_dryrun` | `target`, opt. `args`, `expected_tests`, `expected_tests_exact`, `requires` | `robot --dryrun`: parses the suite and resolves imports and keywords; the count options work as for `robot_pass` (e.g. `args: [--include, smoke]` with an exact count checks tag selection). |
| `keywords_resolve` | `target`, `specs`, opt. `required_libraries`, `min_calls` | Static: every keyword call resolves against suite/resource user keywords, standard libraries and the given libdoc JSON specs (committed under the fixture's `specs/`). `skipped` only when a spec file is missing. Used where the library cannot run on CI (appium, platynui). |
| `no_deprecated_keywords` | `target` | Rejects `Run Keyword If`/`Unless`, `Return From Keyword`. |
| `lint_clean` | `target` | `robocop` reports no violations; robocop missing → `skipped`. |
| `import_resolves` | `path` or `module` | `Library`/`Resource` imports resolve. |
| `custom_python` | `func_ref` | `module:function` returning bool/dict/Verdict; an exception → `error`. Task-specific checks live in `rf_skill_eval.scoring.custom` (e.g. `custom.language`: `hidden_suite`, `file_unchanged`, `any_file_contains`, `no_typed_variables`, `pinned_robot_pass`, `robocop_clean`; `custom.python_library`: `hidden_suite` with `listener` / `expected_rc` / `expected_statuses`, `checker_findings_absent`); hidden grader suites are kept in `eval/graders/<topic>/`, outside the staged fixture. |
| `tool_call_count` / `tool_result_count` / `tool_call_sequence` | see `scoring/session_based.py` | Transcript checks; no transcript → `skipped`. |

## Verdicts and gate results

A verdict is `passed`, `failed`, `skipped` (could not be evaluated: tool
missing, library not importable, no transcript — with a reason) or `error`
(grader defect). `skipped`/`error` never count as passes. A run's gate result
is `pass` when every gating check passed, `fail` when any gating check failed,
and `incomplete` otherwise (a gating check skipped/errored, the run never
started because of the cost cap, or an arm leak). CI treats `incomplete` as a
failure.

## Arms and replicates

`rf-skill-eval run-batch --arms treatment,baseline --runs 3` runs every task
in both arms (treatment = the plugin as shipped; baseline = no plugin parts,
everything else identical) three times each, in fresh workspaces. Reports show
per-arm pass rate, tokens, turns, duration and cost, the treatment − baseline
delta (outcome checks only; "unavailable" when an arm is missing), and flag
flaky tasks (0 < pass rate < 1).

## Tier definitions

- **narrow** — Exercise a single skill (at least one per shipped skill; checked
  by `rf-skill-eval coverage`). Deterministic graders. Haiku.
- **realistic** — Multi-step work that approximates a real user session.
  Multiple files, sometimes real execution (Browser library, API client).
  Sonnet.
- **adversarial** — Deliberately tempts failure modes skills are meant to
  prevent: deprecated / non-existent keywords (`adv-browser-deprecated-wait`,
  `adv-selenium-nonexistent-kw`), installing into the system Python
  (`adv-setup-system-pip`), the wrong web library (`adv-web-wrong-library`),
  "just make it pass" shortcuts (`adv-make-it-pass`) and library gotchas the
  skills document (`adv-restinstance-expectation-leak`,
  `adv-appium-deprecated-visibility`), and legacy or too-new Robot Framework
  syntax the prompt asks for (`adv-language-force-tags-01`,
  `adv-language-rf71-typed-01`). Reported with the same
  arm deltas but **never gates** merges. Sonnet.

## Model policy

Allowed ids: `claude-haiku-4-5-20251001` (narrow tier, trigger evals, PRs),
`claude-sonnet-5` (realistic and adversarial tiers) and `claude-opus-5-5`.
Task YAML and trigger sets may declare Haiku or Sonnet only. Opus is an
explicit run-time opt-in for manual runs — `--model claude-opus-5-5
--allow-opus --max-cost-usd <cap>` — used to check that a skill does not hurt
the strongest model; it never runs on PRs or the weekly schedule. Retired ids
are rejected with a migration hint (see ADR-004).

Every batch, trigger and gate command accepts `--max-cost-usd`. When the
reported cost reaches the cap, no further session starts, the remaining runs
are recorded as `incomplete` (reason `budget`) and the command exits non-zero.

## Trigger evals

Skill *descriptions* (does the agent load the right skill?) are tested
separately from skill bodies with per-skill query sets — see
[eval/triggers/README.md](../triggers/README.md)
for the format and the train/validation discipline.

## Adding a new task

1. Pick a tier directory.
2. Create `<tier>-<skill>-<nn>.yaml` using an existing file as template.
3. Ensure the `fixture` exists under `eval/fixtures/` (or create one).
4. Run `uv run rf-skill-eval validate-tasks eval/tasks` and
   `uv run rf-skill-eval coverage`.
5. Run the task once by hand (`uv run rf-skill-eval run --task … --max-cost-usd 1`)
   to confirm the prompt lands and the grader fires.

## Resolved plugin regressions

Issues the eval has caught and that have since been fixed in the plugin.
Kept here as historical context — these are the behaviors the canary
tasks (`narrow-non-rf-control-01` plus `narrow-rf-injection-positive-01`,
both `skill: plugin`) guard against re-introducing.

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
