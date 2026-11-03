## MODIFIED Requirements

### Requirement: Library skills query libdoc instead of shipping keyword catalogs

The library skills SHALL NOT contain a keyword catalog file. `references/keywords-reference.md` SHALL NOT exist in any of the five library skills or their distribution copies. Each `SKILL.md` SHALL tell the agent how to list and show keywords with libdoc (`robotcode libdoc <Library> list "<pattern>"` and `robotcode libdoc <Library> show "<Keyword>"`, or the `rf-libdoc` script skill), using the library's import name.

#### Scenario: Catalog files absent in all channels
- **WHEN** `skills/` and `plugins/rf-agentskills/skills/` are searched for `keywords-reference.md` under the five library skills
- **THEN** no file is found, and no library `SKILL.md` or reference file links to one

#### Scenario: Libdoc instruction present
- **WHEN** a library `SKILL.md` is read
- **THEN** it contains a `robotcode libdoc <Library>` command with that library's import name (`Browser`, `SeleniumLibrary`, `AppiumLibrary`, `RequestsLibrary`, `REST`) and names the `rf-libdoc` script skill as the fallback

### Requirement: Restructured skills are distributed to every channel

After the canonical skills change, the plugin copy SHALL be regenerated so that deleted files are removed from them too, and the drift check SHALL pass.

#### Scenario: No drift after sync
- **WHEN** `scripts/sync-skills.sh` and then `scripts/check-drift.sh` run
- **THEN** the drift check exits 0, and no distribution copy still contains a file deleted from the canonical skill
