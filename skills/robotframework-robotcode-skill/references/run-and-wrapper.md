# Running Tests: `robotcode robot`, Profiles and Wrappers

## Running

`robotcode robot` (alias `robotcode run`) runs `robot` with the `robot.toml` configuration. All normal `robot` options are passed through.

```bash
robotcode robot                                   # paths from robot.toml
robotcode robot tests/login.robot
robotcode robot -t "Valid Login" tests/           # one test
robotcode robot -i smoke -e wip                   # tag filters
robotcode robot -bl "Tests.Login.Valid Login"     # by long name (from discover)
robotcode -p headed robot -t "Valid Login"        # with a profile
robotcode robot -- --help                         # robot's own help
```

The exit code is Robot's: the number of failed tests (capped at 250), `0` when all passed, `251`–`255` for errors. See also `robotcode rebot …`, `robotcode libdoc …` and `robotcode testdoc …`, which pass options through the same way.

## Wrappers: run inside `xvfb-run` or a setup/teardown script

A wrapper is a command prefix. The actual robot run is appended to it. Use it for a virtual display or for services that must be started and stopped around the run.

```bash
robotcode --wrapper "xvfb-run -a" robot              # CLI flag (global option)
ROBOTCODE_WRAPPER="xvfb-run -a" robotcode robot      # env var
robotcode -p ci robot                                # profile with `wrapper = [...]`
robotcode -p ci --no-wrapper robot                   # switch a configured wrapper off for one run
robotcode -p headed --wrapper "xvfb-run -a" robot    # headed browser on a machine without a screen
```

In `robot.toml`:

```toml
[profiles.ci]
wrapper = ["xvfb-run", "-a"]

[profiles.integration]
wrapper = ["./scripts/with-test-services.sh"]
```

A wrapper script must run `"$@"` and pass the exit code through:

```bash
#!/usr/bin/env bash
set -u
./start-services.sh
trap './stop-services.sh' EXIT
"$@"
```

What uses the wrapper:

| Command | Wrapper applied? |
|---|---|
| `robot`, `robot-debug` | Yes |
| `repl` | Yes (environment variables set by the wrapper are visible as `%{VAR}`) |
| `discover`, `libdoc`, `results`, `analyze` | No: `[ WARN ] Ignoring --wrapper: 'discover' does not execute Robot Framework.` |

## Traps

- **`--dry` still runs the wrapper.** `robotcode --dry -p ci robot` prints the robot options but executes the wrapper script's setup and teardown (exit code 251). Don't use `--dry` with side-effect wrappers. *(Observed on 2.7.0.)*
- **A missing wrapper file exits with 1**, the same code as "1 test failed". Check the output for the error text, not only the exit code. *(Observed on 2.7.0.)*
- Put environment variables in the profile's `env` table, not in a wrapper. The profile's `env` is applied before the wrapper runs.
