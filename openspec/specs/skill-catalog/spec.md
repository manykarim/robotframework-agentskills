# skill-catalog Specification

## Purpose
Define which skills, helper scripts and MCP tools the rf-agentskills content bundle ships, and guarantee that a skill retired from the catalog disappears from every distribution channel with no dangling references, orphaned copies or stale installs left behind.

## Requirements

### Requirement: Generator skills are not shipped

The content bundle SHALL NOT contain the skills `rf-keyword-builder`, `rf-testcase-builder` or `rf-resource-architect`, nor the scripts `keyword_builder.py`, `testcase_builder.py` or `resource_architect.py`, in any channel: the root `skills/` tree, the Claude Code plugin, the VS Code extension (skill directories and `package.json` skill list), the installer's bundled assets, or the release tarballs built from them.

#### Scenario: No generator skill directories in any channel
- **WHEN** the root `skills/`, `plugins/rf-agentskills/skills/`, `vscode-extension/skills/` and a freshly built installer `_assets/` tree are listed
- **THEN** none contains a skill whose `name:` or directory is `rf-keyword-builder`, `keyword-builder`, `rf-testcase-builder`, `testcase-builder`, `rf-resource-architect` or `resource-architect`

#### Scenario: No generator scripts shipped
- **WHEN** the plugin `scripts/` directory, the root skill `scripts/` directories and the installer `_assets/scripts/` are listed
- **THEN** none contains `keyword_builder.py`, `testcase_builder.py` or `resource_architect.py`

#### Scenario: VS Code manifest lists only shipped skills
- **WHEN** `vscode-extension/package.json` is read
- **THEN** every skill path it lists exists on disk
- **AND** no listed path refers to a retired generator skill

### Requirement: No references to retired skills remain in shipped content

Shipped content SHALL NOT name, link to or instruct the agent to use a retired skill, its script or its MCP tool. This covers every `SKILL.md` and reference file, the subagent prompts, the hook scripts and their injected text, plugin/marketplace/extension descriptions, the README, and current-behaviour docs and test fixtures. Historical records (archived OpenSpec changes, dated plans and reports, eval run outputs) are exempt.

#### Scenario: Repository scan finds no live references
- **WHEN** the repository is searched for `keyword-builder`, `keyword_builder`, `testcase-builder`, `testcase_builder`, `resource-architect` and `resource_architect`, excluding `openspec/changes/archive/`, `eval/runs/`, dated plan/report documents, `CHANGELOG` history entries and dependency directories
- **THEN** no match is found

#### Scenario: Companion tables drop the generator rows
- **WHEN** the Companion Skills section of any shipped skill is read
- **THEN** it has no row pointing to a retired generator skill

#### Scenario: Subagents write Robot Framework directly
- **WHEN** the `rf-test-architect`, `rf-keyword-consultant` and `rf-migration-guide` subagent prompts are read
- **THEN** their workflows tell the agent to write keywords, test cases and resource files directly and to verify keyword names and arguments with the libdoc tooling (or `robotcode libdoc`) and the result with `robot --dryrun`
- **AND** they do not invoke any generator script or tool

#### Scenario: Injected context lists only shipped skills
- **WHEN** the context-injection hook fires on a Robot Framework prompt
- **THEN** every skill it names exists in the plugin
- **AND** it names none of the retired generator skills

### Requirement: Distribution tooling rejects orphaned copies

The sync script SHALL make each distribution channel mirror the root `skills/` tree, removing plugin skill directories and plugin scripts that have no root source. The drift check SHALL fail when a plugin skill directory, plugin helper script or VS Code skill directory exists without a corresponding root skill or script.

#### Scenario: Sync removes a retired skill's copies
- **WHEN** a skill directory is deleted from root `skills/` and `scripts/sync-skills.sh` runs
- **THEN** its plugin skill directory, its plugin script(s) and its VS Code skill directory no longer exist

#### Scenario: Drift check catches an orphan
- **WHEN** a plugin skill directory or plugin Python helper script exists that no root skill provides
- **THEN** `scripts/check-drift.sh` exits non-zero and names the orphan

### Requirement: Evaluation assets cover only shipped skills

Eval tasks SHALL only target skills that ship. Every task's `skill:` field SHALL name a skill present in the plugin, and the smoke-eval script SHALL run a task whose skill ships.

#### Scenario: Task skills resolve
- **WHEN** every YAML file under `eval/tasks/` is loaded
- **THEN** each `skill:` value matches a skill directory in `plugins/rf-agentskills/skills/`

#### Scenario: Smoke eval uses a live task
- **WHEN** `scripts/eval-smoke.sh` is read
- **THEN** the task it runs exists and targets a shipped skill

### Requirement: Retirements are released as a breaking content change

Removing a skill or an MCP tool SHALL bump the content channel's major version (plugin manifest, marketplace entry and VS Code extension in lockstep) and SHALL be recorded in the content and installer CHANGELOGs with what was removed, why, and what to use instead.

#### Scenario: Version and changelog reflect the retirement
- **WHEN** the release containing this change is prepared
- **THEN** `plugins/rf-agentskills/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` and `vscode-extension/package.json` carry the same new major version
- **AND** the CHANGELOG entry lists the three removed skills, the three removed MCP tools and the replacement guidance (write Robot Framework directly; verify with libdoc and `robot --dryrun`)

### Requirement: The bundle ships no MCP server

The content bundle SHALL NOT ship an MCP server or an MCP server configuration in any channel: the Claude Code plugin has no `.mcp.json` and no `servers/` directory, and the installer writes no MCP server entry for any agent. Skills SHALL run their helper scripts directly. Shipped content SHALL NOT instruct the agent to call `rf_libdoc_search`, `rf_libdoc_explain`, `rf_results_analyze` or `rf_check_library`.

#### Scenario: Plugin has no MCP config
- **WHEN** the plugin tree `plugins/rf-agentskills/` is listed
- **THEN** it contains no `.mcp.json` and no `servers/` directory

#### Scenario: Subagents name skills, not tools
- **WHEN** the subagent files are searched for the retired tool names
- **THEN** none is found, and keyword lookup and results reading point to the `rf-libdoc` and `rf-results` skills
