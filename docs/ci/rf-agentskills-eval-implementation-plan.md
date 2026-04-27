# Implementation Plan — Evaluating `robotframework-agentskills`

A concrete, buildable plan for measuring whether the skills in `robotframework-agentskills` actually improve Claude Code's behavior on Robot Framework engineering tasks. Scoped to what one person can execute in ~2 weeks part-time, with enough rigor to defend the results at RoboCon.

---

## 0. Goals and non-goals

**Goals**
- Produce a signed per-skill scorecard: ship, iterate, or remove.
- Detect regressions in already-shipped skills when the underlying Claude model changes.
- Generate reusable task bank + harness that can grade future skills without redesign.

**Non-goals (for v1)**
- No human-evaluator rubric. All metrics are derived from session logs or automated test pass/fail.
- No multi-user generalization. Grades reflect *your* tasks; that's fine — they're the tasks the skills exist to support.
- No real-time dashboard. Batch HTML report is enough.

---

## 1. Repository layout

A single new repo, `rf-skill-eval`, with these top-level directories:

```
rf-skill-eval/
├── pyproject.toml
├── README.md
├── src/
│   └── rf_skill_eval/
│       ├── __init__.py
│       ├── telemetry/          # JSONL + hook-log parsing
│       │   ├── parser.py
│       │   ├── metrics.py
│       │   └── schema.py
│       ├── runner/             # Orchestrates Claude Code sessions
│       │   ├── profiles.py     # Skill on/off profile mgmt
│       │   ├── executor.py     # Invokes `claude` CLI headless
│       │   └── capture.py      # Copies JSONL + hook logs into runs/
│       ├── tasks/              # Task bank loader + grader
│       │   ├── loader.py
│       │   └── grader.py       # Runs RF to check task success
│       ├── analysis/
│       │   ├── stats.py        # Mann-Whitney, Cliff's delta, bootstrap CI
│       │   └── aggregate.py
│       └── report/
│           ├── scorecard.py    # Jinja2 → HTML
│           └── templates/
├── tasks/                      # YAML task definitions
│   ├── narrow/
│   ├── realistic/
│   └── adversarial/
├── fixtures/                   # Git-pinned RF project snapshots
│   └── sut-*/                  # "system under test" repos
├── runs/                       # Output: one dir per run, gitignored
└── reports/                    # Output: HTML + JSON scorecards
```

Stack: Python 3.12, `uv` for deps, `pydantic` for schemas, `polars` for metrics dataframes, `scipy.stats` + `numpy` for stats, `jinja2` for reports, `robotframework` for the grader. Everything you already use.

---

## 2. Telemetry layer — parsing session logs

### 2.1 Input sources

Claude Code writes session JSONL files to `~/.claude/projects/<project-slug>/*.jsonl`. Each line is one of: `user`, `assistant`, `tool_use`, `tool_result`, `thinking`, `summary`. Hook logs go wherever your hooks write them (standardize on `~/.claude/hooks/<hook-name>.log` with one JSON object per line: `{ts, session_id, category, matched_phrase, injected_text}`).

### 2.2 Parsed schema

```python
# telemetry/schema.py
class ToolCall(BaseModel):
    session_id: str
    turn_idx: int
    timestamp: datetime
    name: str                    # "Read", "Edit", "Write", "Bash", "mcp__rf-mcp__*", ...
    input: dict
    result_ok: bool
    result_bytes: int

class ThinkingBlock(BaseModel):
    session_id: str
    turn_idx: int
    content_chars: int | None    # None if redacted
    signature_chars: int
    estimated_chars: int         # signature_chars * 0.378 (issue's regression)

class UserMessage(BaseModel):
    session_id: str
    turn_idx: int
    text: str
    is_interrupt: bool           # text contains "[Request interrupted by user]"
```

### 2.3 Metrics functions

One pure function per metric. Each takes a list of parsed rows and returns a scalar or a small dict.

