---
name: rf-results
description: "Use first, before reading output.xml, to summarise, merge Robot Framework results. With robotcode installed, use rf-robotcode."
license: Apache-2.0
compatibility: Requires Python 3.8+ with robotframework>=7 (rebot / ExecutionResult) in the environment that runs the bundled script.
metadata:
  author: manykarim
  version: "2.0.0"
---

# Robot Framework Results

Use the bundled script to read Robot Framework `output.xml` and return JSON. It supports:
- summary totals
- detailed suite/test breakdowns
- tag statistics
- execution errors, failed test messages, and keyword-level errors
- timing (keyword timing is opt-in)
- single or multiple outputs (merge or combine with rebot)

> If `robotcode` is on PATH, `robotcode results summary|show|log|stats|diff` is usually quicker and uses the project's `robot.toml`. See `rf-robotcode`.

## When to use

Load this skill first, before reading or searching for output.xml yourself, when the user asks about the results of a Robot Framework run:

- why tests failed, pass/fail totals, failed suites, tag statistics, slowest tests, execution errors;
- a nightly or CI run to summarise, even if they only say "the robot run" or "the results" and never mention output.xml;
- merging pabot or rerun (`--rerunfailed`) outputs into one report with rebot.

Not this skill: prefer `rf-robotcode` (`robotcode results`) when the robotcode CLI is installed or named.

## Quick start

Run the bundled script through the project environment, so it parses `output.xml` with the Robot Framework version that wrote it. Script paths are relative to this skill's directory (the folder containing this SKILL.md), not to the project.

Single file summary:

```bash
uv run python scripts/rf_results.py --output output.xml --sections summary
```

Multiple outputs, merged (`--merge` replaces earlier results when tests overlap):

```bash
uv run python scripts/rf_results.py --outputs out1.xml out2.xml --merge --sections summary,details
```

Multiple outputs, combined under a new top-level suite (no `--merge`):

```bash
uv run python scripts/rf_results.py --outputs out1.xml out2.xml --name Combined --sections summary
```

Include keyword timing in timing output:

```bash
uv run python scripts/rf_results.py --output output.xml --sections timing --include-keyword-timing
```

Project not managed by uv (no `uv.lock`)? Run with the project's interpreter instead: `.venv/bin/python scripts/rf_results.py …` or `poetry run python scripts/rf_results.py …` (see rf-setup).

## Output sections

- `summary`: totals, suite/test counts, overall status
- `details`: suites, tests, failed tests, tag stats
- `errors`: execution errors, failed test messages, keyword errors
- `timing`: totals and slowest tests; keyword timing requires `--include-keyword-timing`

## Notes

- For multiple outputs, use `--merge` to mirror `rebot --merge` behavior. Without `--merge`, rebot combines outputs under a new top-level suite (name via `--name`).
- JSON output is written to stdout. Use `--pretty` for indented JSON, or `--json-out FILE` to write the full JSON to a file and print only `{written, bytes, mode}`. `--output` is always the input `output.xml`.
- `details` test entries (failed tests first) and each `errors` list are capped by `--limit` (default 50, `0` = unlimited); `details.omitted` / `errors.omitted` count what was left out.
- Exit codes: `0` ok, `2` usage, `3` Robot Framework missing or older than 7 in the interpreter, `4` `output.xml` missing or unparseable, `1` internal error (`--debug` for a traceback). Diagnostics are `error:`/`warning:`/`hint:` lines on stderr; stdout is empty on failure.
- Outside a project (e.g. a downloaded CI artifact), the script's inline metadata lets uv build a throwaway environment with only Robot Framework: `uv run --script scripts/rf_results.py --output ci/output.xml --sections summary`.

## Companion Skills

| Need | Skill |
|------|-------|
| Discover, run, debug and statically check with the robotcode CLI | `rf-robotcode` |
| Look up keyword names, arguments and docs | `rf-libdoc` (or `rf-robotcode`: `robotcode libdoc`) |
| Install Robot Framework or a library, fix the environment | `rf-setup` |
