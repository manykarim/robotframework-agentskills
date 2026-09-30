## Purpose

Makes agents load the right Robot Framework skill, and only that skill, for a user's request. It defines how skill descriptions are written, how sibling skills are told apart, how skills cross-reference each other, and how triggering accuracy is measured and accepted.

## ADDED Requirements

### Requirement: Descriptions lead with capability and a "Use when" clause

Every shipped skill's frontmatter `description` SHALL open with a third-person capability statement that names Robot Framework and the library or tool the skill covers. It SHALL contain a `Use when` clause listing concrete trigger terms: at least one of a library import line or package name, a file name or extension (`.robot`, `.resource`, `output.xml`, `robot.toml`), a CLI name, or an error message the user would paste. It MUST NOT use meta-phrasing about the agent or the skill ("Guide AI agents", "This skill", "Helps the AI"). It MUST be at most 1024 characters and SHOULD be at most 500 characters.

#### Scenario: Meta-phrasing is rejected
- **WHEN** a skill description starts with "Guide AI agents" or contains "This skill"
- **THEN** the description test fails and names the skill

#### Scenario: Trigger clause present
- **WHEN** each shipped skill's description is read
- **THEN** it contains `Use when` and at least one of the listed kinds of trigger terms for that skill

#### Scenario: Length budget
- **WHEN** a description exceeds 1024 characters
- **THEN** the description test fails
- **AND** a description over 500 characters is reported as a warning with its length

### Requirement: Sibling skills state their boundary

Each skill that has a sibling covering a similar task SHALL name that sibling in its description as the skill to use instead, based on an observable signal. The sibling pairs and signals are:
- rf-browser ↔ rf-selenium: the imported library (`Browser` vs `SeleniumLibrary`), or Playwright vs WebDriver/Selenium Grid.
- rf-requests ↔ rf-restinstance: the imported library (`RequestsLibrary` vs `REST`), or JSON Schema/OpenAPI-driven assertions.
- rf-robotcode ↔ rf-results and rf-libdoc: whether the robotcode CLI is installed or named.
- rf-setup ↔ the library skills: installing and fixing the environment vs writing and fixing test code.

#### Scenario: Web siblings reference each other
- **WHEN** the descriptions of rf-browser and rf-selenium are read
- **THEN** rf-browser names rf-selenium for SeleniumLibrary/WebDriver projects, and rf-selenium names rf-browser for Browser Library/Playwright projects

#### Scenario: API siblings reference each other
- **WHEN** the descriptions of rf-requests and rf-restinstance are read
- **THEN** each names the other together with the library import that selects it

#### Scenario: Script skills defer to robotcode
- **WHEN** the descriptions of rf-results and rf-libdoc are read
- **THEN** each says to prefer rf-robotcode when the robotcode CLI is installed, and rf-robotcode's description names rf-results and rf-libdoc as the fallback

#### Scenario: Setup is separated from test writing
- **WHEN** the description of rf-setup is read
- **THEN** it lists installation and environment error triggers and says that writing tests belongs to the library skills

### Requirement: Companion Skills sections are standard and current

Every shipped skill's `SKILL.md` SHALL have a `Companion Skills` section (level-2 heading, matched case-insensitively) with a Markdown table whose first column is `Need` and whose last column is `Skill`. Every skill name in the table MUST be a currently shipped skill and MUST NOT be the skill itself. Each table SHALL have rows for the skill's boundary siblings, for `rf-setup` (except in rf-setup), for keyword lookup (`rf-libdoc`, with the robotcode alternative), and for result analysis (`rf-results`, with the robotcode alternative), using the row wording from the shared catalogue.

#### Scenario: No stale cross-references
- **WHEN** the Companion Skills tables of all shipped skills are parsed
- **THEN** every referenced skill name is the `name` of a skill directory under `skills/`, and none of `rf-keyword-builder`, `rf-testcase-builder`, `rf-resource-architect`, `rf-libdoc-search` or `rf-libdoc-explain` appears

#### Scenario: Siblings are cross-linked
- **WHEN** the rf-browser Companion Skills table is read
- **THEN** it has a row naming `rf-selenium`, and the rf-selenium table has a row naming `rf-browser`

### Requirement: Every shipped skill has a trigger query set

Each shipped skill SHALL have a trigger query set at `eval/triggers/<skill-name>.yaml` in the format accepted by the eval harness. It SHALL contain at least 8 should-trigger and at least 8 should-not-trigger queries, split roughly 60/40 into `train` and `validation` and stratified by polarity. Should-trigger queries SHALL be phrased as users write them, including indirect requests that do not name the library (for example pasted errors or file names). Should-not-trigger queries SHALL be near misses: at least 3 from the skill's boundary siblings and at least 2 non-Robot-Framework look-alikes (for example pytest + Playwright for rf-browser). A query that plausibly belongs to both siblings SHALL NOT be used as a should-not-trigger query for either.

#### Scenario: Set shape
- **WHEN** `eval/triggers/rf-browser.yaml` is loaded
- **THEN** it has ≥ 8 should-trigger and ≥ 8 should-not-trigger queries, each with a split, and the should-not-trigger queries include SeleniumLibrary requests and a pytest-Playwright request

#### Scenario: Every shipped skill is covered
- **WHEN** the set of files in `eval/triggers/` is compared with the shipped skill names
- **THEN** every shipped skill has exactly one trigger set and no trigger set names a retired skill

### Requirement: Descriptions meet trigger-accuracy thresholds

A description change SHALL be accepted only when, on the validation split, with the harness default of 3 runs per query and a query counted as triggered at a trigger rate ≥ 0.5, the skill reaches recall ≥ 0.80 on should-trigger queries and accuracy ≥ 0.90 on should-not-trigger queries, and does not score lower on either than the description it replaces, measured with the same query set, model and harness version. Validation queries MUST NOT be edited to make a description pass. Descriptions are tuned against the train split only.

#### Scenario: Below threshold blocks the change
- **WHEN** a rewritten rf-requests description reaches validation recall 0.67
- **THEN** the description is not accepted and is revised against the train split

#### Scenario: Regression against the old description blocks the change
- **WHEN** a new description's should-not-trigger accuracy on validation is lower than the recorded result of the previous description
- **THEN** the change is not accepted even if the absolute threshold is met

#### Scenario: Pre-change baseline is recorded
- **WHEN** trigger evaluation first runs for this change
- **THEN** results for the old descriptions are recorded before any description is edited, so that later comparisons use the same queries