```python
# telemetry/metrics.py
def read_edit_ratio(calls: list[ToolCall]) -> float:
    reads = sum(c.name in READ_TOOLS for c in calls)
    edits = sum(c.name in EDIT_TOOLS for c in calls)
    return reads / edits if edits else math.inf

def edits_without_prior_read_pct(calls: list[ToolCall], window: int = 20) -> float:
    # For each Edit, check whether the same file was Read in the prior `window` tool calls.
    ...

def reasoning_loops_per_1k(assistant_text: str, tool_count: int) -> float:
    patterns = [r"\bwait\b", r"\bactually\b", r"let me reconsider", r"hmm,? actually"]
    hits = sum(len(re.findall(p, assistant_text, re.I)) for p in patterns)
    return 1000 * hits / tool_count if tool_count else 0

def simplest_rate_per_1k(assistant_text: str, tool_count: int) -> float:
    return 1000 * len(re.findall(r"\bsimplest\b", assistant_text, re.I)) / tool_count

def user_interrupts_per_1k(users: list[UserMessage], tool_count: int) -> float:
    return 1000 * sum(u.is_interrupt for u in users) / tool_count
```

Ship 15–20 of these. The full list lives in the Metrics Catalog (§6).

### 2.4 RF-specific metrics

These are the ones that matter most for judging `robotframework-agentskills`, and they don't exist in the generic issue #42796 analysis:

| Metric | Definition |
|---|---|
| **rf-mcp call rate** | `mcp__rf-mcp__*` tool calls per task |
| **Execution-before-completion** | Did the session contain ≥1 successful `Run Keyword` / `Run Tests` rf-mcp call before the agent claimed done? Boolean per task. |
| **Keyword doc lookups before use** | For each new keyword the agent writes, was there a prior `List Keywords` / `Get Keyword Documentation` rf-mcp call? % |
| **Library import resolution rate** | Of library imports the agent wrote, what % imported cleanly on first run? |
| **Keyword naming convention score** | % of newly created keywords using Space Separated Title Case vs `snake_case` or `CamelCase` |
| **Section ordering violations** | Settings → Variables → Keywords → Test Cases order violated (count per file) |
| **Resource file usage** | Did the agent extract shared keywords into `.resource` files when it created >N? Boolean |
| **First-run test pass rate** | % of test files the agent produced that passed on the first `robot` invocation |

Extract these during parsing by pattern-matching tool inputs and by re-running the produced RF files in the grader.

---

## 3. Task bank

### 3.1 Task schema

```yaml
# tasks/narrow/browser-login-test.yaml
id: narrow-browser-login
tier: narrow
timeout_min: 8
fixture: sut-login-app          # git-pinned project in fixtures/
skill_scope: [browser-library, test-authoring]
prompt: |
  Write a Robot Framework test using the Browser library that logs into the
  demo app at http://localhost:3000 with user "demo" / password "demo" and
  verifies the dashboard shows "Welcome, demo".
  Put the test in tests/login.robot.
success_criteria:
  - type: robot_pass
    path: tests/login.robot
  - type: file_exists
    path: tests/login.robot
  - type: no_deprecated_keywords    # grader lints the produced file
adversarial_flags: []
```

### 3.2 Tiers (from §3.2 of the prior doc, concretized)

**Narrow (20–30 tasks, ~5 min each).** One skill expected to trigger per task. Examples:
- Write a test using a specified library
- Add a new keyword to a resource file following project conventions
- Convert an inline value to a variable file entry
- Debug a keyword-not-found error given a failing log
- Add a tag-based test selection to an existing suite
- Write a Python library with two keywords using the hybrid API
- Add Listener v3 hooks to an existing library
- Extract duplicated steps into a Resource file

**Realistic (6–10 tasks, 20–40 min each).** Multi-step, multi-file changes that approximate real work:
- Migrate a SeleniumLibrary suite (5 tests) to Browser library
- Add data-driven testing to an existing suite using a CSV data source
- Build a small custom library for interacting with a REST API + write tests using it
- Refactor a flat suite into Setup/Teardown + resource file structure + retry logic
- Add doctestlibrary-style visual assertions to an existing PDF verification suite
- Investigate and fix a flaky test (fixture contains a real race condition)

