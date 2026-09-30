# Resources and Variable Files

- [Default layout](#default-layout)
- [Resource files](#resource-files)
- [Imports and paths](#imports-and-paths)
- [Variable files per environment](#variable-files-per-environment)
- [Keyword name conflicts](#keyword-name-conflicts)
- [Private keywords and library aliases](#private-keywords-and-library-aliases)

## Default layout

Follow the layout `rf_conventions` reports (`layout.resource_dir`, `layout.variable_files`). When the project has none yet:

```text
resources/
  common.resource         # Library imports and settings shared by all resources
  login.resource          # one <domain>.resource per domain; imports common.resource
  cart.resource
variables/
  dev.yaml                # one variable file per environment
  staging.yaml
libraries/                # project Python keyword libraries (on the python-path)
tests/
```

- `resource_dir` is the directory with the most `.resource` files, else the first of `resources/`, `keywords/`, `res/` that exists, else create `resources/`.
- Each suite imports the domain resources it needs; the domain resources import `common.resource`.
- Never overwrite an existing resource or variable file unless asked; add keywords to the matching domain file or create a new one.

## Resource files

- Extension `.resource`. Settings may contain only imports (`Library`, `Resource`, `Variables`), `Documentation` and `Keyword Tags`; anything else ("Setting 'Test Setup' is not allowed in resource file") is ignored with an error.
- No `*** Test Cases ***` section: a resource with tests fails to import.
- `*** Variables ***` and `*** Keywords ***` are allowed.

```robotframework
*** Settings ***
Documentation     Cart keywords. Imports what the keywords need, nothing else.
Library           Collections
Keyword Tags      cart

*** Variables ***
${MAX_ITEMS}      10

*** Keywords ***
Cart Should Not Be Full
    [Documentation]    Fails when ``cart`` holds ``${MAX_ITEMS}`` items or more.
    [Arguments]    ${cart}
    ${size}=    Get Length    ${cart}
    Should Be True    ${size} < ${MAX_ITEMS}
```

## Imports and paths

- A relative path in `Resource`, `Variables` or `Library` resolves against the directory of the importing file first, then against the python-path (`--pythonpath`, `python-path` in `robot.toml`).
- Use paths relative to the importing file (`../resources/cart.resource`) or `${CURDIR}/…`; avoid paths that depend on the current working directory.
- Use `/` as the separator on every OS.
- An import that fails is reported as an error and the suite still runs, so dry-run after changing imports.

## Variable files per environment

| Kind | Needs | Notes |
|---|---|---|
| YAML (`.yaml`/`.yml`) | PyYAML in the project environment: `uv add pyyaml` (not using uv: add `pyyaml` with the project's tool, see rf-setup) | Top level is a mapping; takes no arguments (robocop ERR04) |
| JSON (`.json`) | Nothing extra (RF 6.1+) | Top level is an object |
| Python (`.py`) | Nothing extra | Module attributes, or `get_variables(env)` that returns a dict; takes arguments |
| Resource (`.resource`) | Nothing extra | `*** Variables ***` section, imported with `Resource` |

Select the environment on the command line; plain `robot` does not read `robot.toml`:

```bash
uv run robot --variablefile variables/staging.yaml tests
uv run robot --variablefile variables/common.py --variablefile variables/dev.yaml tests
```

With robotcode, a `robot.toml` profile can hold the list: `[profiles.staging]` with `variable-files = ["variables/staging.yaml"]`, run as `robotcode -p staging robot`.

- The suite keeps dev defaults in its own `*** Variables ***` section; `--variablefile` overrides them.
- Python variable files: names starting with `_` are skipped; `__all__` limits what is exported; `LIST__name` and `DICT__name` create `@{name}` and `&{name}`; `get_variables(env="dev")` receives arguments given as `common.py:staging`.
- A missing PyYAML fails with "Using YAML variable files requires PyYAML module to be installed".

## Keyword name conflicts

The same keyword name in two imported resource files fails at the call with "Multiple keywords with name 'Open App' found". Resolve it by:
- calling the keyword by its full name, `<resource file name>.<Keyword>` (`admin.Open App`), or `<Library>.<Keyword>` for library keywords;
- `Set Library Search Order    admin` in a setup, which also works for resource file names;
- renaming one keyword, which is usually the best fix.

```robotframework
*** Settings ***
Resource          ../resources/calc.resource

*** Test Cases ***
Qualified Calls
    calc.The Calculator Is Cleared
    BuiltIn.Log    fully qualified library keyword
```

- The qualified form breaks when two resources share a file name in different directories; rename one of them.
- A keyword defined in the suite file itself wins over imported ones, which can hide a conflict until another suite imports both resources.
- Robocop KW06 (`ambiguous-keyword-name`, robocop 9.x, disabled by default) finds such conflicts statically: `uv run robocop check --no-cache -s KW06 tests resources`.

## Private keywords and library aliases

- Tag helper keywords `robot:private` (RF 6.0+) so they are meant only for the file that defines them; a call from another file logs a warning ("is private and should only be called by keywords in the same file"). `Keyword Tags    robot:private` is too broad; tag individual keywords.
- Import a library twice with different arguments, or give it a short name, with `AS`: `Library    Collections    AS    Coll`, then call `Coll.Append To List`. `WITH NAME` is legacy (robocop DEPR03).

```robotframework
*** Settings ***
Library           Collections    AS    Coll

*** Test Cases ***
Alias And Private Helper
    VAR    @{items}    a
    Coll.Append To List    ${items}    b
    Public Step    ${items}

*** Keywords ***
Public Step
    [Arguments]    ${items}
    Count Items    ${items}

Count Items
    [Tags]    robot:private
    [Arguments]    ${items}
    Length Should Be    ${items}    2
```
