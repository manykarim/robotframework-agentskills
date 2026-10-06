# skill-script-execution Specification

## Purpose
Define how the helper scripts bundled with rf-agentskills skills (`rf_libdoc.py`, `rf_results.py` and future ones) are invoked and how they behave as command-line tools. The goal is that they run in the user's project environment, can be located by any supported agent, and fail with actionable diagnostics.

## Requirements

### Requirement: Scripts run in the project environment

Every documented invocation of a skill script SHALL use `uv run python <script-path> …` as the default command. This covers SKILL.md, subagent definitions, hook messages and repository docs. Each document SHALL also give one fallback line for non-uv projects that names the project interpreter (`.venv/bin/python`, `poetry run python`) and refers to the rf-setup skill. Documented invocations SHALL NOT use a bare `python`/`python3` from PATH. Script-related documentation SHALL NOT recommend `pip install` into a global or system interpreter.

#### Scenario: Canonical command in SKILL.md
- **WHEN** the rf-libdoc or rf-results SKILL.md is read in any channel
- **THEN** every fenced shell command that runs a bundled script starts with `uv run python`
- **AND** the document contains a single fallback line naming the non-uv project interpreter and rf-setup

#### Scenario: Libraries of the project are visible
- **WHEN** `uv run python <skill-dir>/scripts/rf_libdoc.py --library Browser --search click` runs in a uv project that depends on `robotframework-browser`
- **THEN** the Browser library is loaded from the project environment and matching keywords are returned

#### Scenario: No system pip advice
- **WHEN** the repository's skill docs, scripts and hook messages are scanned
- **THEN** no script-related text advises `pip install` outside a project environment

### Requirement: Script paths resolve from the skill directory in every channel

Script paths in SKILL.md SHALL resolve to the skill's own `scripts/` directory whatever the agent's working directory is. The root and VS Code channels SHALL use paths relative to the skill root (`scripts/<name>.py`) and SHALL state in the SKILL.md that such paths are relative to the skill directory. The Claude Code plugin channel SHALL use `${CLAUDE_SKILL_DIR}/scripts/<name>.py`. When an installed agent expands neither form, the installer SHALL write the absolute installed skill path. No channel SHALL reference `${CLAUDE_PLUGIN_ROOT}` inside a SKILL.md. Each skill that uses a script SHALL ship that script inside its own `scripts/` directory in every channel.

#### Scenario: Plugin channel uses the skill-dir variable
- **WHEN** the sync script generates the plugin copy of a skill with scripts
- **THEN** its SKILL.md commands reference `${CLAUDE_SKILL_DIR}/scripts/<name>.py`
- **AND** `plugins/rf-agentskills/skills/<skill>/scripts/<name>.py` exists

#### Scenario: Root channel stays portable
- **WHEN** the root `skills/<skill>/SKILL.md` is read
- **THEN** script commands use `scripts/<name>.py` relative to the skill directory and contain no agent-specific variables

#### Scenario: Installer resolves paths for other agents
- **WHEN** the installer installs a script-bearing skill for an agent adapter that does not expand `${CLAUDE_SKILL_DIR}`
- **THEN** the installed SKILL.md references the absolute path of the installed script, and that file exists

#### Scenario: Works from project CWD in Claude Code
- **WHEN** Claude Code loads the plugin skill and runs its documented command from the project root
- **THEN** the script path resolves on the first attempt, with no retry caused by a missing file

### Requirement: Script dependencies are declared

Each skill script SHALL declare its runtime requirements in PEP 723 inline script metadata. The metadata SHALL include `requires-python` and `robotframework>=7`. When a script starts, it SHALL verify that Robot Framework is importable and at least version 7. Each skill that ships a script SHALL state in its `compatibility` frontmatter that it needs Python and Robot Framework 7 or newer in the project environment.

#### Scenario: Inline metadata present
- **WHEN** a shipped skill script is parsed for a `# /// script` block
- **THEN** the block exists and lists `robotframework>=7` in `dependencies` and a `requires-python` bound

#### Scenario: Old Robot Framework detected
- **WHEN** a script runs under an interpreter with Robot Framework 6.1
- **THEN** it exits with the environment exit code and stderr names the found version, the interpreter path and the required minimum

### Requirement: Consistent exit codes

Every skill script SHALL use these exit codes:
- `0` when the operation completed. This includes a search that found no matches.
- `1` for an unexpected internal error.
- `2` for invalid command-line usage.
- `3` when the environment is unsuitable (Robot Framework missing or too old).
- `4` when the requested input cannot be found or loaded. Examples are an `output.xml` that is missing or unparseable, or a state where every requested library, resource or spec failed to load.

When only some requested sources fail to load, the script SHALL exit `0`, report the failures in its JSON output, and emit a warning on stderr.

