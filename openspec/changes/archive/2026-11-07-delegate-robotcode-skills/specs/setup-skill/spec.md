## MODIFIED Requirements

### Requirement: Library-specific post-install steps are documented

The skill SHALL document, per library, the package name and any step needed after installing the Python package:
- Browser: `[bb]` BrowserBatteries with `rfbrowser install`, or Node.js LTS with `rfbrowser init`;
- SeleniumLibrary: Selenium Manager resolves drivers;
- AppiumLibrary: Appium server and platform drivers via npm;
- RequestsLibrary;
- RESTinstance;
- PlatynUI: pre-release install.

It SHALL link to the library skill for usage. robotcode is covered by the prerequisite step, not by this table. Robocop comes with `robotcode[all]` and SHALL NOT be listed as a separate install.

#### Scenario: Browser has both install paths
- **WHEN** `references/libraries.md` is read
- **THEN** it shows the no-Node path (`robotframework-browser[bb]` then `rfbrowser install`) and the Node path (Node 22/24/26 LTS, `robotframework-browser`, then `rfbrowser init`), and the `python -m Browser.entry` fallback when `rfbrowser` is not found

#### Scenario: Library skills linked
- **WHEN** the library add-on table in `SKILL.md` is read
- **THEN** each library row names its companion skill (`rf-browser`, `rf-selenium`, `rf-appium`, `rf-requests`, `rf-restinstance`, `rf-platynui`), and no row names `rf-robotcode`

### Requirement: Setup is verified before handing over

The skill SHALL end its workflow with verification:
- the interpreter and versions in use (`robot --version` and `robotcode discover info`);
- a smoke test run;
- a static check of the project's suites with `robotcode analyze code`.

#### Scenario: Verification steps present
- **WHEN** `SKILL.md` is read
- **THEN** it lists verification commands for the chosen tool (for example `uv run robot --version`, `uv run robotcode discover info`, `uv run robotcode analyze code`) and refers to the example smoke test

#### Scenario: Examples are valid
- **WHEN** the example tests run
- **THEN** every `.toml` example parses, the example smoke test passes `robot --dryrun`, and the example GitHub Actions workflow is valid YAML

### Requirement: Setup skill is discoverable from hooks and companion skills

The setup skill SHALL be reachable from three places:
- the `UserPromptSubmit` context text SHALL list it;
- the SessionStart environment check's install hint SHALL point to it and show a uv command;
- every other shipped skill SHALL name `rf-setup` in its companion skills for installing Robot Framework, robotcode and libraries.

#### Scenario: Injected context names the setup skill
- **WHEN** a Robot Framework prompt triggers the context-injection hook
- **THEN** the injected text names the `setup` skill

#### Scenario: Environment check points to the setup skill
- **WHEN** the SessionStart environment check reports missing packages
- **THEN** its install hint mentions the setup skill and includes a `uv add` command
- **AND** the check still always exits 0

#### Scenario: robotcode skill links to setup
- **WHEN** the Companion Skills section of any shipped skill other than `rf-setup` is read
- **THEN** it names `rf-setup` for installing Robot Framework, robotcode and libraries into the project environment

## ADDED Requirements

### Requirement: robotcode is a prerequisite step

The skill SHALL install robotcode as part of every new or repaired setup, right after Robot Framework, as `robotcode[all]>=2.8` in the project environment:
- uv: `uv add --dev "robotcode[all]>=2.8"`;
- Poetry: `poetry add --group dev "robotcode[all]>=2.8"`;
- venv + pip: `pip install "robotcode[all]>=2.8"`.

The step SHALL state:
- the other rf-agentskills skills and hooks assume robotcode is present;
- `[all]` is needed because it alone bundles `runner`, `analyze`, `repl` and Robocop;
- a CI job that only runs tests can use `robotcode[runner]`;
- it is verified with `robotcode --version` and `robotcode discover info` through the project environment.

When robotcode is already present but older than 2.8, the skill SHALL show the upgrade command.

#### Scenario: New uv project gets robotcode
- **WHEN** `SKILL.md` Step 3 (new project with uv) is read
- **THEN** it adds `robotcode[all]>=2.8` as a dev dependency and verifies it with `uv run robotcode --version`

#### Scenario: Extras rationale stated
- **WHEN** the robotcode prerequisite step is read
- **THEN** it names the `runner`, `analyze` and `repl` extras and Robocop as the reasons for `[all]`, and names `robotcode[runner]` for test-only CI

#### Scenario: Existing project without robotcode
- **WHEN** an agent follows the skill in a project that has Robot Framework but no robotcode
- **THEN** the skill tells it to add robotcode with the project's own tool before writing or checking tests
