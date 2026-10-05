---
name: rf-robotcode
description: "Use first for the robotcode CLI and robot.toml in RF: profiles, discover, debug. Not VS Code extension."
license: Apache-2.0
compatibility: Requires Python 3.10+ and robotcode[all] 2.x installed in the project environment next to robotframework>=7.
metadata:
  author: manykarim
  version: "2.0.0"
---

# robotcode CLI Skill

## When to use

Load this skill first, before reading robot.toml or exploring the tests, when a Robot Framework project uses the robotcode CLI or a robot.toml:

- run suites with robot.toml profiles, discover tests and tags without running them;
- debug a failing test step by step with robot-debug, or try keywords in a non-interactive REPL;
- keyword docs (`robotcode libdoc`), result summaries, failures and diffs of output.xml (`robotcode results`), static checks (`robotcode analyze code`).

Not this skill: settings of the RobotCode VS Code extension. Without robotcode, use `rf-results` for output.xml and `rf-libdoc` for keyword docs.

## Quick Reference

`robotcode` is the CLI of the RobotCode project (the same engine as the VS Code extension). It wraps `robot`, `libdoc`, `rebot` and `testdoc` with the project's `robot.toml` configuration, and adds discovery, a REPL, a CLI debugger, result analysis and static analysis. Every command reads the same `robot.toml` and profiles.

Verified against **robotcode 2.7.0**, Robot Framework 7.5.

## Is robotcode available?

Check once per session, from the project root:

```bash
robotcode --version          # or, in a uv project: uv run robotcode --version
robotcode discover info      # which Python / RF / robotcode will actually be used
```

- **Available** → use the commands below.
- **Not installed** → use the script-based skills instead (see Companion Skills), or, if the user agrees, install it into the project environment: `uv add --dev "robotcode[all]"` (or `pip install "robotcode[all]"` in the active venv).
- Run robotcode from the **project's** environment (`uv run robotcode …` or the activated venv). A global install sees the wrong library versions.

## ⚠️ Agent safety rule: never run the REPL or debugger interactively

`robotcode repl` and `robotcode robot-debug` are interactive. In scripts and agent terminals:

- **Pipe the input in** (`printf '…' | robotcode repl` or `robotcode repl < steps.robotrepl`), or pass **`--plain`**.
- **End piped REPL input with `.exit`.**
- In a real terminal (PTY) without agent detection, piped lines become one pasted block and the REPL **hangs**. robotcode detects agent terminals (`CLAUDECODE`, `AI_AGENT`, …) and switches to the plain backend. `ROBOTCODE_FORCE_AI_AGENT=1` forces this on. See `references/agent-mode.md`.
- If stdin ends (EOF) while the debugger is paused, the run resumes and finishes. It does not hang.

## Which command for which question

| Question | Command | Details |
|---|---|---|
| Which tests / suites / tags exist? | `robotcode discover tests --tags` · `discover tags` · `discover all` | `references/discover.md` |
| How do I call keyword X? | `robotcode libdoc <Lib> show "<Keyword>"` | `references/libdoc.md` |
| Which keyword does Y? | `robotcode libdoc <Lib> list "*text*"`, or REPL `.kw <text>` | `references/libdoc.md` |
| Does this locator / request work? | `robotcode repl` (piped), line by line | `references/repl.md` |
| Why does this test fail? | `robotcode robot-debug -t "<Test>" <suite>` (stops at the failure) | `references/debug.md` |
| What failed in that run? | `robotcode results summary --failed` · `results log --failed` | `references/results.md` |
| What changed since the last run? | `robotcode results diff old.xml new.xml` | `references/results.md` |
| Do the files have errors (missing keywords, variables, arguments)? | `robotcode analyze code [paths]` | `references/analyze.md` |
| Run tests with a profile / display / services | `robotcode -p <profile> [--wrapper "xvfb-run -a"] robot …` | `references/run-and-wrapper.md` |
| What configuration is in effect? | `robotcode config show` · `robotcode profiles list` | `references/setup-and-config.md` |
| A trap or surprising result | — | `references/gotchas.md` |

## Recommended agent workflow

```text
1. robotcode discover info                            # right interpreter and versions?
2. robotcode --format json discover tests -i <tag>    # find the test(s); don't grep .robot files
3. robotcode libdoc <Library> show "<Keyword>"        # check signatures before writing calls
4. robotcode analyze code <changed files>             # static check after editing
5. robotcode robot -t "<Test>" <suite>                # run
6. robotcode --format json results summary --failed   # what failed? (don't parse output.xml by hand)
7. printf '.where\n.vars\n<checks>\n.c\n' | robotcode robot-debug --plain -t "<Test>" <suite>
8. robotcode repl (piped) only to explore where no test exists yet (locators, API calls)
9. robotcode results diff before.xml after.xml        # confirm the fix, no new failures
```

