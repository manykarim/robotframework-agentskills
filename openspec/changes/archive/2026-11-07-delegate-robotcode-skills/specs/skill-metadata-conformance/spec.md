## MODIFIED Requirements

### Requirement: Skills declare runtime compatibility, license and metadata

Every skill SHALL declare `license: Apache-2.0`, a `compatibility` field that states the runtimes and packages it needs (Python floor, Robot Framework floor, library package and any external runtime such as Node.js, the Appium server, robotcode or uv), and `metadata` with at least `author` and `version`. `metadata.version` MUST equal the content version in the repository `VERSION` file.

#### Scenario: Script-based skill states its Python dependencies
- **WHEN** the frontmatter of a skill that ships a Python script (for example `rf-language` or `rf-python-library`) is read
- **THEN** `compatibility` names the minimum Python version and `robotframework>=7`

#### Scenario: Library skill states its library and external runtime
- **WHEN** the frontmatter of `rf-appium` is read
- **THEN** `compatibility` names `robotframework-appiumlibrary` and the Appium server

#### Scenario: robotcode requirement stated
- **WHEN** the frontmatter of any shipped skill that runs a `robotcode` command is read
- **THEN** `compatibility` names `robotcode[all]>=2.8` in the project environment

#### Scenario: Version stays in step with the bundle
- **WHEN** `scripts/bump-version.sh` bumps the content version
- **THEN** every root skill's `metadata.version` is updated to the new value, and the validator fails if any skill disagrees with `VERSION`

