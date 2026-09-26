# Static Analysis: `robotcode analyze code`

Analyzes `.robot` and `.resource` files **without running them**, using the same engine as the RobotCode language server. It resolves imports against the installed libraries, so it finds problems a linter can't see:

- keywords that don't exist (`KeywordNotFound`)
- undefined variables (`VariableNotFound`)
- wrong argument counts and other Robot data errors (`DataError`)
- libraries that fail to import (`DataError: Importing test library … failed: ModuleNotFoundError …`)
- optionally, unused keywords and variables (`KeywordNotUsed`, `VariableNotUsed`)

Use it after editing test data and before running. It is complementary to Robocop: Robocop checks style and structure, `analyze code` checks that names and arguments resolve.

All examples below were run against robotcode 2.7.0 / Robot Framework 7.5.

## Usage

```bash
robotcode analyze code                               # whole project: every file under the detected project root, even when run from a subfolder
robotcode analyze code tests/login.robot resources/  # specific files / folders
robotcode analyze code -f "**/*.resource"            # glob filter (repeatable)
robotcode analyze code -P libraries -V vars.yaml -v ENV:dev   # like robot's --pythonpath / --variablefile / --variable
```

```text
tests/bad.robot:3:5: [ERROR] KeywordNotFound: No keyword with name 'This Keyword Does Not Exist' found.
tests/bad.robot:6:14: [ERROR] VariableNotFound: Variable '${UNDEFINED_VAR}' not found.
tests/bad.robot:9:5: [ERROR] DataError: Keyword 'BuiltIn.Should Be Equal' expected 2 to 10 arguments, got 1.
Files: 1, Errors: 3, Warnings: 0, Infos: 0, Hints: 0 (in 0.03s)
```

Positions are `file:line:column`, 1-based. Run it from the project environment (`uv run robotcode …`). If a library isn't installed there, every keyword from it is reported as `KeywordNotFound`, so fix the environment before trusting the result.

## Exit code is a bitmask

| Bit | Meaning |
|---:|---|
| `0` | No issues |
| `1` | Errors |
| `2` | Warnings |
| `4` | Informations |
| `8` | Hints |

Examples: 2 errors + 1 warning → exit **3**; warnings only → exit **2**. In scripts, test the bit, not equality: `(( $? & 1 ))` means "there were errors".

`-xm, --exit-code-mask error|warn|info|hint|all` removes severities from the exit code (still reported). For example, `-xm warn` gives exit 0 when only warnings were found. `-xe` extends the mask set in the config file.

## Changing and filtering diagnostics

| Option | Effect |
|---|---|
| `-mi CODE` | Ignore a diagnostic code |
| `-me CODE` / `-mw CODE` / `-mI CODE` / `-mh CODE` | Re-classify as error / warning / information / hint |
| `--code CODE` | Only report these codes (without changing severity) |
| `--severity error,warn` | Only report these severities (others don't count for the exit code either) |
| `--collect-unused` | Also report `KeywordNotUsed` / `VariableNotUsed` (as warnings) |
| `--show-tracebacks` | Include full import tracebacks in text output |
| `--full-paths` | Absolute paths |
| `--load-library-timeout SECONDS` | For slow library imports (env `ROBOTCODE_LOAD_LIBRARY_TIMEOUT`) |

Inline suppression for one line:

```robotframework
    Keyword From Dynamic Library    arg    # robotcode: ignore[KeywordNotFound]
```

Project-wide in `robot.toml`:

```toml
[tool.robotcode-analyze.modifiers]
ignore = ["VariableNotFound"]      # e.g. variables injected at run time with -v
warning = ["KeywordNotFound"]

[tool.robotcode-analyze.code]
exit-code-mask = ["warn"]
```

Prefer narrow fixes (a variable file via `-V`, an inline ignore) over ignoring a whole code project-wide, because an ignored `KeywordNotFound` hides real typos.

## Output formats

```bash
robotcode --format json analyze code                                  # machine-readable
robotcode analyze code --output-format github                         # GitHub Actions annotations
robotcode analyze code --output-format sarif --output-file analyze.sarif   # code scanning upload
robotcode analyze code --output-format gitlab --output-file gl-code-quality.json
```

`--output-format` accepts `concise` (default), `json`, `json-indent`, `sarif`, `github`, `gitlab`.

JSON shape (LSP-style: `line`/`character` are **0-based**; `severity` 1 = error, 2 = warning, 3 = information, 4 = hint):

```json
{"diagnostics": {"tests/bad.robot": [
   {"range": {"start": {"line": 2, "character": 4}, "end": {"line": 2, "character": 31}},
    "message": "No keyword with name 'This Keyword Does Not Exist' found.",
    "severity": 1, "code": "KeywordNotFound", "source": "robotcode"}]},
 "summary": {"files": 1, "errors": 3, "warnings": 0, "infos": 0, "hints": 0}}
```

```bash
robotcode --format json analyze code | jq -r '.diagnostics | to_entries[] | .key as $f | .value[] | "\($f):\(.range.start.line+1): \(.code): \(.message)"'
```

## Cache

Analysis results and library docs are cached in `.robotcode_cache/<python>/<rf>/` in the project root. Add it to `.gitignore`.

```bash
robotcode analyze cache path | info | list | clear | prune
```

Clear the cache after upgrading a library if results look stale.
