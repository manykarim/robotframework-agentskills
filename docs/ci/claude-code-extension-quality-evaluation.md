# Evaluating the Quality of Custom Claude Code Extensions
## Metrics derived from issue #42796, applied to Agent Skills, Hooks, and SubAgents

---

## Part 1 — Metrics collected in issue #42796

The issue analyzes 6,852 session JSONL files, 17,871 thinking blocks, 234,760 tool calls, and ~18,000 user prompts. The metrics fall into seven families.

### 1.1 Thinking-depth metrics
- **Thinking block count** per session and per response
- **Thinking content length (chars)** per block
- **Signature field length** (0.971 Pearson correlation with content length — usable as a proxy when content is redacted)
- **Estimated thinking chars over time** (median per day/week)
- **Redaction rate** (% of blocks redacted per day)

### 1.2 Tool-usage / workflow metrics
- **Read:Edit ratio** (file reads per file edit): 6.6 → 2.0 during the regression
- **Research:Mutation ratio** (all read-type tools vs all write-type tools): 8.7 → 2.8
- **Read % / Edit % of all tool calls**
- **Write vs Edit share of mutations** (full-file rewrites vs surgical edits): 4.9% → 10–11%
- **Edits without a prior Read of the same file** (%, measured on recent tool history): 6.2% → 33.7%
- **Repeated edits to the same file in rapid succession** (thrash indicator)

### 1.3 Stop-hook violation metrics (programmatic)
Categories, each counted per day and per 1K tool calls:
- Ownership dodging ("not caused by my changes", "existing issue")
- Permission-seeking ("should I continue?", "want me to keep going?")
- Premature stopping ("good stopping point", "natural checkpoint")
- Known-limitation labeling ("known limitation", "future work")
- Session-length excuses ("continue in a new session", "getting long")

### 1.4 Linguistic quality signals (per 1K tool calls or per 1K words)
- **Reasoning loops**: "wait", "actually", "let me reconsider", "hmm, actually" — 8.2 → 26.6
- **"Simplest" mentions**: 2.7 → 6.3
- **Self-admitted quality failures**: "lazy and wrong", "rushed", "sloppy" — 0.1 → 0.5
- **Convention-violation markers**: abbreviated names, banned cleanup patterns, temporal phrases in code ("Phase 2")

### 1.5 User-sentiment / prompt-vocabulary metrics
- **User interrupts (Escape / "Request interrupted by user") per 1K tool calls**: 0.9 → 11.4
- **Frustration indicators** in user prompts (%): 5.8% → 9.8%
- **Positive:negative word ratio**: 4.4:1 → 3.0:1
- **Workflow-word frequency** (bead, commit, review, read, test) — proxy for how much of the workflow the human still trusts the agent with
- **Politeness drop** (please −49%, thanks −55%)

### 1.6 Session-shape metrics
- **Prompts per session**: 35.9 → 27.9 (shorter sessions = more abandonment)
- **Sessions with 5+ reasoning loops**
- **Ownership-dodging corrections per session**

### 1.7 Efficiency / cost metrics
- **API requests per user prompt** (work amplification factor)
- **Input / output / cache-read / cache-write tokens**
- **Cost per unit of useful work** (e.g., per merged LOC, per closed ticket)
- **Subagent request share** (% of requests spawned by parents)
- **Peak concurrency sustainable before quality collapse**
- **Variance by hour-of-day** (load-sensitivity of allocation)

---

## Part 2 — Which of these evaluate Skills, Hooks, and SubAgents

An extension's job is to either **raise the quality ceiling** (the agent does better work), **raise the quality floor** (it fails less catastrophically), or **reduce the cost** to reach a given quality. Every metric above is a candidate scoreboard dimension — but they map differently to each extension type.

### 2.1 Agent Skills
A skill is context injected on-demand. Its value is measured by whether the agent's **behavior on tasks matching the skill's trigger** is measurably better than without it.

| Metric | Why it applies to Skills |
|---|---|
| Read:Edit ratio | A good skill (e.g., your rf-mcp skills) should *raise* this on relevant tasks by directing the agent to inspect keyword docs/library source before editing. A drop means the skill is short-circuiting research. |
| Edits-without-prior-Read % | Should decrease on in-scope tasks. |
| Convention-violation rate | Skills that encode conventions should measurably reduce drift — this is the cleanest signal for documentation/SKILL.md-style skills. |
| Reasoning loops per 1K tool calls | A skill that narrows the action space should reduce "wait / actually" reversals because the agent spends fewer cycles rediscovering the approach. |
| "Simplest" rate | Should decrease if the skill provides the non-obvious-but-correct approach. |
| User interrupts per 1K tool calls | The cleanest end-user signal. Compare in-scope sessions with and without the skill loaded. |
| Task completion without escalation | Did the agent finish autonomously, or did it ask the human to disambiguate something the skill should have covered? |
| Token cost per completed task | Skills add context tokens. If quality doesn't improve proportionally, the skill is a net negative. |