#### Scenario: No matches is success
- **WHEN** `rf_libdoc.py --library BuiltIn --search zzzz-no-match` runs
- **THEN** it exits 0 with an empty results list

#### Scenario: Missing output.xml
- **WHEN** `rf_results.py --output does-not-exist.xml` runs
- **THEN** it exits 4 and stderr names the missing path

#### Scenario: Unknown library only
- **WHEN** `rf_libdoc.py --library NoSuchLib --search click` runs and no other source is given
- **THEN** it exits 4 and stderr explains the import failure and how to add the library to the project environment

#### Scenario: Partial load failure
- **WHEN** `rf_libdoc.py --library BuiltIn --library NoSuchLib --search log` runs
- **THEN** it exits 0, the BuiltIn results are returned, the JSON reports the NoSuchLib load error, and stderr carries a warning

#### Scenario: Missing argument
- **WHEN** `rf_results.py` runs with no `--output`/`--outputs`
- **THEN** it exits 2 with a usage message on stderr

### Requirement: Diagnostics are on stderr and actionable

Scripts SHALL write only the JSON result to stdout. All diagnostics SHALL go to stderr as lines prefixed `error:`, `warning:` or `hint:`. Every non-zero exit SHALL include at least one `hint:` line that states a concrete next action. For environment errors (exit 3) the stderr output SHALL name the running interpreter (`sys.executable`). It SHALL also suggest the project-environment command (`uv run python …`) and the uv-based install (`uv add robotframework`). On a non-zero exit, stdout SHALL be empty.

#### Scenario: Robot Framework missing
- **WHEN** a script runs under an interpreter without Robot Framework installed
- **THEN** it exits 3, stdout is empty, and stderr contains an `error:` line naming the interpreter path and `hint:` lines suggesting `uv run python …` and `uv add robotframework`
- **AND** stderr does not suggest `pip install`

#### Scenario: Stdout stays parseable
- **WHEN** a script succeeds with warnings
- **THEN** stdout parses as a single JSON document and all warnings appear only on stderr

### Requirement: Help includes runnable examples

Each script's `--help` output SHALL describe every option and SHALL end with an examples section. That section SHALL contain at least three example invocations in the canonical `uv run python scripts/<name>.py …` form, covering the script's main modes. `--help` SHALL work without Robot Framework installed and SHALL exit 0.

#### Scenario: Help without dependencies
- **WHEN** `rf_results.py --help` runs under an interpreter without Robot Framework
- **THEN** it exits 0 and prints the options and an examples section with at least three `uv run python` invocations

### Requirement: Output is bounded by default

Script output SHALL be bounded by default, and callers SHALL be able to raise or remove each bound explicitly:
- `rf_libdoc.py` SHALL cap each keyword `doc` at a default character limit (`--max-doc-chars`, `0` meaning unlimited). Truncated text SHALL end with a marker giving the omitted character count and the flag that shows the full text. The JSON keys and item shape SHALL stay unchanged.
- `rf_libdoc.py` SHALL keep a default `--limit` on search results.
- `rf_results.py` SHALL cap the items listed in `details` and `errors` with `--limit` (failed tests first). For each capped list it SHALL report how many items were omitted.

#### Scenario: Long keyword doc truncated
- **WHEN** `rf_libdoc.py --library SeleniumLibrary --keyword "Input Text"` runs with default flags
- **THEN** the keyword doc is at most the default limit plus the marker, and the marker states how many characters were omitted and names `--max-doc-chars 0`

#### Scenario: Full doc on request
- **WHEN** the same command runs with `--max-doc-chars 0`
- **THEN** the full doc is returned without a marker

#### Scenario: Large result set capped
- **WHEN** `rf_results.py --output big.xml --sections details --limit 20` runs on a suite with 500 tests
- **THEN** at most 20 tests are listed, failed tests are listed first, and the output reports 480 omitted tests

### Requirement: Results can be written to a file

Each script SHALL accept `--json-out FILE`. When it is given, the script SHALL write the full JSON result to `FILE`, creating parent directories as needed. It SHALL then print to stdout a single small JSON object with the written path, the byte size and the mode. The existing `rf_results.py --output` option SHALL keep its meaning as the input `output.xml` path.

#### Scenario: Write to file
- **WHEN** `rf_results.py --output output.xml --sections all --json-out results/summary.json` runs
- **THEN** `results/summary.json` contains the full JSON result and stdout contains only a short JSON object naming that path and its size

### Requirement: Script trees contain only regular files

Skill `scripts/` directories SHALL contain regular files only, with no symlinks, in every channel. A skill script SHALL NOT import code from another skill's directory. The drift check SHALL fail when any shipped skill tree contains a symlink.

#### Scenario: Symlink rejected
- **WHEN** a symlink is added under any `skills/*/scripts/` directory
- **THEN** `scripts/check-drift.sh` exits non-zero and names the symlink
