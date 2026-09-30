# Stepwise Execution: `robotcode repl`

A prompt where each line is one Robot Framework step: a keyword call, an assignment or a block. State such as an open browser, an HTTP session or variables stays alive between lines. Alias: `robotcode shell`.

**When to use it:** exploring a page or an API **before** a test exists, trying locators, checking how a keyword behaves. For an existing failing test, use `robot-debug` instead (`debug.md`).

## Always non-interactive for agents

```bash
mkdir -p results/repl                                                # the REPL does not create it
robotcode repl --plain --no-history -d results/repl < steps.robotrepl
printf 'Log To Console    hello\n.exit\n' | robotcode repl --plain --no-history
robotcode repl --plain steps.robotrepl                               # file as argument
robotcode repl --plain --no-history -d results/repl <<'EOF'
Import Library    RequestsLibrary
Create Session    api    https://restful-booker.herokuapp.com
${resp}=    GET On Session    api    /ping    expected_status=201
Log To Console    ${resp.status_code}
.exit
EOF
```

- `--plain` (= `--backend plain`) reads line by line. It is selected automatically for a pipe and in detected agent terminals. Pass it anyway.
- End input with `.exit`. `--no-history` keeps agent sessions out of the user's REPL history.
- Lines starting with `#` are comments.
- Example scripts: `assets/examples/explore-api.robotrepl`, `assets/examples/explore-browser.robotrepl`.

## Options

| Option | Use |
|---|---|
| `-v NAME:value`, `-V vars.yaml` | Variables and variable files (as for `robot`). `[variables]` from `robot.toml` are loaded too. |
| `-P, --pythonpath PATH` | Extra library search path |
| `-d DIR`, `-o output.xml`, `-l log.html`, `-r report.html`, `-x xunit.xml` | Write result files. All lines become one test named `RobotCode REPL`. |
| `-k, --show-keywords` | Print the full keyword name before each call (`KEYWORD BuiltIn.Set Variable  42`), useful for ambiguous names |
| `-i, --inspect` | Run the given script files, then keep reading more lines from stdin with the session still alive |
| `-s, --source FILE` | Resolve relative imports from FILE's directory |
| `--plain`, `--no-history` | See above |

With a profile: `robotcode -p headed repl --plain …`.

## What works in the REPL

```text
Import Library    Browser    timeout=15s
New Browser    chromium    headless=${HEADLESS}
New Page    https://www.saucedemo.com
${title}=    Get Title
Log To Console    last return value is ${_}          # ${_} holds the last return value
FOR    ${i}    IN RANGE    3
    Log To Console    item ${i}
END
IF    ${price} > 100
    Log To Console    expensive
ELSE
    Log To Console    cheap
END
TRY
    GET On Session    api    /missing
EXCEPT    *404*    type=GLOB    AS    ${err}
    Log To Console    caught: ${err}
END
VAR    ${greeting}    hello from VAR
```

- A failing keyword prints `[ FAIL ] …` and the session **goes on**.
- A failure caught by `TRY/EXCEPT` is still printed as `[ FAIL ]` before the `EXCEPT` branch runs. That is correct, not a second error.
- `*** Settings ***`-style lines such as `[Tags]    smoke` are **silently ignored**.
- A bare `${_}` line is not echoed; it fails with `Keyword name cannot be empty.` Use `Log To Console    ${_}` or `.vars`.

## Dot-commands

| Command | Use |
|---|---|
| `.help [cmd]` | List dot-commands / details for one |
| `.imports` | Loaded libraries and resources with keyword counts |
| `.kw [name-or-text]` | Keyword docs, or a search across imports (see `libdoc.md`) |
| `.doc <name>` | Library / resource documentation |
| `.vars [--user]` (`.v`) | Variables in scope. `--user` skips most Robot internals but still lists `${/}`, `${True}`, `${None}`. |
| `.save [-a] [-t "Test Name"] FILE` | Save the session as a `.robot` file. `-a` appends. |
| `.cwd`, `.clear` | Working directory / clear screen |
| `.exit` (`.quit`) | End the session |

The debugger dot-commands (`.break`, `.where`, …) exist too; see `debug.md`.

## Turning an exploration into a test: `.save`

```text
.save -t "Saved Browser Login" tests/saved_login.robot
```

Result: imports go into `*** Settings ***` and every executed line goes into one test case. Then `robotcode robot tests/saved_login.robot`.

- ⚠️ **Lines that failed are kept** (observed on 2.7.0, although `.help save` says they are skipped). The saved suite then fails. Save only after a clean session, or delete the failing lines by hand.
- Multi-word test names must be quoted: `.save -t "Two Words" file.robot`. Without quotes you get a usage error.

## Traps

- **Create the output directory first** (`mkdir -p`). The REPL uses `-d` or `output-dir` from `robot.toml` but does not create it. Browser writes `playwright-log.txt` there, so `New Browser` fails with `FileNotFoundError`. In one run, every following Browser keyword also failed and restarted Playwright (112 s instead of 9 s).
- **The exit code is always 0**, even when steps failed, and the `RobotCode REPL` test in `output.xml` is PASS. Read the `[ FAIL ]` lines in the output. Use `robot` / `robot-debug` when you need pass/fail.
- **Secrets in the output.** RequestsLibrary logs full request and response bodies at INFO level, so passwords and tokens appear in plain text (`&{creds} = { username=admin | password=password123 }`). Don't paste raw REPL output into reports, commits or issues. Lower the log level or avoid logging credential variables.
- **Output is verbose** for HTTP libraries (headers, bodies, warnings). Use `Log To Console` for the values you want to see, and read those lines.
