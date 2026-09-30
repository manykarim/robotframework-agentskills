## MODIFIED Requirements

### Requirement: Library skills follow the standard SKILL.md skeleton

Each library skill's `SKILL.md` (`skills/rf-{browser,selenium,appium,requests,restinstance}/SKILL.md`) SHALL contain these level-2 sections in this order:
1. a short orientation (at most ~5 lines, stating what the library is for and when to prefer a sibling skill);
2. `When to use` (the trigger-terms and sibling-boundary block defined by the `skill-triggering` capability), which is the first level-2 section;
3. `Installation` (the short block defined by the `library-skill-install-guidance` capability);
4. `Import and defaults`;
5. `Which keyword for which situation`;
6. `Agent workflow`;
7. `Gotchas`;
8. `When to read the references`;
9. `Companion Skills`.

Optional sections (for example a locator strategy or a short pattern) MAY appear between `Which keyword for which situation` and `Gotchas`.

#### Scenario: Required sections present and ordered
- **WHEN** the structure test parses the level-2 headings of each of the five library `SKILL.md` files
- **THEN** each file contains every required section heading, and the required headings appear in the order given above

#### Scenario: When to use leads the body
- **WHEN** the level-2 headings of a library `SKILL.md` are parsed
- **THEN** `When to use` is the first level-2 heading and appears within the first 20 body lines, and no other section precedes `Installation`

#### Scenario: Frontmatter unchanged by this capability
- **WHEN** a library `SKILL.md` is restructured
- **THEN** its frontmatter `name` and `description` stay the same (descriptions are owned by the `skill-triggering` capability)
