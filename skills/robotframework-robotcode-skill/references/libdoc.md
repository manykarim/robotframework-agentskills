# Keyword Documentation: `robotcode libdoc`, REPL `.kw` / `.doc`

Look up keywords **before** writing a call. The docs match the **installed** library version and the project's own `.resource` files, because `robotcode libdoc` uses the project's Python path and variables from `robot.toml`.

## `robotcode libdoc`

`robotcode libdoc` passes its arguments to Robot's `libdoc`. The console subcommands `version`, `list` and `show` are the ones agents need:

```bash
robotcode libdoc Browser version                   # 20.5.0
robotcode libdoc Browser list                      # all keyword names (152 for Browser)
robotcode libdoc Browser list "Get*"               # glob filter (case-insensitive)
robotcode libdoc Browser list "*cookie*"
robotcode libdoc Browser show "Get Text"           # full docs for one keyword
robotcode libdoc RequestsLibrary show "POST On Session"
robotcode libdoc resources/booker.resource show    # all keywords of a resource file
robotcode libdoc resources/booker.resource show "Create Booking"
robotcode libdoc -- --help                         # libdoc's own help
```

About 1.8 s per call, even for Browser. `show` prints Markdown with arguments, types, defaults, return type, tags and docs:

```text
### Get Text
#### Arguments
* `selector` (type: `str`)
* `assertion_operator` (type: `AssertionOperator | None`, default: `None`)
* `assertion_expected` (type: `Any | None`, default: `None`)
...
#### Returns
* `str | list[str] | dict | tuple`
```

### JSON spec for tools

```bash
robotcode libdoc --format JSON RequestsLibrary results/RequestsLibrary.json
jq -r '.keywords[].name' results/RequestsLibrary.json
```

Useful for building a local keyword index or comparing library versions.

### Caveat: `*args, **kwargs` signatures (library behaviour)

All `* On Session` keywords in RequestsLibrary have the signature `*args | **kwargs`. The real parameters (`alias`, `url`, `json`, `params`, `expected_status`, …) are **only in the doc text**. Read the full `show` output. Don't infer arguments from the signature line alone. This is a property of the library, not of robotcode.

## Inside the REPL: `.imports`, `.kw`, `.doc`

When you are already exploring in the REPL (see `repl.md`), look things up in the same session:

```text
Import Library    Browser
Import Library    RequestsLibrary
Import Resource   resources/booker.resource
.imports                  # every library/resource with keyword count and file
.kw Get Text              # exact name → full documentation
.kw session               # not an exact name → search across all imports, grouped by library
.doc booker               # documentation of a library or resource
.exit
```

`.kw <text>` search output:

```text
# Keywords matching 'session'
## Browser (Library)
- SessionStorage Clear  ...
## RequestsLibrary (Library)
- Create Session  - DELETE On Session  - GET On Session  - POST On Session ...
## booker (Resource)
- Open Booker Session
```

This is the fastest way to answer "which keyword does Y?" across several libraries. A `.kw` lookup costs about 2 s including REPL start-up. `BuiltIn`, `Easter` and `robotcode.repl.Repl` are always loaded.

## Without robotcode

Use `rf-libdoc-search` (keyword search across libraries) and `rf-libdoc-explain` (detailed argument docs). They only need `robotframework`.
