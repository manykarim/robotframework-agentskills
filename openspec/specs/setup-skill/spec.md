# setup-skill Specification

## Purpose

Provide a Robot Framework agent skill that guides AI agents to install Robot Framework, its libraries and tooling into the right project environment with uv (preferred), venv + pip or poetry, and to verify the result, so that every other skill finds a working setup.

## Requirements

### Requirement: Setup skill exists and follows the house structure

The repository SHALL provide a skill at `skills/rf-setup/` with a `SKILL.md` whose frontmatter has `name: rf-setup` (matching its directory) and a non-empty `description`, a `references/` directory and an `assets/examples/` directory.

#### Scenario: Skill directory and frontmatter
- **WHEN** the repository is inspected
- **THEN** `skills/rf-setup/SKILL.md` exists with frontmatter `name: rf-setup` and a description that mentions installing Robot Framework and uv, venv/pip and poetry
- **AND** `references/` and `assets/examples/` exist and each contain at least one file

#### Scenario: Marketplace validation passes
- **WHEN** the marketplace/SKILL.md validation test suite runs
- **THEN** the new skill passes the same frontmatter and structure checks applied to every other skill

### Requirement: Tool choice follows the project, uv by default

The skill SHALL tell agents to detect the tool an existing project already uses before installing anything (`uv.lock` → uv, `poetry.lock` or `[tool.poetry]` → poetry, `requirements*.txt` / an existing venv → pip), and to use uv for new projects. It SHALL NOT recommend installing into the system Python.

#### Scenario: Detection table present
- **WHEN** `SKILL.md` is read
- **THEN** it maps `uv.lock`, `poetry.lock` and `requirements*.txt` to uv, poetry and pip respectively, and names uv as the default for new projects

#### Scenario: No system-wide installs
- **WHEN** any install command in the skill is read
- **THEN** it installs into a project environment (uv project, activated venv, poetry env) or, for CLI tools only, into an isolated tool environment (`uv tool`, `pipx`)
- **AND** the skill states that test libraries must not be installed with `pipx` / `uv tool` or `sudo pip`

### Requirement: Each install path has a complete, verified recipe

The skill SHALL provide a reference each for uv, venv + pip, and poetry. Each covers creating the environment, pinning a Python version, adding Robot Framework and libraries (including dev-only tools), locking or pinning, running `robot`, and reproducing the environment on another machine or in CI. Each recipe SHALL have been run successfully before release.

#### Scenario: Three install references present
- **WHEN** `references/` is listed
- **THEN** it contains `uv.md`, `venv-pip.md` and `poetry.md`

#### Scenario: Recipes run
- **WHEN** the recipe in each of the three references is followed in an empty directory with the recommended Python
- **THEN** `robot --version` runs in that environment and the example smoke test passes

#### Scenario: Windows and POSIX activation shown
- **WHEN** `references/venv-pip.md` is read
- **THEN** it shows venv activation for bash/zsh, Windows PowerShell and cmd, and how to call the venv's Python without activation

### Requirement: Python version guidance matches library floors

The skill SHALL state the minimum Python version required by Robot Framework and by each library it covers, with the date the floors were checked, and SHALL recommend a single Python version that satisfies all of them.

#### Scenario: Floors and recommendation stated
- **WHEN** `SKILL.md` is read
- **THEN** it recommends Python 3.12 and lists the higher floors: 3.10+ for Browser, SeleniumLibrary, robotcode and robocop; 3.11+ for RESTinstance; 3.12+ for PlatynUI new_core

### Requirement: Library-specific post-install steps are documented

The skill SHALL document, per library, the package name and any step needed after installing the Python package: Browser (`[bb]` BrowserBatteries with `rfbrowser install`, or Node.js LTS with `rfbrowser init`), SeleniumLibrary (Selenium Manager resolves drivers), AppiumLibrary (Appium server and platform drivers via npm), RequestsLibrary, RESTinstance, PlatynUI (pre-release install), robotcode and robocop. It SHALL link to the library skill for usage.

#### Scenario: Browser has both install paths
- **WHEN** `references/libraries.md` is read
- **THEN** it shows the no-Node path (`robotframework-browser[bb]` then `rfbrowser install`) and the Node path (Node 22/24/26 LTS, `robotframework-browser`, then `rfbrowser init`), and the `python -m Browser.entry` fallback when `rfbrowser` is not found

#### Scenario: Library skills linked
- **WHEN** the library add-on table in `SKILL.md` is read
- **THEN** each library row names its companion skill (`rf-browser`, `rf-selenium`, `rf-appium`, `rf-requests`, `rf-restinstance`, `rf-platynui`, `rf-robotcode`)

