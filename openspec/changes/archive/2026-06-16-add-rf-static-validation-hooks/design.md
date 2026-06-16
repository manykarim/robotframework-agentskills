## Context

The plugin ships four Claude Code hooks (`plugins/rf-agentskills/hooks/hooks.json`, mirrored under `installer/.../_assets/`). The `PostToolUse` hook runs `validate_robot.mjs` after Write/Edit. That script is a thin Node orchestrator that shells out to a recorded Python interpreter and calls `robot.api.get_model`.

Experiments on RF 7.4.2 / Robocop 8.2.11 / find-unused 0.9.0 established the current state and the tooling landscape:

- **`get_model` is a no-op for validation.** It is a lenient tokenizer that builds an AST with embedded error nodes and never raises. Across a matrix of broken files — unterminated `FOR`, undefined keyword, missing imports, argument-count mismatch, and even a file of pure random prose — it returned "OK, sections≥1" every time. The error nodes were not even reachable via a `ModelVisitor` for those cases.
- **Robocop covers the real per-file errors without noise — when scoped.** Default Robocop fires `DOC03 Missing documentation` (and ~130 other style rules) on a perfectly valid file and exits `1`, which would bury the agent in nags. `robocop check --threshold E` returns "No issues found" / exit `0` on a clean file and the precise `ERR12 ... FOR loop must have closing END` / exit `1` on the broken one. Robocop has 167 rules; the `ERR`/`ARG`/`IMP`/`DUP` categories are genuine problems, the rest are style.
- **`robot --dryrun` is powerful but project-scoped and side-effecting.** It catches undefined keywords, argument errors, and FOR errors with a non-zero exit. But: (a) it imports libraries (runs import-time code — can open browsers, hit DBs); (b) its exit code does NOT reflect import errors when the broken import is unused — those surface only as `[ ERROR ]` console lines (exit `0`); (c) it cannot run on a bare `.resource` file ("contains no tests"); (d) latency scales with suite size and import cost.
- **`robotframework-find-unused` is inherently whole-project.** `robotunused keywords .` correctly found an unused keyword and an undefined call, but only by parsing the entire project and importing every library. A keyword just written looks "unused" until something calls it; a call into a not-yet-written resource looks "undefined". Mid-task per-file use would false-alarm constantly.
- **Latency (tiny project, warm):** get_model 0.25s · robocop check 0.50s · format-check 0.51s · dryrun 0.41s · robotunused 0.71s. Per-file Robocop stays bounded; dryrun/find-unused scale with the project.

The Claude Code PostToolUse contract: exit `2` feeds stderr back to the model (tool already ran — non-blocking but visible to the agent); exit `1`/other is shown to the user, not reliably to the agent; exit `0` with JSON on stdout can supply `additionalContext`/`systemMessage`. PostToolUse cannot block (the write already happened) — only PreToolUse can deny. The current hook uses exit `1`, so even its rare failures would not reach the agent.

Other agentic systems (aider `--auto-lint`/`--auto-test`, Cursor 1.7 hooks, OpenAI Codex hooks) all implement the same edit→validate→feed-back→self-correct loop, and all warn that only real errors (not style) should be fed back.

## Goals / Non-Goals

**Goals:**
- Make per-file validation actually detect real structural errors, with zero style noise.
- Make detected errors reach the agent so it self-corrects (exit `2` + stderr).
- Add formatting consistency and opt-in project-wide semantic/dead-code checks at the right lifecycle points.
- Preserve the "never break the session" guarantee: silent no-op when tools are missing.
- Keep both distribution channels in sync (existing `sync-skills.sh` / `check-drift.sh`).

**Non-Goals:**
- Blocking writes before they happen (PreToolUse). PostToolUse + exit 2 self-correction is sufficient and simpler.
- Replacing or extending the rf-mcp server (a Robocop-MCP-based path is noted as future work, not built here).
- Making Robocop/find-unused hard dependencies, or auto-installing them without consent.
- Enforcing a project-specific Robocop style config; this change ships error-severity defaults only.
- Auto-applying formatter changes to files the agent wrote (surface as suggestion only, at least initially).

## Decisions

### D1: Per-file check = `robocop check --threshold E`, replacing `get_model`
Validated recipe: clean file → exit 0/"No issues found"; broken file → exit 1 with the exact error and location. This is the only candidate that catches real structural errors per-file with no style noise and bounded latency, no side effects (purely static).
- *Alternatives considered:* keep `get_model` (rejected — proven no-op); custom AST `ModelVisitor` walking for ERROR tokens (rejected — reimplements a subset of Robocop's `ERR` rules with more code and less coverage); `robot --dryrun` per file (rejected for per-file — side effects, can't handle bare `.resource`, project-scoped).

