## MODIFIED Requirements

### Requirement: No references to retired skills remain in shipped content

Shipped content SHALL NOT name, link to or instruct the agent to use a retired skill, a retired subagent, their scripts or their MCP tools. This covers every `SKILL.md` and reference file, the subagent prompts, the hook scripts and their injected text, plugin/marketplace/extension descriptions, the README, and current-behaviour docs and test fixtures. Historical records (archived OpenSpec changes, dated plans and reports, eval run outputs) are exempt.

Retired skills are the generator skills (`rf-keyword-builder`, `rf-testcase-builder`, `rf-resource-architect`), `rf-robotcode`, `rf-libdoc` and `rf-results`. The retired subagent is `rf-keyword-consultant`. The retired scripts are `rf_libdoc.py` and `rf_results.py`.

#### Scenario: Repository scan finds no live references
- **WHEN** the repository is searched for `keyword-builder`, `keyword_builder`, `testcase-builder`, `testcase_builder`, `resource-architect`, `resource_architect`, `rf-robotcode`, `rf-libdoc`, `rf_libdoc`, `rf-results`, `rf_results` and `rf-keyword-consultant`, excluding `openspec/changes/archive/`, `openspec/specs/` requirement text about the retirement itself, `eval/runs/`, dated plan/report documents, `CHANGELOG` history entries and dependency directories
- **THEN** no match is found

#### Scenario: Companion tables drop the generator rows
- **WHEN** the Companion Skills section of any shipped skill is read
- **THEN** it has no row pointing to a retired skill

#### Scenario: Subagents write Robot Framework directly
- **WHEN** the `rf-test-architect` and `rf-migration-guide` subagent prompts are read
- **THEN** their workflows tell the agent to write keywords, test cases and resource files directly, to verify keyword names and arguments with `robotcode doc keyword`, and to check the result with `robotcode analyze code`
- **AND** they do not invoke any generator script or tool

#### Scenario: Injected context lists only shipped skills
- **WHEN** the context-injection hook fires on a Robot Framework prompt
- **THEN** every skill it names exists in the plugin
- **AND** it names none of the retired skills

### Requirement: Retirements are released as a breaking content change

Removing a skill, a subagent or an MCP tool SHALL bump the content channel's major version (every plugin and marketplace manifest in lockstep) and SHALL be recorded in the content and installer CHANGELOGs with what was removed, why, and what to use instead.

#### Scenario: Version and changelog reflect the retirement
- **WHEN** the release containing this change is prepared
- **THEN** `plugins/rf-agentskills/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` carry the same new major version
- **AND** the CHANGELOG entry lists the removed skills (`rf-robotcode`, `rf-libdoc`, `rf-results`), the removed subagent (`rf-keyword-consultant`), the removed scripts, and the replacement (`robotcode doc`, `robotcode results`, the robotcode plugin, and the `robotcode[all]>=2.8` prerequisite)

### Requirement: The bundle ships no MCP server

The content bundle SHALL NOT ship an MCP server or an MCP server configuration in any channel: the Claude Code plugin has no `.mcp.json` and no `servers/` directory, and the installer writes no MCP server entry for any agent. Skills SHALL run their helper scripts or the project's robotcode CLI directly. Shipped content SHALL NOT instruct the agent to call `rf_libdoc_search`, `rf_libdoc_explain`, `rf_results_analyze` or `rf_check_library`.

#### Scenario: Plugin has no MCP config
- **WHEN** the plugin tree `plugins/rf-agentskills/` is listed
- **THEN** it contains no `.mcp.json` and no `servers/` directory

#### Scenario: Subagents name skills, not tools
- **WHEN** the subagent files are searched for the retired tool names
- **THEN** none is found, and keyword lookup and results reading use `robotcode doc` and `robotcode results`

## ADDED Requirements

### Requirement: Upgrades remove the robotcode-overlap skills and subagent

An installer upgrade or reinstall SHALL remove the `rf-robotcode`, `rf-libdoc` and `rf-results` skill directories and the `rf-keyword-consultant` subagent files (including the Codex and OpenCode variants) from every location the installer manages. It SHALL remove them only when they carry the installer's ownership marker. It SHALL also remove their Claude Desktop archives. Directories without the marker SHALL be left in place, and the upgrade SHALL print a note naming them.

#### Scenario: Managed copies removed
- **WHEN** a project that has installer-managed `rf-libdoc`, `rf-results`, `rf-robotcode` and `rf-keyword-consultant` copies is upgraded
- **THEN** those copies are gone, the nine remaining skills and three subagents are present, and the summary lists what was removed

#### Scenario: Hand-copied folder kept
- **WHEN** an `rf-results` folder without the ownership marker exists in a managed skills directory
- **THEN** the upgrade leaves it in place and prints a note that it was retired and can be deleted