### Requirement: Setup is verified before handing over

The skill SHALL end its workflow with verification: the interpreter and versions in use (`robot --version`, and `robotcode discover info` when robotcode is installed), a smoke test run, and a dry run of the project's suites.

#### Scenario: Verification steps present
- **WHEN** `SKILL.md` is read
- **THEN** it lists verification commands for the chosen tool (for example `uv run robot --version`, `uv run robot --dryrun tests`) and refers to the example smoke test

#### Scenario: Examples are valid
- **WHEN** the example tests run
- **THEN** every `.toml` example parses, the example smoke test passes `robot --dryrun`, and the example GitHub Actions workflow is valid YAML

### Requirement: Project layout, CI and troubleshooting are covered

The skill SHALL provide a recommended project layout (with `robot.toml`, `tests/`, `resources/` and ignored output folders), a CI example using uv, and a troubleshooting reference covering at least: wrong interpreter / environment, PEP 668 "externally-managed-environment", `rfbrowser` not found, Python too old for a library, and PowerShell execution policy blocking venv activation.

#### Scenario: References present
- **WHEN** `references/` is listed
- **THEN** it contains `project-layout.md`, `ci.md`, `cli-tools.md`, `libraries.md` and `troubleshooting.md`

#### Scenario: Troubleshooting entries
- **WHEN** `references/troubleshooting.md` is read
- **THEN** it has an entry, with symptom and fix, for each of the five problems listed above

### Requirement: Setup skill is discoverable from hooks and companion skills

The `UserPromptSubmit` context text SHALL list the setup skill, the SessionStart environment check's install hint SHALL point to the setup skill and show a uv command, and `rf-robotcode` SHALL name `rf-setup` in its companion skills.

#### Scenario: Injected context names the setup skill
- **WHEN** a Robot Framework prompt triggers the context-injection hook
- **THEN** the injected text names the `setup` skill

#### Scenario: Environment check points to the setup skill
- **WHEN** the SessionStart environment check reports missing packages
- **THEN** its install hint mentions the setup skill and includes a `uv add` command
- **AND** the check still always exits 0

#### Scenario: robotcode skill links to setup
- **WHEN** the `rf-robotcode` `SKILL.md` companion section is read
- **THEN** it names `rf-setup` for installing Robot Framework and robotcode into the project environment

### Requirement: Setup skill is distributed without drift

The skill SHALL be registered in the sync tooling so the Claude Code plugin, VS Code extension and installer channels are generated from the root skill under the same `rf-setup` identifier, and the drift check SHALL pass.

#### Scenario: Sync registers the skill
- **WHEN** `scripts/sync-skills.sh` runs
- **THEN** the skill is propagated to `plugins/rf-agentskills/skills/rf-setup/` with `name: rf-setup`, and to `vscode-extension/skills/rf-setup/`, and `vscode-extension/package.json` lists it

#### Scenario: Drift check passes
- **WHEN** `scripts/check-drift.sh` runs after sync
- **THEN** it reports no drift

### Requirement: Project layout reference points to current skills and states variable-file rules

The rf-setup `references/project-layout.md` SHALL do the following:
- point to `rf-language` for keyword, resource-file and variable-file design, and name no retired skill;
- describe `libraries/` as the place for project Python keyword libraries, and state that it is put on the python-path (`python-path` in `robot.toml`, `--pythonpath` for plain `robot`);
- state that YAML variable files under `variables/` need PyYAML in the project environment (`uv add pyyaml`, with the non-uv equivalent), and that JSON variable files need no extra package;
- state that plain `robot` does not read `robot.toml`, so options such as `--variablefile variables/<env>.yaml` and `--pythonpath` have to be passed on the command line unless the run goes through robotcode with a profile.

The rf-setup `SKILL.md` Companion Skills table SHALL have a row for `rf-language` and no row for a retired skill.

#### Scenario: Layout reference names the keyword design skill
- **WHEN** `references/project-layout.md` is read
- **THEN** it names `rf-language` for resource and keyword conventions
- **AND** it does not contain `rf-resource-architect`

#### Scenario: YAML variable files need PyYAML
- **WHEN** `references/project-layout.md` describes `variables/dev.yaml`
- **THEN** it states that PyYAML must be added to the project environment and shows `uv add pyyaml`

#### Scenario: robot.toml is not read by plain robot
- **WHEN** `references/project-layout.md` shows how to select an environment's variable file
- **THEN** it gives a plain `robot` command with `--variablefile` and says that `robot.toml` is only read by robotcode
