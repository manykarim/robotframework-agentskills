# Known Limitations and Traps

**Observed on robotcode 2.7.0** (Robot Framework 7.5, Python 3.13) in a set of 121 scripted experiments against Browser and RequestsLibrary suites, and rechecked where marked. Later robotcode versions may fix some of these. When the installed version is newer, check a trap again before working around it (`robotcode --version`).

"Library" in the Source column means the behaviour comes from the test library, not from robotcode.

| # | Area | Issue | Effect | Workaround | Source |
|---|---|---|---|---|---|
| 1 | REPL + Browser | The output directory (from `robot.toml` or `-d`) is not created | `New Browser` fails with `FileNotFoundError … playwright-log.txt`; following Browser keywords fail too and restart Playwright (112 s instead of 9 s in one run) | `mkdir -p <output-dir>` before starting the REPL, or pass an existing `-d`. Rechecked in this repo on 2.7.0. | robotcode |
| 2 | REPL `.save` | Lines that failed at run time are kept (`.help save` says they are skipped) | The saved suite fails | Save only clean sessions, or delete failing lines by hand. Rechecked in this repo on 2.7.0. | robotcode |
| 3 | Debugger | `.break "Name"` with quotes at `(rdb)` keeps the quotes as part of the name | The breakpoint never matches | `.break Keyword Name` without quotes. On the shell command line `--break "Name"` is fine. | robotcode |
| 4 | Debugger | Breakpoint conditions are evaluated at the call site; an unknown variable doesn't raise | The breakpoint stops at every hit | Use the caller's variables in conditions (`${index} == 2`, not the keyword's argument) | robotcode |
| 5 | Debugger | Running a keyword at a `--break-on-failed-test` stop | `IndexError: list index out of range` | Use the default exception stop (before the failure unwinds) | robotcode |
| 6 | REPL | Exit code is always 0; the `RobotCode REPL` test in `output.xml` is PASS even when a step failed | False "all good" signal | Read `[ FAIL ]` lines; use `robot` / `robot-debug` for pass/fail | robotcode |
| 7 | REPL | A bare `${var}` line is not echoed (`Keyword name cannot be empty.`); `[Tags]` lines are silently ignored | Confusing errors; the failed line also ends up in `.save` output | `Log To Console    ${var}`, `.vars` | robotcode |
| 8 | Wrapper | `--dry` still runs the wrapper; a missing wrapper file exits with 1 | Side effects during a "dry" run; a setup error looks like "1 test failed" | Don't use `--dry` with side-effect wrappers; check the output text, not only the exit code | robotcode |
| 9 | REPL + Requests | Credentials and tokens appear in plain text in INFO output | Secrets leak into shared logs | Don't share raw logs; lower the log level; use secret-handling keywords | Library |
| 10 | Debugger `.set` | Only works for existing scalar variables; the value is stored as a string | `Variable '${x}' not found`, or `'1000'` instead of `1000` | Assign at the prompt: `${x}=    Set Variable    ${1000}` | robotcode |
| 11 | Debugger `.source` | Not available for keywords defined in the suite file itself | "not found" | Use `.list` | robotcode (documented) |
| 12 | RequestsLibrary docs | `*args, **kwargs` signatures hide the real parameters | Signature-based tools and completion show nothing useful | Read the doc text: `robotcode libdoc RequestsLibrary show "POST On Session"` | Library |
| 13 | prompt-toolkit backend | Piped input under a PTY is taken as one pasted block | The REPL waits forever | `--plain`, a real pipe, or agent mode (`ROBOTCODE_FORCE_AI_AGENT=1`) | robotcode |
| 14 | Debugger | No graphical view (gutter breakpoints, variables pane) in the CLI | — | Use the RobotCode VS Code extension | robotcode (documented) |

Additional behaviour seen while writing this skill (2.7.0):

- `robotcode results diff` exits with 0 even with new failures. Gate on JSON: `jq -e '(.newFailures // []) | length == 0'`.
- `robotcode discover` / `robot` without path arguments and without `paths` in `robot.toml` fail with `Expected at least 1 argument, got 0.`
- `robotcode discover … --search` also matches keyword calls inside tests, not only test names.
- `robotcode analyze code` without paths analyzes the whole project root, even when run from a subfolder.
- **Windows, piped output:** text output that contains non-ASCII characters (`results` prints ❌/✅, some `--help` texts contain `→`) crashes with `UnicodeEncodeError: 'charmap' codec can't encode character` when stdout uses cp1252. Set `PYTHONUTF8=1` (or `PYTHONIOENCODING=utf-8`) in the environment, or use `--format json`. Seen in GitHub Actions Windows runners; reproduced with `PYTHONIOENCODING=cp1252`.
