# Tags and Selection

- [Setting tags](#setting-tags)
- [Reserved robot: tags](#reserved-robot-tags)
- [Tag matching and patterns](#tag-matching-and-patterns)
- [Selecting tests](#selecting-tests)
- [Skipping and re-running](#skipping-and-re-running)
- [Recipes](#recipes)

Commands below run from `assets/examples/` against its `tests/` tree (14 tests).

## Setting tags

- `Test Tags` in a suite file's Settings (or an `__init__.robot`) adds tags to every test below it (RF 6.0+).
- `[Tags]` in a test case adds tags to that test.
- `[Tags]    -smoke` removes a tag that `Test Tags` added, for that test only (RF 7.0+); `-` also takes patterns (`-sm*`).
- `Keyword Tags` (resource files) and `[Tags]` on keywords tag keywords, not tests.
- `Force Tags` and `Default Tags` are the legacy forms; the migration reference has the replacement.
- Tags are free text; keep a small vocabulary (`smoke`, `slow`, `api`, `wip`, an issue key) and follow the one `rf_conventions` reports in `tests.top_tags`.

```robotframework
*** Settings ***
Test Tags         users    smoke

*** Test Cases ***
Quick Check
    No Operation

Full Export
    [Tags]    -smoke    slow
    No Operation
```

## Reserved robot: tags

Tags starting with `robot:` are reserved. Use only these; any other `robot:` tag is flagged by robocop TAG03:

| Tag | Where | Effect |
|---|---|---|
| `robot:skip` | test | Skips the test |
| `robot:exclude` | test | Removes the test from the run |
| `robot:skip-on-failure` | test | A failure becomes a skip |
| `robot:continue-on-failure` | test or keyword | Continue after failures, also in nested keywords |
| `robot:recursive-continue-on-failure` | test or keyword | Same, recursively for all child keywords |
| `robot:stop-on-failure` | test or keyword | Stop at the first failure, also in templated tests |
| `robot:no-dry-run` | keyword | The keyword is not run in `--dryrun` |
| `robot:private` | keyword | The keyword is meant for its own file only (RF 6.0+) |
| `robot:flatten` | keyword | Its child keywords are flattened in the log |

## Tag matching and patterns

- Tags are normalized: case, spaces and underscores are ignored, so `Smoke`, `SMOKE` and `s_m o k e` are one tag.
- Patterns take `*` and `?` wildcards: `--include "req-*"`.
- Operators are upper case: `AND`, `OR`, `NOT`. Lower-case `and`/`or`/`not` are ordinary tag text, so `--include "smoke not slow"` matches no test.
- Quote patterns that contain spaces or wildcards so the shell passes them unchanged.
- `NOT` binds weakest: `"smoke AND api NOT slow"` means smoke and api, but not slow.
- Operators may be written without spaces (`smokeNOTslow`), but the spaced form is easier to read.

## Selecting tests

| Option | Selects |
|---|---|
| `--test NAME` / `-t` | Tests by name or full name; full names count from the root suite (RF 7.0+): `Tests.Api.Users.Create User` |
| `--suite NAME` / `-s` | Suites by name or full name; the parent init files still run |
| `--include PATTERN` / `-i` | Tests whose tags match the pattern |
| `--exclude PATTERN` / `-e` | Removes tests whose tags match |
| `--parseinclude GLOB` / `-I` | Parses only matching files (RF 6.1+); faster than `--suite` on big trees |

- A test name without dots matches in any suite: `--test "Create User"`.
- `*.Users.Create User` matches the test in any root suite; `Api.Users.Create User` matches nothing, because full names start at the root suite.
- `*` and `?` in test names act as wildcards here, so keep them out of names: `--test "Login ?"` would also select `Login A`.
- Several `--test`/`--include` options are combined with OR.

## Skipping and re-running

| Option | Effect |
|---|---|
| `--skip PATTERN` | Tests with matching tags are skipped (they appear in the report as SKIP) |
| `--skiponfailure PATTERN` | A failure of a test with a matching tag becomes a skip (`--skip-on-failure` is accepted too) |
| `--rerunfailed output.xml` | Runs only the tests that failed in that output; errors with "All tests passed" when nothing failed |
| `--rerunfailedsuites output.xml` | Re-runs whole suites that had failures |
| `--runemptysuite` | Does not fail when the selection is empty (useful in CI matrices) |

Re-run and merge:

```bash
uv run robot --outputdir results tests
uv run robot --outputdir results --rerunfailed results/output.xml --output rerun.xml tests
uv run rebot --outputdir results --merge results/output.xml results/rerun.xml
```

## Recipes

| Goal | Command | Tests in `assets/examples` |
|---|---|---|
| Smoke but not slow | `robot --include "smoke NOT slow" tests` | 2 |
| All smoke tests | `robot --include smoke tests` | 3 |
| Everything except slow | `robot --exclude slow tests` | 13 |
| One test by full name | `robot --test "Tests.Api.Users.Create User" tests` | 1 |
| One test by pattern | `robot --test "*.Users.Create User" tests` | 1 |
| One suite with its parent init files | `robot --suite users tests` | 3 |
| API suites by tag | `robot --include api tests` | 3 |
| Parse only the data-driven file | `robot --parseinclude "02__*.robot" tests` | 3 |
| Run all, skip slow | `robot --skip slow tests` | 14 |
