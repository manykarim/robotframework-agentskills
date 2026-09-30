# skill-triggering Specification

## Purpose
Makes agents load the right Robot Framework skill, and only that skill, for a user's request. It defines how skill descriptions are written, how sibling skills are told apart, how skills cross-reference each other, and how triggering accuracy is measured and accepted.

## Requirements

### Requirement: Descriptions lead with capability and a "Use when" clause

Every shipped skill's frontmatter `description` SHALL be compact. Claude Code lists skill descriptions only while they fit a character budget that scales with the model's context window: about 8000 characters for 200k-context models, most of it used by bundled skills and skill names. A description is not shown at all once the budget is used up.

Therefore:
- Each `description` MUST be at most 160 characters.
- The combined listing lines of all shipped skills (`- <name>: <description>`) MUST total at most 1700 characters.
- Each description SHALL name Robot Framework (or "RF") and the library, tool or file the skill covers, and SHALL state the user intent it serves.
- It SHALL contain a load cue telling the model to load the skill for that intent, starting with "Use", "Load" or "Use first".
- It MUST NOT use meta-phrasing about the agent ("Guide AI agents", "Helps the AI").
- It MUST NOT name more than 2 keyword or API names.
- It MUST NOT exceed 1024 characters under any circumstances (portability limit).

#### Scenario: Meta-phrasing is rejected
- **WHEN** a skill description starts with "Guide AI agents" or contains "Helps the AI"
- **THEN** the description test fails and names the skill

#### Scenario: Length budget
- **WHEN** a description exceeds 1024 characters
- **THEN** the description test fails regardless of any other rule

#### Scenario: Compact length enforced
- **WHEN** a skill description is 161 characters long
- **THEN** the description test fails and names the skill and its length

#### Scenario: Combined listing fits the default budget
- **WHEN** the listing lines of all shipped skills total more than 1700 characters
- **THEN** the description test fails and reports the total and the three longest descriptions

#### Scenario: Trigger clause present
- **WHEN** each shipped skill's description is read
- **THEN** it names Robot Framework or RF and the skill's library, tool or file, and it contains a load cue starting with "Use", "Load" or "Use first"

#### Scenario: Keyword catalog rejected
- **WHEN** a description names 3 or more keyword or API names
- **THEN** the description test fails and names the skill and the count

### Requirement: Sibling skills state their boundary

Each skill that has a sibling covering a similar task SHALL name that sibling, based on an observable signal, in a "When to use" block within the first 20 lines of its `SKILL.md` body; compact descriptions have no room for it. The block SHALL also list the concrete trigger terms (import lines, file names, CLI names, pasted errors and symptoms) that no longer fit in the description.

The sibling pairs and signals are:
- rf-browser ↔ rf-selenium: the imported library (`Browser` vs `SeleniumLibrary`), or Playwright vs WebDriver/Selenium Grid.
- rf-requests ↔ rf-restinstance: the imported library (`RequestsLibrary` vs `REST`), or JSON Schema/OpenAPI-driven assertions.
- rf-robotcode ↔ rf-results and rf-libdoc: whether the robotcode CLI is installed or named.
- rf-setup ↔ the library skills: installing and fixing the environment vs writing and fixing test code.

#### Scenario: Web siblings reference each other
- **WHEN** the "When to use" blocks of rf-browser and rf-selenium are read
- **THEN** rf-browser names rf-selenium for SeleniumLibrary/WebDriver projects, and rf-selenium names rf-browser for Browser Library/Playwright projects

#### Scenario: API siblings reference each other
- **WHEN** the "When to use" blocks of rf-requests and rf-restinstance are read
- **THEN** each names the other together with the library import that selects it

#### Scenario: Script skills defer to robotcode
- **WHEN** the "When to use" blocks of rf-results and rf-libdoc are read
- **THEN** each says to prefer rf-robotcode when the robotcode CLI is installed, and rf-robotcode's block names rf-results and rf-libdoc as the fallback

#### Scenario: Setup is separated from test writing
- **WHEN** the "When to use" block of rf-setup is read
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

A description change SHALL be measured with the corrected trigger harness (see skill-eval-harness "Trigger detection and scoring") under the **default skill-listing budget** of the evaluation model. That means no listing-budget override, with every compared variant staged together. Each query runs 3 times and counts as triggered at a trigger rate ≥ 0.5. Every comparison uses the same query set, model, harness version and Claude Code version. Results under the enlarged listing budget of 1M-context models (40000 characters) SHALL be reported next to them but do not gate.

**Re-baseline.** Before any description is edited, the current descriptions SHALL be measured on the train and validation splits under the default budget, and stored as the comparison baseline.

**Tuning.**
- Tuning SHALL use the train split only, with all compact candidates staged together, and at most 5 iterations.
- The candidate set kept is the one with the best train score.
- Validation queries and holdout queries MUST NOT be edited, and MUST NOT be used to choose between candidates.
- Train queries that failed MUST NOT be pasted into a description verbatim.

**Acceptance.** A skill's final description SHALL be accepted when, on the validation split:
- (a) should-trigger recall is ≥ 0.80, should-not-trigger accuracy is ≥ 0.90, and neither is lower than the re-baseline; or
- (b) recall is still below 0.80 after tuning, but it improves on the re-baseline recall by at least 0.25, should-not-trigger accuracy is ≥ 0.90 and not lower than the re-baseline, and the shortfall is recorded in the stored trigger baseline and the change's design.

A skill meeting neither (a) nor (b) SHALL still ship a compact description, because the previous description no longer meets the length rules. The result SHALL be recorded as not meeting the target.

**Holdout and cross-model.** After acceptance:
- The holdout split SHALL be run once (3 runs per query) and reported next to the validation result. It does not gate.
- The validation split SHALL be run once on `claude-sonnet-5`, with 1 run per query. It is reported, not gating.

#### Scenario: Below threshold with sufficient improvement is accepted with a recorded shortfall
- **WHEN** the rf-setup compact description reaches validation recall 0.75, where the re-baseline was 0.25, and should-not-trigger accuracy stays 1.00
- **THEN** the description is accepted under rule (b)
- **AND** the stored trigger baseline records rf-setup's shortfall against 0.80

#### Scenario: Below threshold blocks the change
- **WHEN** the rf-requests compact description reaches validation recall 0.50 against a re-baseline of 0.50
- **THEN** it is not accepted under either rule and is recorded as not meeting the target

#### Scenario: No improvement keeps the current description
- **WHEN** the rf-results compact description reaches validation recall 0.25 against a re-baseline of 0.25
- **THEN** the result is recorded as no improvement, and the compact text still ships, because the previous description exceeds the compact length rule

#### Scenario: Regression against the old description blocks the change
- **WHEN** a compact description's should-not-trigger accuracy on validation is lower than the re-baseline for that skill
- **THEN** it is not accepted, and it is revised against the train split

#### Scenario: Validation not used for selection
- **WHEN** two candidate sets are compared during tuning
- **THEN** only their train-split results decide which one is kept

#### Scenario: Pre-change baseline is recorded
- **WHEN** trigger evaluation first runs for this change
- **THEN** results for the current descriptions on both splits are stored, under the default listing budget, before any description is edited

#### Scenario: Enlarged-budget result reported
- **WHEN** the accepted descriptions are measured
- **THEN** the report also shows validation results under a 40000-character listing budget, labelled as the 1M-context condition
