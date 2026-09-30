## ADDED Requirements

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