**Adversarial (8–12 tasks).** Tempt the failure modes `agentskills` are meant to prevent:
- "Just make this test pass" where the correct fix is in the product, not the test
- A task where the obvious keyword is deprecated; correct answer requires reading library docs
- Convention-pressure task: existing code violates project conventions; agent should not propagate
- Task that looks like it needs a new library but can be solved with an existing resource file
- Task where generating the code is easy but requires executing it to discover a runtime issue (tests the rf-mcp execution-before-completion behavior)

### 3.3 Fixtures

Each fixture is a real RF project at a specific git SHA, copied fresh for every run (`git worktree add` or `cp -r`). Include:
- A small RF project using Browser library
- A legacy SeleniumLibrary project
- A library-development project with pyproject.toml
- An rf-doctestlibrary user project (dogfoods your own work)
- A corporate-style layered project (resource files, Python libs, CI config)

Pin every fixture by SHA in the task YAML so results are reproducible.

---

## 4. Runner — A/B execution

### 4.1 Profile isolation

The cleanest way to toggle the skill bundle is via `CLAUDE_CONFIG_DIR`. Create two profiles:

```
~/rf-eval-profiles/
├── control/       # no robotframework-agentskills installed
│   ├── CLAUDE.md  # identical minimal system context for both arms
│   └── skills/    # only whatever baseline skills are common to both
└── treatment/
    ├── CLAUDE.md
    └── skills/
        └── robotframework-agentskills/   # the package under test
```