**Not applicable**: thinking-depth metrics (not under skill control), time-of-day variance (infrastructure).

### 2.2 Hooks
Hooks are qualitatively different: they are **themselves measurement instruments**. The stop-phrase-guard.sh in the issue is literally a canary. Evaluating a hook means answering two questions:

1. **Is it firing on true positives?** (precision of the pattern match)
2. **Is the corrective injection changing downstream behavior in the desired direction?**

| Metric | Why it applies to Hooks |
|---|---|
| Hook fire rate over time | The primary signal. A hook that catches a named failure mode should see its fire rate *fall* after it starts injecting corrections — because the agent adapts within the session and the behavior stops recurring. A flat or rising rate means the hook is not teaching, only blocking. |
| Hook fire rate per category | Separates "ownership dodging" from "permission seeking" etc. so you can tune each pattern independently. |
| User interrupts per 1K tool calls, *with hook vs without* | If your hook is doing its job, human interrupt rate drops because the hook pre-empts the corrections. This is the ROI of the hook. |
| Post-hook task completion rate | Did forcing continuation actually produce useful work, or did the agent produce noise until it found another way to stop? |
| False-positive rate (hook fires on legitimate stops) | Measured by sampling + labeling. Too-aggressive hooks block legitimate checkpoints. |
| Token cost delta from forced continuation | A hook that forces 3× more turns to reach the same endpoint may not be worth it. |

