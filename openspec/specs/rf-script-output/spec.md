# rf-script-output Specification

## Purpose

Define a stable, lean, and consistent output contract for the Robot Framework helper scripts (`rf_libdoc.py` and `testcase_builder.py`) so that agent consumers receive predictable, single-shape responses dominated by the data they asked for, free of fixed library prose overhead, with directly usable artifacts, and kept in sync across all distribution channels.

## Requirements

### Requirement: Library prose doc is not embedded by default

`rf_libdoc.py` SHALL NOT include a library's full prose `doc` in its output by default. The full `doc` (and `source`) SHALL be available only when explicitly requested via an opt-in flag (`--include-library-doc`). Default library entries SHALL carry only lightweight metadata (`name`, `type`, `version`, `scope`, `doc_format`, and optionally `short_doc`).

#### Scenario: Search payload excludes library prose
- **WHEN** `rf_libdoc.py --library Browser --search "mouse click"` runs without `--include-library-doc`
- **THEN** no library entry in the output contains the full `doc` prose
- **AND** the total payload is a small multiple of the matched-keyword data, not dominated by fixed library overhead

#### Scenario: Opt-in restores full library doc
- **WHEN** the same command is run with `--include-library-doc`
- **THEN** library entries include the full `doc`

### Requirement: Per-match library reference is minimal

In keyword-explain output, each result's `library` field SHALL be a minimal reference (`{name, type, version}`) and SHALL NOT re-embed the full library meta or `doc`.

#### Scenario: Explain output is not dominated by library doc
- **WHEN** `rf_libdoc.py --library Browser --keyword Hover` runs (default flags)
- **THEN** the result's `library` field contains no full `doc`
- **AND** the dominant content of the payload is the keyword's own documentation and usage, not library prose

#### Scenario: Non-matching libraries do not bloat output
- **WHEN** multiple libraries are supplied and only one contains the requested keyword
- **THEN** libraries that contributed zero matches do not have their full `doc` embedded in the output

### Requirement: Stable single-shape response with mode discriminator

`rf_libdoc.py` SHALL return a stable top-level schema for every invocation: a `mode` field (`"explain"`, `"search"`, `"fallback"`, or `"list"`) and a single `results` array whose items share one schema. Item fields that do not apply to a mode SHALL be present as `null` rather than absent, and the top-level key names SHALL NOT change based on whether a keyword was found.

#### Scenario: Found, not-found, and search share the schema
- **WHEN** `--keyword <exact>`, `--keyword <missing>`, and `--search <query>` are each run
- **THEN** all three return the same top-level keys (including `mode` and `results`)
- **AND** a consumer can read `results` without branching on different top-level key names

#### Scenario: Mode reflects the operation
- **WHEN** an exact keyword is found
- **THEN** `mode` is `"explain"`
- **WHEN** an exact keyword is not found and a search fallback runs
- **THEN** `mode` is `"fallback"`
- **WHEN** a `--search` query runs
- **THEN** `mode` is `"search"`

#### Scenario: Result items carry the right optional fields
- **WHEN** results come from an explain/fallback
- **THEN** each item includes a non-null `usage`
- **WHEN** results come from a search
- **THEN** each item includes a non-null `score` and `reasons`

### Requirement: Clean structured usage breakdown

The `usage` breakdown SHALL expose each argument as a structured entry `{name, type, default, kind}` where `name` is the bare parameter name (no `: type` annotation), `type` is the annotation (or null), `default` is the default value (or null), and `kind ∈ {required, optional, vararg, kwarg, named_only}`. Any `defaults` mapping SHALL be keyed by the bare parameter name.

#### Scenario: Annotations are separated from names
- **WHEN** a keyword argument is `button: MouseButton = left`
- **THEN** its structured entry is `{name: "button", type: "MouseButton", default: "left", kind: ...}`
- **AND** any `defaults` map uses the key `"button"`, not `"button: MouseButton"`

#### Scenario: Positional vs keyword-only is preserved
- **WHEN** a keyword has arguments after a `*`/vararg sentinel (keyword-only args)
- **THEN** those arguments have `kind: "named_only"` (distinct from ordinary `optional`)

### Requirement: In-repo consumers stay consistent with the contract

The MCP server and skill documentation SHALL emit/describe the same output contract as `rf_libdoc.py`. The contract SHALL be documented in the single `rf-libdoc` skill's `SKILL.md`. The MCP tools `rf_libdoc_search` and `rf_libdoc_explain` SHALL keep their names. Changes to the script's schema SHALL be reflected in `rf-tools-server.py` and the `rf-libdoc` skill doc in the same change, and the cross-channel drift check SHALL pass.

#### Scenario: MCP server matches the script schema
- **WHEN** the `rf-tools` MCP libdoc tools (`rf_libdoc_search`, `rf_libdoc_explain`) run
- **THEN** their output uses the same `mode`/`results` schema and minimal library references as the CLI script

#### Scenario: Contract documented once
- **WHEN** the shipped skills are searched for the output-contract description (`mode`, `results`, `usage.params`)
- **THEN** it is found in the `rf-libdoc` skill and matches the script's behaviour

#### Scenario: Channels stay in sync
- **WHEN** `scripts/sync-skills.sh` and `scripts/check-drift.sh` run after the change
- **THEN** the drift check reports no drift

### Requirement: rf_results output carries no criticality grouping

`rf_results.py` and the `rf_results_analyze` MCP tool SHALL NOT emit a `criticality` key in the `details` section, and the rf-results skill SHALL NOT describe criticality grouping. Robot Framework removed test criticality in 4.0. Tag-based grouping stays available through `details.tags`. This is a breaking change to the `details` shape, and the change that makes it SHALL record it in the installer CHANGELOG.

#### Scenario: Details section without criticality
- **WHEN** `rf_results.py --output output.xml --sections details` runs
- **THEN** `details` contains `suites`, `failed_tests` and `tags`
- **AND** `details` has no `criticality` key

#### Scenario: Skill text has no criticality wording
- **WHEN** the rf-results `SKILL.md` (frontmatter description and body) is read
- **THEN** it does not mention criticality

#### Scenario: Tags still cover critical-style grouping
- **WHEN** a test carries a tag such as `critical` or `smoke`
- **THEN** its counts appear under that tag's entry in `details.tags`
