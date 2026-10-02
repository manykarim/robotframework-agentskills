# Trigger query sets

One file per shipped skill: `eval/triggers/<skill-name>.yaml`. A set measures
whether the skill's frontmatter `description` makes an agent load the skill
for the right requests — and only for those. Task outcomes (does the skill
*help*?) are measured separately by the task bank in `eval/tasks/`.

## Format

```yaml
skill: rf-browser                    # a shipped skill name (skills/*/SKILL.md `name`)
model: claude-haiku-4-5-20251001     # Haiku or Sonnet only (Opus: run-time opt-in)
runs: 3                              # sessions per query
threshold: 0.5                       # triggered when loads / runs >= threshold
queries:
  - {id: br-t01, split: train, should_trigger: true, query: "..."}
  - {id: br-n01, split: validation, should_trigger: false, note: sibling rf-selenium, query: "..."}
```

Loader rules (enforced by `rf-skill-eval coverage` / `trigger` and by
`tests/eval/test_trigger_sets.py`):

- at least **8 should-trigger** and **8 should-not-trigger** queries;
- every query has a `split` (`train`, `validation`, `holdout` or
  `holdout<N>` such as `holdout2`; regex `^holdout\d*$`), and both
  polarities appear in `train` and `validation` (aim for ~60/40
  train/validation per polarity; retired holdout queries are outside that
  ratio);
- holdout splits are optional and do not count toward the minimum of 8: they
  hold queries written *after* the last description change and are never used
  to choose or accept a description (`trigger --split holdout2` runs only
  those; the report adds one column group per holdout split that ran, after
  train and validation: Holdout, Holdout2, ...);
- **retiring a holdout:** once a holdout split's results have been inspected
  to diagnose failures it is no longer unseen. Move its queries to `train`
  (keep the ids, add `retired holdout (<date> evidence)` to the note) and add
  a new numbered holdout with fresh queries. The first holdout was retired
  this way on 2026-09-30; the current one is `holdout2`;
- `skill` names a shipped skill and the file is named `<skill>.yaml`;
- query ids are unique within the set.

Content rules (from `sharpen-skill-descriptions`): should-trigger queries are
phrased as users write them — including at least two indirect ones (pasted
error, file name, intent only) and one edit to an existing file. Should-not-
trigger queries are *near misses*: at least 3 from the skill's boundary
siblings (Browser ↔ SeleniumLibrary, RequestsLibrary ↔ RESTinstance,
results/libdoc ↔ robotcode, setup ↔ library skills) and at least 2 non-Robot-
Framework look-alikes. A query that plausibly belongs to two siblings is never
used as a should-not-trigger query for either.

## How a set is run

`rf-skill-eval trigger --skills rf-browser --split validation --max-cost-usd 2`
runs every selected query `runs` times with `claude -p`, the plugin staged but
**hooks disabled** (the UserPromptSubmit hook would measure itself, not the
description), `--max-turns 3`, and only the tools `Skill,Read,Glob,Grep`
available (`--tools`, so `Bash`/`Write`/`Edit` do not exist in the session).
Each session starts in a fresh copy of `eval/fixtures/sut-trigger/` — a small
Robot Framework project (`pyproject.toml`, `tests/smoke.robot`,
`resources/common.resource`) that imports no test library, so the query alone
decides which skill fits. A run *loads* the skill when the transcript has a
`Skill` call naming it (with or without the `rf-agentskills:` prefix) or a
`Read` of its `SKILL.md`. The report gives TP/FP/TN/FN, precision, recall and
accuracy per skill for **train, validation (and each holdout split) separately**, and
lists which other skills were loaded for failing queries.

- **Resume:** each finished query is appended to `<output>/outcomes.jsonl`;
  re-running with the same `--output` skips queries already recorded (keyed by
  variant id, model, listing budget, skill, query id, split) and re-runs
  incomplete ones.
- **Listing budget:** Claude Code shows a skill's description only while it
  fits a character budget (about 8000 for 200k-context models such as Haiku;
  bundled skills first, then the others alphabetically, the rest by name
  only). `--listing-budget <chars>` sets `SLASH_COMMAND_TOOL_CHAR_BUDGET` for
  the sessions (for example `40000`, what a 1M-context model gets); without it
  the default applies. Results then go to `trigger-results-budget-<N>.json`.
- **Visibility:** every run's `skill_listing` attachment (in its
  `session.jsonl`) is parsed; each outcome records, per run, which rf-*
  descriptions were shown, and the report's "Description visibility" table
  counts per skill the sessions that saw its description.
- **Concurrency:** `--concurrency 2` runs two queries at once (default 1, max 2).
- **Variants:** `scripts/build-description-variant.py --candidates <yaml> --out <dir>`
  copies the plugin with candidate descriptions, byte-exact (runs of spaces as
  in `Library    Browser` are kept); `trigger --variant-root <dir>` measures it
  without touching `skills/`. See `docs/ci/usage.md`.
- **No repository snapshot:** trigger sessions have no write-capable tool, so
  the runner skips the before/after repository integrity check for them.

## Train / validation discipline

- Tune descriptions against the **train** split only.
- **Never edit validation queries to make a description pass.** A failing
  validation query is a finding, not a typo.
- Rotate validation queries only when the skill's *intent* changes (a new
  sibling, a merged or retired skill), and record the rotation in the PR.
- The stored result lives in `eval/baselines/triggers.json`; the PR gate fails
  when validation accuracy drops by more than one query's worth.

## Adding a skill

A new skill under `skills/` needs a set here (and a narrow task in
`eval/tasks/narrow/`) or `rf-skill-eval coverage` fails and names it.
