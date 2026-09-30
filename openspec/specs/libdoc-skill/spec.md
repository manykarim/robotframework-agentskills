# libdoc-skill Specification

## Purpose
Provide one Robot Framework keyword-lookup skill, `rf-libdoc`, that finds keywords for a use case and explains a keyword's arguments from libdoc data through a single bundled script with a stable JSON contract, and that defers to `robotcode libdoc` when robotcode is installed.

## Requirements

### Requirement: One libdoc skill replaces search and explain

The bundle SHALL ship exactly one libdoc skill, named `rf-libdoc`, whose root directory is `skills/rf-libdoc/`. The skills `rf-libdoc-search` and `rf-libdoc-explain` SHALL NOT be shipped in any channel (root `skills/`, Claude Code plugin, VS Code extension and its `package.json`, installer assets, release tarballs).

#### Scenario: Only the merged skill exists
- **WHEN** the root, plugin, VS Code and freshly built installer skill trees are listed
- **THEN** each contains one libdoc skill (`skills/rf-libdoc/` in root, `rf-libdoc` in VS Code, the plugin channel's name for it in the plugin)
- **AND** none contains `libdoc-search`, `libdoc-explain`, `rf-libdoc-search`, `rf-libdoc-explain`, `robotframework-libdoc-search` or `robotframework-libdoc-explain`

#### Scenario: Frontmatter name matches directory
- **WHEN** `skills/rf-libdoc/SKILL.md` is read
- **THEN** its frontmatter `name` is `rf-libdoc`

### Requirement: Description covers both jobs and the robotcode boundary

The `rf-libdoc` description SHALL state both uses — finding keywords that match a use case across libraries, resource files and suites, and explaining a keyword's arguments, types and defaults — and SHALL include a "use when" clause with trigger terms (keyword search, libdoc, keyword arguments/signature). The description or the first section of `SKILL.md` SHALL state that when `robotcode` is on PATH, `robotcode libdoc` (see `rf-robotcode`) is preferred, and that `rf-libdoc` is the fallback or the choice for ranked multi-source search and structured JSON output. The description SHALL be at most 1024 characters.

#### Scenario: Search and explain triggers present
- **WHEN** the `rf-libdoc` description is read
- **THEN** it mentions finding keywords for a use case and explaining keyword arguments
- **AND** it is at most 1024 characters

#### Scenario: robotcode boundary stated
- **WHEN** the start of `skills/rf-libdoc/SKILL.md` is read
- **THEN** it tells the agent to prefer `robotcode libdoc` when robotcode is installed and names `rf-robotcode`

### Requirement: SKILL.md documents search, explain and list with one contract

`SKILL.md` SHALL show one command for each mode — search (`--search`), explain (`--keyword`), explain with search fallback (`--keyword` + `--search`), and listing a library's keywords — and SHALL document the output contract once: the `mode` discriminator, the single `results` array, the `usage.params` structure, and the opt-in `--include-library-doc`. It SHALL list the shared input flags (`--library`, `--resource`, `--suite`, `--spec`, `--tag`, `--include-private`, `--exclude-deprecated`, `--limit`).

#### Scenario: All modes shown
- **WHEN** `skills/rf-libdoc/SKILL.md` is read
- **THEN** it contains a command using `--search`, one using `--keyword`, one using both, and one listing keywords without a query
- **AND** it names the modes `search`, `explain`, `fallback` and `list`

#### Scenario: Documented flags exist
- **WHEN** every long option in the `SKILL.md` code blocks is compared with `rf_libdoc.py --help`
- **THEN** each documented option is accepted by the script

### Requirement: Single regular-file script copy

Each channel SHALL contain exactly one `rf_libdoc.py` for the libdoc skill, as a regular file, with no symbolic links anywhere in a shipped skill tree. The root copy at `skills/rf-libdoc/scripts/rf_libdoc.py` is the source; the plugin's flat `scripts/rf_libdoc.py` and the VS Code copy SHALL be byte-identical to it.

#### Scenario: No symlinks in skill trees
- **WHEN** the root `skills/`, plugin `skills/` and `scripts/`, and `vscode-extension/skills/` trees are scanned
- **THEN** no symbolic link is found

#### Scenario: Copies identical
- **WHEN** `scripts/check-drift.sh` runs
- **THEN** it compares `skills/rf-libdoc/scripts/rf_libdoc.py` with the plugin and VS Code copies and reports no drift

### Requirement: MCP tool names are unchanged

The `rf-tools` MCP server SHALL keep exposing `rf_libdoc_search` and `rf_libdoc_explain` with their current input schemas and output contract. The merge SHALL NOT rename, remove or alias these tools.

#### Scenario: Tools still listed
- **WHEN** a client lists the `rf-tools` server's tools after the merge
- **THEN** `rf_libdoc_search` and `rf_libdoc_explain` are present with the same required inputs as before

### Requirement: References use the merged skill

Shipped content SHALL refer to keyword lookup only as `rf-libdoc` (or its plugin-channel name). Companion Skills tables SHALL have one row for `rf-libdoc` in place of the two former rows; subagent prompts, the context-injection hook text, README, marketplace/plugin/extension descriptions, installer checks, eval tasks and tests SHALL use the merged name. The context-injection trigger SHALL fire on the merged skill name and SHALL still fire on the generic term `libdoc`.

#### Scenario: No old names in shipped content
- **WHEN** the repository is searched for `libdoc-search`, `libdoc-explain`, `libdoc_search` and `libdoc_explain`, excluding the MCP tool names `rf_libdoc_search`/`rf_libdoc_explain` and their server functions, `openspec/changes/archive/`, `eval/runs/`, dated plan/report documents and CHANGELOG history
- **THEN** no match is found

#### Scenario: Companion row merged
- **WHEN** the Companion Skills section of a library skill is read
- **THEN** it has one row pointing to `rf-libdoc` for keyword search and argument lookup

#### Scenario: Hook names the merged skill
- **WHEN** the context-injection hook fires on a Robot Framework prompt
- **THEN** the injected text names the merged libdoc skill and `robotcode libdoc`, and names neither old libdoc skill

#### Scenario: Eval tasks target the merged skill
- **WHEN** eval tasks that previously used `skill: libdoc-search` are loaded
- **THEN** their `skill:` names the merged skill and their session-grader patterns match invocations of the merged skill, the script and the MCP tools

### Requirement: Upgrades remove the old libdoc skills

Upgrading any channel SHALL leave no copy of the old libdoc skills that the channel itself installed: the plugin and VS Code trees are regenerated by sync without them, and an installer re-install removes previously installed `libdoc-search/` and `libdoc-explain/` files under the prune-on-reinstall rule of `installer-uninstall-safety`.

#### Scenario: Installer re-install removes old dirs
- **WHEN** a manifest-tracked install from content 1.2.0 is upgraded by running `rf-agentskills install` again
- **THEN** the old `libdoc-search/` and `libdoc-explain/` skill directories are removed (unless user-modified, in which case they are reported)
- **AND** the merged libdoc skill is installed

#### Scenario: Release notes cover manual installs
- **WHEN** the CHANGELOG entry for the release is read
- **THEN** it states that `rf-libdoc-search` and `rf-libdoc-explain` were merged into `rf-libdoc`, that MCP tool names are unchanged, and that users who copied skill folders by hand must delete the two old folders