## Top traps (observed on robotcode 2.7.0)

1. **The REPL does not create its output directory.** Browser then fails with `FileNotFoundError … playwright-log.txt`. Run `mkdir -p <output-dir>` first, or pass an existing `-d`.
2. **`.save` keeps lines that failed**, so the saved `.robot` file fails too. Save only clean sessions, or delete the failing lines afterwards.
3. **At the `(rdb)` prompt, `.break "Keyword Name"` with quotes never matches.** Write `.break Keyword Name` without quotes. (On the shell command line `--break "Keyword Name"` is fine, because the shell strips the quotes.)
4. **The REPL exit code is always 0**, and a REPL `output.xml` marks its test PASS even when a step failed. Use `robot` / `robot-debug` for pass/fail.

All 14 known limitations with workarounds: `references/gotchas.md`.

## Cheat sheet

| Task | Command |
|---|---|
| Versions and interpreter | `robotcode discover info` |
| Tests with tags, filtered | `robotcode discover tests --tags -i apiANDsmoke` |
| Test long names as JSON | `robotcode --format json discover tests \| jq -r '.items[].longname'` |
| Keyword list / details | `robotcode libdoc Browser list "Get*"` / `robotcode libdoc Browser show "Get Text"` |
| Resource file docs | `robotcode libdoc path/to/file.resource show` |
| Static analysis for CI | `robotcode analyze code --output-format github` |
| Scripted REPL | `robotcode repl --plain --no-history -d results/repl < steps.robotrepl` |
| Debug at failure | `robotcode robot-debug -t "<Test>" <suite>` |
| Debug at keyword / line | `robotcode robot-debug --break "Keyword" --break file.robot:42 <suite>` |
| Run summary | `robotcode results summary --failed [-o output.xml]` |
| Slowest tests | `robotcode results show --sort elapsed --top 10` |
| Failure tree + screenshots | `robotcode results log --failed --extract ./extracted` |
| Stats by tag | `robotcode results stats --by tag` |
| Regression gate | `robotcode --format json results diff base.xml new.xml \| jq -e '(.newFailures // []) \| length == 0'` |
| Headed run in CI | `robotcode -p headed --wrapper "xvfb-run -a" robot` |

Global options (`-p/--profile`, `-f/--format`, `--wrapper`, `-d/--dry`, `-r/--root`) go **before** the subcommand: `robotcode -p ci --format json results summary`.

Out of scope for agents: `robotcode debug`, `repl-server` and `language-server` are for IDEs.

## When to Load Additional References

| Need | Reference File |
|------|----------------|
| Installing robotcode, `robot.toml`, profiles, `config` / `profiles` commands | `references/setup-and-config.md` |
| Discovering tests, suites, tags, files; filters; JSON | `references/discover.md` |
| Running tests, profiles, `--wrapper`, `xvfb-run` | `references/run-and-wrapper.md` |
| Keyword signatures and docs (`libdoc`, REPL `.kw` / `.doc`) | `references/libdoc.md` |
| Stepwise execution, `.save`, REPL output files | `references/repl.md` |
| Breakpoints, stepping, inspecting at a failure, logpoints | `references/debug.md` |
| Summaries, failure trees, stats, diffs, screenshot extraction | `references/results.md` |
| Static analysis, exit codes, CI formats (SARIF / GitHub / GitLab) | `references/analyze.md` |
| Agent detection, pipe vs PTY, secrets in output | `references/agent-mode.md` |
| All known limitations with workarounds | `references/gotchas.md` |

Examples in `assets/examples/`: `robot.toml` (profiles), `explore-api.robotrepl`, `explore-browser.robotrepl`, `debug_target.robot` + `debug-at-failure.rdb`.

## Companion Skills

robotcode is preferred when it is installed. Without it, use the script-based skills:

| Need | With robotcode | Without robotcode |
|------|----------------|-------------------|
| Analyze output.xml results | `robotcode results …` | `rf-results` |
| Look up keyword names, arguments and docs | `robotcode libdoc <Lib> list`, `robotcode libdoc <Lib> show "<Kw>"`, REPL `.kw` | `rf-libdoc` |
| Install Robot Framework or a library, fix the environment | `rf-setup` | `rf-setup` |
| Web UI tests with Browser Library (Playwright) | — | `rf-browser` |
| API tests with RequestsLibrary | — | `rf-requests` |
| Write tests, suites, user keywords, resources and variables in Robot Framework syntax | `robotcode analyze code` after writing | `rf-language` |