### D2: Failures exit `2` (not `1`) and write the diagnostic to stderr
This is the single change that turns validation from invisible to corrective, matching the aider/Cursor/Codex feedback loop. Optionally also emit exit-0 JSON `additionalContext` as a richer channel, but exit 2 + stderr is the baseline and most portable.
- *Alternative:* exit 1 (current) — rejected, the agent never sees it.

### D3: Lifecycle split — per-file on `PostToolUse`, project-wide on `Stop`
Per-file static checks (Robocop check + format) run on every Write/Edit. Cross-file/semantic checks (`--dryrun`, find-unused) run once at end of turn on `Stop`, when the whole project is on disk and intermediate states won't false-alarm.
- *Rationale:* directly mirrors the per-file vs whole-project nature found in experiments. Running find-unused/dryrun per-save would be slow, side-effecting, and full of false positives on half-written work.

### D4: Project-wide tier is opt-in via env flag, default off
`--dryrun` imports libraries (side effects) and both tools scale with project size. Default-on would risk surprising side effects and slow turns. Gate behind a documented env flag (e.g. `RF_AGENTSKILLS_PROJECT_VALIDATION=1`).
- *Alternative:* default on — rejected on side-effect/latency risk.

### D5: Dry-run result derived from `[ ERROR ]` output, not exit code alone
Because dryrun exits `0` on unused-but-broken imports, the Stop-tier script parses stdout/stderr for `[ ERROR ]` lines in addition to checking the exit code.

### D6: Graceful degradation preserved
Reuse the existing interpreter-resolution pattern (`python_runtime.json` → fallbacks). Each tier probes for its tool (e.g. `robocop --version`, import check) and exits `0` silently if absent. Robocop/find-unused are optional; the installer may *offer* to install them.

### D7: Implement as the existing Node-orchestrator pattern; plugin is the single source of truth
Keep `validate_robot.mjs` as a Node wrapper (matches the Windows-compatibility rationale behind commit history) and add a parallel `validate_robot_project.mjs` for the Stop tier. Edit only `plugins/rf-agentskills/` — that tree is the canonical source.
- *Correction discovered during implementation:* the installer's `src/rf_agentskills/_assets/` tree is **gitignored and regenerated at build time** by `installer/hatch_build.py` (`shutil.copytree(plugins/rf-agentskills → _assets)`). It is NOT a manually-maintained mirror, so there is no manual sync step for the hooks and no plugin↔installer drift check to add (such a check would wrongly fail on a fresh checkout before any build). `sync-skills.sh` / `check-drift.sh` continue to cover only the root→plugin Python *skill* scripts, which is a separate concern.

## Risks / Trade-offs

- **Robocop default ruleset is noisy** → Mitigation: hard-scope to `--threshold E` (error severity) so style rules can't fire; document how users opt into stricter checking.
- **The current hook may never run at all** (reads `TOOL_INPUT` env var; documented contract is stdin JSON) → Mitigation: a task to empirically verify the input channel and read whichever the running Claude Code version actually provides (support both: try stdin JSON, fall back to `TOOL_INPUT`).
- **`--dryrun` side effects** (library imports execute code) → Mitigation: opt-in only, default off, documented warning; never run per-save.
- **False positives from find-unused on libraries it can't import** → Mitigation: Stop-tier only, treat "undefined" cautiously, surface as informational where ambiguous; document that public/library keywords may appear "unused".
- **Latency on large suites** (dryrun/find-unused) → Mitigation: opt-in; bound or document; per-file tier stays Robocop-only.
- **New optional dependencies** (`robotframework-robocop`, `robotframework-find-unused`) → Mitigation: optional, silent no-op when absent; surfaced via installer prompt, not forced.
- **Self-correction loop on a false positive could waste a turn** → Mitigation: threshold-E keeps per-file feedback high-signal; formatting differences are suggestion-only (never exit 2).

## Open Questions

- Should Tier 2 (formatting) eventually **auto-apply** `robocop format` to agent-written files (aider-style) rather than only suggest? Start with suggest; revisit.
- Should the project-wide tier live in the **rf-mcp server** (Robocop ships an official MCP server) instead of a Stop hook, giving the agent an on-demand `validate` tool with controlled side effects? Out of scope here; worth a follow-up.
- Exact env flag name(s) and whether per-tier granularity (separate flags for dryrun vs find-unused) is warranted.
- Whether to also wire `additionalContext` JSON (exit 0) in addition to exit-2 stderr, for richer feedback on Claude Code versions that support it.