Both profiles get the same `CLAUDE.md`, same MCP server config (rf-mcp is available to both — it's infrastructure, not the subject of evaluation), same hook set. The *only* difference is the skills directory content.

For per-skill isolation (evaluating one skill at a time vs the whole bundle), generate a matrix of profiles: `treatment-skill-A`, `treatment-skill-B`, ..., `treatment-all`. This lets you attribute effects to individual skills, which matters for deciding what to ship.

### 4.2 Headless invocation

Use Claude Code's print mode:

```bash
CLAUDE_CONFIG_DIR=~/rf-eval-profiles/treatment \
  claude -p "$(cat tasks/narrow/browser-login-test.yaml | yq .prompt)" \
  --output-format stream-json \
  --max-turns 40 \
  --allowedTools "Read,Edit,Write,Bash,mcp__rf-mcp__*" \
  > runs/$RUN_ID/stdout.jsonl
```

Before each invocation, `cd` into a fresh copy of the task's fixture. After the invocation returns (or times out), copy:
- The session JSONL from `~/.claude/projects/`
- Any hook log lines emitted during the run (filter by start/end timestamps)
- The final state of the fixture directory
- The stdout stream-json

into `runs/<run_id>/`.

### 4.3 Randomization and replication

For each `(task, skill_config)` cell, run N=8 replicates. Randomize the order of cells across a run-batch so that time-of-day effects (which the issue shows are real) don't confound a single arm. A run batch of 30 tasks × 2 arms × 8 replicates = 480 sessions. At ~10 min average, that's ~80 hours of wall clock — parallelize to 4–8 concurrent sessions on different fixtures to bring it to overnight.

Record run metadata: Claude Code version, model name, timestamp, profile, task id, fixture SHA, replicate idx, exit reason (normal / timeout / tool error).

### 4.4 Grader

After each run, `grader.py` reads the fixture end-state and applies the `success_criteria` from the task YAML:

```python
class RobotPassCriterion(BaseModel):
    type: Literal["robot_pass"]
    path: str
    def grade(self, fixture_dir: Path) -> GradeResult:
        proc = subprocess.run(
            ["robot", "--outputdir", "grader-out", self.path],
            cwd=fixture_dir, capture_output=True, timeout=120,
        )
        return GradeResult(passed=proc.returncode == 0, detail=proc.stdout[-2000:])
```

Criterion types: `robot_pass`, `file_exists`, `file_contains`, `no_deprecated_keywords`, `lint_clean` (ruff/robotidy), `import_resolves`, `custom_python` (arbitrary hook). Keep the set small and composable.

---

## 5. Analysis — statistical comparison

### 5.1 Per-metric test

For every metric × every (task, skill-config) pair:

```python
def compare_arms(control: np.ndarray, treatment: np.ndarray) -> ArmCompare:
    u, p = mannwhitneyu(treatment, control, alternative="two-sided")
    delta = cliffs_delta(treatment, control)
    ci_low, ci_high = bootstrap_diff_ci(treatment, control, n=10_000, alpha=0.05)
    return ArmCompare(
        median_control=np.median(control),
        median_treatment=np.median(treatment),
        delta=delta,           # Cliff's δ in [-1, +1]
        p_value=p,
        ci_95=(ci_low, ci_high),
        n_control=len(control),
        n_treatment=len(treatment),
    )
```

### 5.2 Shipping gate

A skill (or bundle) earns a green score when:
1. At least one *primary* quality metric improves with |δ| ≥ 0.33 ("medium" effect) and 95% CI excluding zero.
2. No primary quality metric regresses with |δ| ≥ 0.33.
3. Token cost increase ≤ 30% (tunable; context-heavy skills that meaningfully help can justify more).
4. End-to-end task success rate does not decrease.

Primary quality metrics for RF skills: first-run test pass rate, execution-before-completion rate, user-interrupts per 1K tool calls, convention-violation rate.

Secondary: Read:Edit ratio, reasoning loops per 1K, "simplest" rate.

Secondary metrics can flag concerns but not gate.

### 5.3 Multiple testing

With ~20 metrics × ~10 skills you'll hit false positives on p-values. Two defenses:
- Primary metrics are a small, pre-registered set (4 per skill). Apply Benjamini-Hochberg only on the primary set.
- Secondary metrics are exploratory; report them with effect sizes and CIs, not pass/fail.

---

## 6. Metrics catalog (the full list)

Grouped by family. Each line is `metric_id — unit — how_to_compute`.

**Tool workflow**
- `read_edit_ratio` — ratio — reads / edits
- `research_mutation_ratio` — ratio — (Read+Grep+Glob) / (Edit+Write)
- `edits_without_prior_read_pct` — % — edits where same file not read in prior 20 tool calls
- `write_share_of_mutations_pct` — % — Write / (Write + Edit)
- `repeated_edit_burst_count` — count — bursts of ≥3 edits to same file in ≤5 tool calls

**Thinking depth (for context, not gating)**
- `thinking_block_count` — count
- `median_signature_chars` — chars
- `estimated_thinking_chars` — chars (signature × 0.378)

**Linguistic quality**
- `reasoning_loops_per_1k` — per 1K tool calls
- `simplest_rate_per_1k` — per 1K
- `self_admitted_failure_rate_per_1k` — per 1K
- `ownership_dodging_rate_per_1k` — per 1K

**User signals**
- `user_interrupts_per_1k` — per 1K
- `user_corrections_per_task` — count — user messages containing "no,", "stop", "that's wrong"
- `frustration_word_rate` — per 1K words

**RF-specific (the important ones for this eval)**
- `rf_mcp_calls_per_task` — count
- `executed_before_complete` — bool — per task
- `keyword_doc_lookup_rate` — % — doc lookups / new keywords used
- `library_import_first_try_ok_pct` — %
- `keyword_naming_convention_pct` — %
- `section_order_violations_per_file` — count
- `first_run_test_pass_pct` — %
- `resource_file_extraction_appropriate` — bool — given ≥3 duplicate keyword blocks

**Outcome / cost**
- `task_success` — bool — grader verdict
- `time_to_success_min` — min
- `turns_to_success` — count
- `input_tokens_per_task` — tokens
- `output_tokens_per_task` — tokens
- `cache_read_tokens_per_task` — tokens

---

## 7. Results overview — the scorecard

### 7.1 Per-skill HTML report

One page per skill, one page per bundle, one index page. Sections:

1. **Header** — skill name, version SHA, Claude Code version, model, dates, N tasks, N replicates.
2. **Verdict** — big green/yellow/red badge. One sentence rationale.
3. **Primary metrics table** — median control / median treatment / δ / 95% CI / gate pass.
4. **Secondary metrics table** — same columns, no gate.
5. **Per-task breakdown** — success rate and key metrics per task id, sortable.
6. **Failure gallery** — for tasks that regressed, 3 example session transcripts side-by-side (control success, treatment failure).
7. **Cost table** — tokens and wall time.
8. **Raw data link** — path to the run artifacts.

### 7.2 Longitudinal view

One row per weekly eval run, tracking primary metrics for each shipped skill over time. Annotate Claude Code / model version changes. This is the canary from §3.4 of the prior doc — when a row turns red with no skill change, the model regressed.

### 7.3 Sample scorecard (illustrative, populated from real runs later)

```
=== Skill: rf-mcp-execution-first v0.4.1 ===================================
Task bank: rf-full-v1 (narrow=24, realistic=8, adversarial=10)
N = 8 replicates per (task, arm). Total sessions: 672.
Claude Code: 1.x.y | Model: claude-opus-4-6 | Window: 2026-04-10..12

PRIMARY METRICS                        control    treatment   δ      95% CI          gate
  first_run_test_pass_pct              58%        81%         +0.52  [+0.35, +0.68]  ✓
  executed_before_complete             61%        94%         +0.66  [+0.52, +0.78]  ✓
  user_interrupts_per_1k               4.1        1.6         -0.44  [-0.58, -0.29]  ✓
  convention_violations_per_task       2.7        0.9         -0.48  [-0.63, -0.32]  ✓

SECONDARY METRICS                      control    treatment   δ      95% CI
  read_edit_ratio                      3.8        5.4         +0.29  [+0.14, +0.43]
  reasoning_loops_per_1k               18.3       12.1        -0.34  [-0.48, -0.19]
  simplest_rate_per_1k                 5.1        2.8         -0.37  [-0.52, -0.21]
  edits_without_prior_read_pct         22%        11%         -0.41  [-0.55, -0.26]

COST                                   control    treatment   delta
  input_tokens_per_task (mean)         38,400     47,900      +24.7%
  output_tokens_per_task (mean)        11,200     9,300       -17.0%
  wall_time_per_task (median)          14.2 min   11.6 min    -18.3%

VERDICT: SHIP
Primary quality gains are large and consistent. Context overhead (+25%) is
within threshold and more than offset by shorter runs and fewer retries.
Two adversarial tasks (adv-fix-product-not-test, adv-deprecated-keyword) show
no significant movement — next iteration should target those.
```

---

## 8. Phased delivery

**Phase 1 — Telemetry library (days 1–3).**  
Parse session JSONLs → dataframe. Implement 8 metrics from §6 (the ones not requiring the grader). Unit tests on synthetic sessions. One-command CLI: `rf-skill-eval metrics <run-dir>` prints a table.

**Phase 2 — Runner + 5 narrow tasks (days 4–6).**  
Profile isolation via `CLAUDE_CONFIG_DIR`. Headless invocation. Capture pipeline. 5 narrow tasks in YAML. Run 4 replicates × 2 arms × 5 tasks = 40 sessions end-to-end. Sanity-check the numbers.

**Phase 3 — Grader + RF-specific metrics (days 7–9).**  
`robot_pass`, `file_exists`, `file_contains`, `no_deprecated_keywords` criteria. Implement RF-specific metrics from §6. Re-run Phase 2 sessions through the grader.

**Phase 4 — Stats + scorecard (days 10–12).**  
Mann-Whitney, Cliff's delta, bootstrap CI. Jinja HTML template. Run first real scorecard on a single skill of your choice (suggest: `rf-mcp-execution-first` or whichever is most recently updated).

**Phase 5 — Expand task bank + bundle eval (days 13–14).**  
Fill out narrow to 20 tasks, add 3 realistic tasks, 4 adversarial tasks. Run the full bundle eval. Commit results.

**Phase 6 — Weekly cron (ongoing).**  
`systemd` timer or GH Actions runner that re-runs the eval weekly and appends a row to the longitudinal view. Alert (email via n8n on your Netcup box) if any primary metric moves >2σ from the 30-day baseline.

---

## 9. Practical gotchas and how to handle them

- **Sessions that hang.** `--max-turns 40` + a wall clock timeout. Label timed-out runs and keep them in the data — "failed to finish" *is* an outcome.
- **Stochastic tool-call ordering.** N=8 per cell gives tolerable noise for medium effects; bump to N=15 for adversarial tier where variance is higher.
- **Fixture pollution.** Always `cp -r` or `git worktree add` a clean fixture per run. Never run twice in the same dir.
- **Hook log ordering.** Hooks may buffer; include a 2-second post-run sleep before collecting logs, and key by session_id rather than timestamp windows when possible.
- **rf-mcp flakiness.** rf-mcp itself is under development. Pin its version per eval batch and record it in run metadata. If a skill looks bad, check whether rf-mcp changed.
- **Model drift during a batch.** Record model + CC version on every run. If a batch straddles a model release, split the analysis.
- **Self-scoring bias.** Several metrics (reasoning loops, "simplest" rate) are measured from the assistant's own output. These will improve if you make a skill that just tells the agent "don't say 'simplest'." Primary gate metrics are grounded in external reality (test pass, grader, user interrupt) for exactly this reason.
- **Skill ordering effects.** When evaluating individual skills within a bundle, the order in which Claude Code loads them can matter. Hold bundle composition fixed when attributing per-skill effects; use "leave-one-out" rather than "add-one-in" for cleaner attribution.

---

## 10. Open questions worth deciding before you start

1. **Which skill ships first through the harness?** Recommend the most-used one — gets the most downstream value from the eval and exercises the harness on realistic task breadth.
2. **Single-skill vs bundle as the unit of evaluation?** Start with bundle (easier, bigger effect size), add per-skill attribution in Phase 5+.
3. **Is the adversarial tier part of the ship gate or only reported?** Suggest reported-only for v1; those tasks are where you learn what to build next, not whether to ship what you have.
4. **Public or private?** If the eval harness itself goes public, it becomes a community contribution (RoboCon talk, blog series). The task bank and fixtures can stay private if they contain proprietary patterns.

---

## Appendix — Minimal first script

If you want to see numbers today, this ~80-line script computes 6 metrics from an existing run directory and prints a table. It's the seed of `telemetry/metrics.py`.

```python
# quick_metrics.py
import json, re, sys
from pathlib import Path
from collections import Counter

READ_TOOLS = {"Read", "Grep", "Glob"}
EDIT_TOOLS = {"Edit", "MultiEdit"}
WRITE_TOOLS = {"Write"}
LOOP_PATTERNS = [r"\bwait\b", r"\bactually\b", r"let me reconsider"]

def parse_jsonl(path):
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]

def metrics_for_session(events):
    reads = edits = writes = rf_mcp = 0
    assistant_text = []
    interrupts = 0
    for e in events:
        if e.get("type") == "assistant":
            for b in e.get("message", {}).get("content", []):
                if b.get("type") == "text":
                    assistant_text.append(b["text"])
                elif b.get("type") == "tool_use":
                    name = b.get("name", "")
                    if name in READ_TOOLS: reads += 1
                    elif name in EDIT_TOOLS: edits += 1
                    elif name in WRITE_TOOLS: writes += 1
                    if name.startswith("mcp__rf-mcp__"): rf_mcp += 1
        elif e.get("type") == "user":
            text = str(e.get("message", {}).get("content", ""))
            if "[Request interrupted by user]" in text:
                interrupts += 1
    tool_count = reads + edits + writes
    text = "\n".join(assistant_text)
    loops = sum(len(re.findall(p, text, re.I)) for p in LOOP_PATTERNS)
    return {
        "tool_count": tool_count,
        "read_edit_ratio": reads / edits if edits else None,
        "write_share_mutations_pct": 100 * writes / (writes + edits) if (writes + edits) else 0,
        "rf_mcp_calls": rf_mcp,
        "reasoning_loops_per_1k": 1000 * loops / tool_count if tool_count else 0,
        "user_interrupts": interrupts,
    }

if __name__ == "__main__":
    for jsonl in Path(sys.argv[1]).glob("**/*.jsonl"):
        m = metrics_for_session(parse_jsonl(jsonl))
        print(jsonl.name, m)
```

Point it at `~/.claude/projects/<some-rf-project>/` and you have Phase 1's MVP running before you've finished your coffee. Everything after that is making it rigorous, reproducible, and pretty.
