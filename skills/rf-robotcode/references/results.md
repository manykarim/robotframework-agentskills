# Result Analysis: `robotcode results`

Reads a finished `output.xml` or `output.json` (Robot 7) and prints summaries, test lists, execution trees, statistics and differences between two runs, as text (Markdown-like), JSON or TOML. Use it after every run, in CI, or when you get someone else's `output.xml`, instead of opening `log.html` or parsing XML by hand.

## Which output file?

- `-o, --output PATH` selects the file explicitly.
- Without `-o`, robotcode looks **only** in the active profile's `output-dir` and in the project root. It does not search other folders for the newest file. If nothing is found, it stops with a message that lists the searched paths.
- So `robotcode -p ci results summary` reads the `ci` profile's output directory.

## Subcommands

### `summary`: headline counts

```bash
robotcode results summary                       # status, counts, elapsed
robotcode results summary --failed              # plus each failure with message and file:line
robotcode --format json results summary | jq -r '"\(.status): \(.counts.passed)/\(.counts.total) passed"'
```

```text
- _Status:_ ❌ **FAIL**
- _Total:_ 1
...
## Failures (1)
- ❌ **FAIL** Debug Target.Sum Prices (`tests/debug_target.robot:9`)
  > Total is 60, expected 100: 60 != 100
```

JSON keys: `status`, `counts` (`total`, `passed`, `failed`, `skipped`, `notRun`), `elapsedSeconds`, `startTime`, `endTime`, `messagesCount`.

### `show`: list tests

```bash
robotcode results show --failed --message-chars 0         # failing tests with full messages
robotcode results show --sort elapsed --top 10            # slowest first
robotcode results show --sort elapsed --reverse --top 10  # fastest first
robotcode results show --search Kitchen                   # tests whose data contains the text
robotcode results show --tags --timing
```

`--sort` accepts `name`, `suite`, `status` (FAIL → SKIP → PASS → NOT RUN), `elapsed`, `start`.

### `log`: execution tree

```bash
robotcode results log --failed                          # keyword → sub-keyword → message trees
robotcode results log --failed --max-depth 2            # fold deep levels
robotcode results log -t "Checkout*" --keyword-info     # add each keyword's [Documentation]
robotcode results log --failed --level warn             # only messages at WARN and above
robotcode results log --failed --extract ./extracted    # copy/decode screenshots and other artifacts
```

`--extract DIR` writes, for example, `extracted/Tests.Saucedemo_Ui.Problem_User_Sorts_By_Price/fail-screenshot-1.png`. In JSON output the file is listed under `artifacts` with `resolvedPath` and `extractedTo`.

⚠️ Browser takes an automatic screenshot only when a **Browser keyword** fails. If the failing check is BuiltIn `Should Be Equal`, there is nothing to extract. Use a Browser assertion (`Get Text    h1    ==    Welcome`) for checks where a screenshot matters.

### `stats`: aggregate

```bash
robotcode results stats --by tag
robotcode results stats --by suite --sort elapsed
robotcode results stats --by status
```

| Name | Total | Pass | Fail | Skip | Elapsed |
|---|---:|---:|---:|---:|---:|
| api | 18 | 16 | 2 | 0 | 2.70 s |
| ui | 9 | 7 | 1 | 1 | 18.47 s |

### `diff`: compare two runs

```bash
robotcode results diff baseline/output.xml latest/output.xml
robotcode results diff base.xml new.xml --only new-failures      # also: new-passes, status-changes, added, removed
```

```text
## New failures (1)
- Tests.Debug Target.Injected Failure Toggle (`tests/debug_target.robot:31`) — PASS → FAIL
  > Injected failure for results diff: Furniture != Kitchen
```

⚠️ `diff` **exits with 0 even when there are new failures**. For a CI gate, use JSON and jq:

```bash
robotcode --format json results diff base.xml new.xml | jq -e '(.newFailures // []) | length == 0'
# exit 0 = no new failures, exit 1 = regression
```

## Filters (all subcommands)

`--status pass|fail|skip|not-run`, `--failed`/`--passed`/`--skipped` (not on `summary`/`diff`), `-i`/`-e` tag patterns, `-s` suite, `-t` test (glob), `-bl`/`-ebl` long names, `--search`, `--search-regex`.

## Exit codes

`results` commands exit with 0 when they could read the file, whatever the test outcome. A missing file exits with 2 (`Error: Result file not found: …`). Use the JSON `status` field, or `robotcode robot`'s own exit code, for pass/fail.

## Without robotcode

Use `rf-results` (bundled script, needs only `robotframework`). It also merges multiple outputs via rebot. With robotcode, `robotcode rebot --merge a.xml b.xml` does the merge.
