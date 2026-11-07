## MODIFIED Requirements

### Requirement: Scripts run in the project environment

Every documented invocation of a skill script SHALL use `uv run python <script-path> …` as the default command. This covers SKILL.md, subagent definitions, hook messages and repository docs. Each document SHALL also give one fallback line for non-uv projects that names the project interpreter (`.venv/bin/python`, `poetry run python`) and refers to the rf-setup skill. Documented invocations SHALL NOT use a bare `python`/`python3` from PATH. Script-related documentation SHALL NOT recommend `pip install` into a global or system interpreter.

#### Scenario: Canonical command in SKILL.md
- **WHEN** the rf-language or rf-python-library SKILL.md is read in any channel
- **THEN** every fenced shell command that runs a bundled script starts with `uv run python`
- **AND** the document contains a single fallback line naming the non-uv project interpreter and rf-setup

#### Scenario: Libraries of the project are visible
- **WHEN** `uv run python <skill-dir>/scripts/rf_conventions.py` runs in a uv project that depends on Robot Framework 7.4
- **THEN** the script reports Robot Framework 7.4 from the project environment

#### Scenario: No system pip advice
- **WHEN** the repository's skill docs, scripts and hook messages are scanned
- **THEN** no script-related text advises `pip install` outside a project environment

