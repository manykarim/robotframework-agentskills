## Purpose

Give agents one consistent, project-environment-safe way to install Robot Framework libraries: the library skills defer to rf-setup and repeat only the uv-form install line and the library-specific post-install essential, so no skill contradicts the setup skill.

## ADDED Requirements

### Requirement: Library skills defer installation to rf-setup

Each library skill (rf-browser, rf-selenium, rf-appium, rf-requests, rf-restinstance, rf-platynui) SHALL keep its installation guidance in `SKILL.md` to one short block with three parts:
- a pointer to the `rf-setup` skill for environment creation, other tools (venv + pip, Poetry) and troubleshooting
- the library's install command in uv form, identical to the "Install (uv form)" cell for that library in rf-setup's Step 4 table
- the library-specific post-install essential from the "Extra step" cell of the same table

The skill SHALL also name `rf-setup` in its companion-skills section.

#### Scenario: Pointer and uv line present
- **WHEN** a library skill's `SKILL.md` installation block is read
- **THEN** it names `rf-setup` as the place for environment setup, pip/Poetry forms and troubleshooting
- **AND** it contains the same `uv add …` command that rf-setup's Step 4 table lists for that library

#### Scenario: Post-install essential matches rf-setup
- **WHEN** the rf-appium installation block is read
- **THEN** it states that the Appium server and platform drivers are installed with npm (`appium driver install uiautomator2` / `xcuitest`), consistent with rf-setup
- **WHEN** the rf-restinstance installation block is read
- **THEN** it states the Python ≥ 3.11 floor

#### Scenario: Companion section links setup
- **WHEN** a library skill's companion-skills section is read
- **THEN** it lists `rf-setup` for installing the library into the project environment

### Requirement: No bare pip install recipes in library skills

Library-skill content (`SKILL.md`, `references/`, `assets/`) SHALL NOT contain `pip install` or `pip3 install` commands, except on a line explicitly labelled as a pip alternative (for example, text containing "pip alternative" or a `# pip:` comment next to the uv command). Tool-environment installs for standalone CLIs (`uv tool install …`) remain allowed.

#### Scenario: Check passes on compliant content
- **WHEN** the install-guidance test scans every library skill
- **THEN** it finds no `pip install` / `pip3 install` occurrence outside a line labelled as a pip alternative

#### Scenario: Check fails on a bare pip recipe
- **WHEN** a fixture library skill contains `pip install robotframework-browser` in a bash block without a pip-alternative label
- **THEN** the test fails and names the file and line

### Requirement: Selenium drivers come from Selenium Manager

rf-selenium SHALL present Selenium Manager (bundled with Selenium ≥ 4.6) as the way drivers are resolved. It SHALL NOT recommend `webdriver-manager`, custom driver-download helpers, or `executable_path` for normal use. Offline or air-gapped driver setup SHALL be deferred to rf-setup.

#### Scenario: No webdriver-manager or executable_path
- **WHEN** rf-selenium `SKILL.md`, `references/` and `assets/` are scanned
- **THEN** they contain no `webdriver-manager`, `webdriver_manager` or `executable_path=` occurrence
- **AND** `SKILL.md` states that a real browser must be installed and that Selenium Manager fetches the matching driver

#### Scenario: CI examples use the project environment
- **WHEN** a CI example in rf-selenium is read
- **THEN** it installs dependencies from the project's lock (for example `uv sync --locked`) and has no separate driver installation step

### Requirement: Browser defaults to BrowserBatteries

rf-browser SHALL present `uv add "robotframework-browser[bb]"` followed by `uv run rfbrowser install chromium` as the default install. It SHALL mention the Node.js path (`robotframework-browser` + `rfbrowser init`, Node 22/24/26 LTS) only as an escape hatch for platforms without a BrowserBatteries wheel or for users who need Node plugins. It SHALL NOT combine `rfbrowser init` with `[bb]` or `rfbrowser install` without it.

#### Scenario: Default path shown first
- **WHEN** rf-browser `SKILL.md` installation block is read
- **THEN** the first install command is `uv add "robotframework-browser[bb]"` and the next is `uv run rfbrowser install chromium`
- **AND** `rfbrowser init` appears only in the labelled Node.js escape hatch

#### Scenario: Troubleshooting consistent with setup
- **WHEN** rf-browser `references/troubleshooting.md` installation section is read
- **THEN** it contains no `pip uninstall` / `pip install` reinstall recipe and points to rf-setup for environment problems

### Requirement: PlatynUI pre-release install stays explicit in uv form

rf-platynui SHALL show its install in uv form with an explicit pre-release opt-in or exact pin: `uv add robotframework-PlatynUI==<verified dev version>` or `uv add --prerelease allow robotframework-PlatynUI`. It SHALL keep the warning that an unpinned install without the pre-release opt-in resolves the old 0.9.2 library. pip equivalents MAY appear only as a labelled pip alternative.

#### Scenario: uv-form pin and footgun warning
- **WHEN** rf-platynui `SKILL.md` installation block is read
- **THEN** it shows a `uv add` command with either the exact `0.12.0.dev…` pin or `--prerelease allow`
- **AND** it warns that a plain install gets 0.9.2 without `PlatynUI.BareMetal`

### Requirement: Install guidance changes are synced

Changes SHALL be made in root `skills/` and propagated with the sync script. The drift check SHALL pass.

#### Scenario: Channels stay in sync
- **WHEN** `scripts/sync-skills.sh` and `scripts/check-drift.sh` run after the change
- **THEN** the drift check reports no drift and the install-guidance test passes on the plugin copies too
