# Discovery: `robotcode discover`

Reads the suites the way Robot Framework would (with `robot.toml`, profiles and filters) **without running anything**. Use it instead of grepping `.robot` files. Each call takes about 1–2 s.

## Subcommands

| Command | Lists |
|---|---|
| `robotcode discover all` | Suites, tests and tasks as a tree |
| `robotcode discover tests` | Tests (flat), with long name and `file:line` |
| `robotcode discover tasks` | RPA tasks |
| `robotcode discover suites` | Suites |
| `robotcode discover tags` | Tags (`--tests` also lists the tests per tag) |
| `robotcode discover files` | The files that take part in discovery |
| `robotcode discover info` | Python / RF / robotcode versions and executable |

Paths come from the arguments or from `paths` in `robot.toml`. With neither, the command fails with `Expected at least 1 argument, got 0.`

## Filters

`discover` accepts every `robot` selection option, plus its own:

```bash
robotcode discover tests --tags                              # show tags per test
robotcode discover tests --include apiANDsmoke               # robot tag patterns: AND, OR, NOT, globs
robotcode discover tests --include ui --exclude expected-fail
robotcode discover tests --test "*Login*"
robotcode discover tests --suite "Checkout"
robotcode discover tests -bl "Tests.Saucedemo Ui.Standard User Can Log In"   # by long name
robotcode discover tests -ebl "Tests.Wip*"                                   # exclude by long name
robotcode discover tests --search login                      # case-insensitive text search
robotcode discover tests --search-regex '(?i)(cart|checkout)'
robotcode -p regression discover tests                       # profile filters apply too
```

⚠️ `--search` also matches **keyword calls inside tests**, not only names. `--search login` returns a test named `Locked Out User Sees Error` if it calls `Login As`. This is useful for "which tests use keyword X?", but surprising if you expect a name match. Use `--test "*login*"` for name-only matching.

Text output looks like this:

```text
- **Tests.Booker Api.Ping Returns 201** (`tests/booker_api.robot:9`)
  - _Tags:_ `api`, `booker`, `smoke`
```

## JSON for tools

`--format` is a global option, so it goes before `discover`:

```bash
robotcode --format json discover tests --include smoke | jq -r '.items[].longname'
robotcode --format json discover tags | jq '.tags | map_values(length)'     # tests per tag
```

Each item in `.items` has `type`, `name`, `longname`, `source`, `relSource`, `lineno`, `range`, `rpa` and (with `--tags`) `tags`. Parse errors show up in the top-level `diagnostics` object, so check it before trusting an empty result.

## Typical uses

- **Before running:** find the exact long name, then `robotcode robot -bl "<longname>"`.
- **Sharding in CI:** split `.items[].longname` into groups and pass each group with repeated `-bl`.
- **Tag hygiene:** `discover tags` shows misspelled or one-off tags.