**Not applicable**: most linguistic quality signals at the *global* level (hooks change them locally in-session, but they're not the right evaluation surface). Use hook-anchored windows instead: "in the 10 tool calls after a hook fires, what happened?"

### 2.3 SubAgents
SubAgents are parallel or delegated instances. Their job is to **reduce main-agent context bloat** while **producing a reliable summary**. The evaluation question is: did the delegation save context/time *without* losing fidelity?

| Metric | Why it applies to SubAgents |
|---|---|
| Research:Mutation ratio on the main agent | Well-designed research subagents should let the main agent *raise* this, because research is offloaded. |
| Main-agent context growth per task | Measured in tokens. A subagent that returns a 2K-token summary in place of 30K tokens of file reads is doing its job. |
| Subagent request share (%) | From Appendix D: 26% in the working multi-agent period. Track per workflow type. |
| Parent-to-child handoff accuracy | Did the subagent answer the question asked, or did the parent have to re-ask / re-do the work? Measurable as "tool calls by parent on the same topic after subagent return." |
| Interrupt rate on subagents | A subagent the human feels compelled to interrupt is failing the autonomy promise that justifies delegation. |
| End-to-end task success rate with vs without delegation | The ultimate A/B. |
| Token cost per delegated task | Subagents have startup overhead; for tiny tasks they're pure loss. |
| Concurrency sustainable before quality collapse | From Appendix D: the "5–10 concurrent agents" threshold. Measure per subagent type. |

---

## Part 3 — Solution proposal: a quality-evaluation framework for Claude Code extensions

The issue demonstrates that **session JSONL files plus hook logs contain enough signal to detect quality regressions statistically**. The same instrumentation works for evaluating your own extensions. Given your RF background, I'd structure this as a test harness rather than a dashboard — evaluation runs repeatably, produces structured output, and gates releases.

### 3.1 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Extension Eval Harness                     │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐     │
│  │ Task Bank    │   │ Runner       │   │ Analyzer     │     │
│  │ (scenarios)  │──▶│ (CC sessions)│──▶│ (JSONL+hooks)│     │
│  └──────────────┘   └──────────────┘   └──────────────┘     │
│         │                   │                   │           │
│         ▼                   ▼                   ▼           │
│   versioned YAML    ~/.claude/projects/   metrics.parquet   │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐     │
│  │ Baselines DB │◀──│ Diff Engine  │──▶│ Scorecard    │     │
│  │ (SQLite)     │   │ (stats tests)│   │ (HTML/JSON)  │     │
│  └──────────────┘   └──────────────┘   └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 The five-layer evaluation

**Layer 1 — Instrumentation.** Parse session JSONLs to extract the metrics from Part 1. This is a pure function over `~/.claude/projects/**/*.jsonl` plus your hook log files. The issue author's scripts are a starting point; generalize into a library (call it `cc-telemetry`) that emits a tidy dataframe: `(session_id, turn_idx, timestamp, metric_name, metric_value)`.

**Layer 2 — Task bank.** A versioned set of scenarios, each pinned to a project snapshot (git SHA) with a clear success criterion. Three tiers:

- **Narrow unit tasks** — one skill/hook/subagent is expected to trigger. ~5 min each. 20–50 of these.
- **Realistic engineering tasks** — 20–40 min autonomous runs with multi-file changes. 5–10 of these.
- **Adversarial tasks** — tasks designed to tempt the failure modes the extension is meant to prevent ("this should look simple but isn't").

The RF analogy is exact: these are your test suites, each suite gets a tag, and you run them with `--include skill:rf-mcp` etc.

**Layer 3 — A/B execution.** For each task, run N=5–10 sessions each in: `control` (extension disabled), `treatment` (extension enabled). Randomize order. Use different CC session IDs so there's no cross-contamination. This is where rf-mcp itself becomes useful — you can drive CC from RF, capture outputs, and assert against them.

**Layer 4 — Statistical comparison.** For each metric, compute:

- Median and IQR per arm
- Mann-Whitney U (non-parametric, metrics are non-normal)
- Effect size (Cliff's delta or rank-biserial)
- Bootstrap 95% CI on the treatment-minus-control difference

Gate on effect size, not just p-value. A statistically significant 3% improvement on Read:Edit ratio isn't worth shipping a skill for.

**Layer 5 — Scorecard.** Per extension, produce a signed scoreboard:

```
Skill: robotframework-keyword-research  v0.3.2
Task bank: rf-engineering-v2 (n=40 tasks, 10 runs each)

Quality metrics:
  Read:Edit ratio              6.1 → 8.4   Δ +2.3  [+1.5, +3.1]  ✓
  Edits w/o prior Read %       18%  → 7%   Δ -11pp [-15, -7]    ✓
  Convention violations/task   3.2  → 0.9  Δ -2.3  [-2.9, -1.7] ✓
  User interrupts / task       1.4  → 0.3  Δ -1.1  [-1.5, -0.7] ✓
  Reasoning loops / 1K calls   14.2 → 11.8 Δ -2.4  [-4.1, -0.7] ✓

Cost metrics:
  Context tokens / task        42K  → 51K  Δ +9K   (+21%)        ⚠
  Output tokens / task         18K  → 16K  Δ -2K   (-11%)        ✓
  Wall time / task             22m  → 18m  Δ -4m   (-18%)        ✓

Verdict: SHIP. Quality gains dominate; context cost acceptable.
```

### 3.3 Extension-type specializations

**For Skills** — also track *skill activation rate*: how often did the agent actually read the SKILL.md when it was in-scope? A skill that never triggers is invisible. Log via a wrapper around the view tool or via a trivial hook on SKILL.md reads.

**For Hooks** — track the **in-session decay curve**: within a single session, does the hook fire less as the session progresses? If yes, the hook is teaching. If no, it's only blocking. Also sample 10% of fires for manual precision labeling.

**For SubAgents** — track **delegation regret**: count of times the parent had to redo subagent work. Compute as tool calls by the parent on topics/files the subagent already covered, within N turns after return.

### 3.4 Continuous monitoring (the canary pattern)

The stop-hook violation rate in the issue was a leading indicator of the March 8 regression *before* user reports arrived. Apply the same principle to your extensions:

- Define 3–5 canary metrics per extension (e.g., for rf-mcp: keyword-lookup-without-execution rate, convention-violation-per-test rate, failed-library-import rate).
- Run the eval harness on a fixed weekly cadence against main-line Claude Code.
- Alert on >2σ movement from the 30-day rolling baseline.

This separates "the extension got worse" from "the underlying model got worse" — which, per issue #42796, is not a hypothetical concern.

### 3.5 Minimum viable version

If you want to start this week rather than next quarter:

1. Write a 200-line Python script that parses one project's JSONLs and emits the Part-1 metrics as CSV. (~1 day)
2. Pick one skill you've already shipped. Run 10 sessions on a fixed task, once with the skill disabled, once enabled. (~half day of CC time)
3. Eyeball the Read:Edit ratio, edits-without-read %, and user-interrupt count. If the signal is there with n=10, it'll be much clearer with n=100.
4. Iterate: add tasks to the bank, add metrics, add the stats layer.

The issue author did steps 1–3 post-hoc on production logs. You can do it prospectively and use it as a release gate.

---

## Appendix — Mapping to your current work

Your **rf-mcp** is a natural first subject: it's a subagent-like boundary (MCP tool calls delegate work to a real RF executor) *and* ships with agent skills. The evaluation question splits cleanly:

- Does the MCP layer reduce main-agent context bloat vs a code-generation-only approach? (Part 2.3 metrics)
- Do the `robotframework-agentskills` narrow the agent toward real-execution-first behavior? (Part 2.1 metrics, especially Read:Edit and "simplest" rate)
- Does your stop-hook equivalent catch the RF-specific failure mode where the agent writes but doesn't run? (Part 2.2 metrics)

This is also a RoboCon-worthy talk: "We measured whether our own skills actually help Claude, and here's what we found." The issue has already done the hard work of legitimizing session-log analysis as a method.
