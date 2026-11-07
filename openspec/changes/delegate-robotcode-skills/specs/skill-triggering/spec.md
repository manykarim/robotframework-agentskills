## MODIFIED Requirements

### Requirement: Descriptions lead with capability and a "Use when" clause

Every shipped skill's frontmatter `description` SHALL be compact. Claude Code lists skill descriptions only while they fit a character budget that scales with the model's context window: about 8000 characters for 200k-context models, most of it used by bundled skills and skill names. A description is not shown at all once the budget is used up.

Therefore:
- Each `description` MUST be at most 160 characters.
- The description text of all shipped skills together MUST fit the room measured for rf-* descriptions under the default budget, minus a 5% margin. The room is measured from a real session's skill listing, and the test records it together with the Claude Code version and date of the measurement.
- Each description SHALL name Robot Framework (or "RF") and the library, tool or file the skill covers, and SHALL state the user intent it serves.
- It SHALL contain a load cue telling the model to load the skill for that intent, starting with "Use", "Load" or "Use first".
- A skill for which a trigger evaluation recorded a should-not-trigger load belonging to a sibling skill SHALL carry a short sibling cue naming that sibling and the distinguishing signal (for example "installs/drivers: rf-setup").
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
- **WHEN** the description text of all shipped skills exceeds the recorded room minus 5%
- **THEN** the description test fails and reports the total, the limit, the Claude Code version the room was measured with, and the three longest descriptions

#### Scenario: Trigger clause present
- **WHEN** each shipped skill's description is read
- **THEN** it names Robot Framework or RF and the skill's library, tool or file, and it contains a load cue starting with "Use", "Load" or "Use first"

#### Scenario: Keyword catalog rejected
- **WHEN** a description names 3 or more keyword or API names
- **THEN** the description test fails and names the skill and the count

#### Scenario: Sibling cue present where near-misses were observed
- **WHEN** the descriptions of rf-appium and rf-selenium are read
- **THEN** both name rf-setup for installs and drivers, and no description names a retired skill


### Requirement: Sibling skills state their boundary

Each skill that has a sibling covering a similar task SHALL name that sibling, based on an observable signal, in a "When to use" block within the first 20 lines of its `SKILL.md` body; compact descriptions have no room for it. The block SHALL also list the concrete trigger terms (import lines, file names, CLI names, pasted errors and symptoms) that no longer fit in the description.

The sibling pairs and signals are:
- rf-browser ↔ rf-selenium: the imported library (`Browser` vs `SeleniumLibrary`), or Playwright vs WebDriver/Selenium Grid.
- rf-requests ↔ rf-restinstance: the imported library (`RequestsLibrary` vs `REST`), or JSON Schema/OpenAPI-driven assertions.
- rf-language ↔ the robotcode plugin's `robotcode` skill: writing Robot Framework syntax vs running, discovering, looking up, analysing or debugging with the robotcode CLI. rf-language names the robotcode skill by its plugin, outside its Companion Skills table.
- rf-setup ↔ the library skills: installing and fixing the environment vs writing and fixing test code.

#### Scenario: Web siblings reference each other
- **WHEN** the "When to use" blocks of rf-browser and rf-selenium are read
- **THEN** rf-browser names rf-selenium for SeleniumLibrary/WebDriver projects, and rf-selenium names rf-browser for Browser Library/Playwright projects

#### Scenario: API siblings reference each other
- **WHEN** the "When to use" blocks of rf-requests and rf-restinstance are read
- **THEN** each names the other together with the library import that selects it

#### Scenario: Script skills defer to robotcode
- **WHEN** the "When to use" blocks of all shipped skills are read
- **THEN** none names `rf-results`, `rf-libdoc` or `rf-robotcode` as a sibling or fallback

#### Scenario: Language skill defers CLI work to robotcode
- **WHEN** the "When to use" block of rf-language is read
- **THEN** it says that running, discovering, keyword lookup, result reading and debugging with the robotcode CLI are covered by the robotcode plugin's `robotcode` skill

#### Scenario: Setup is separated from test writing
- **WHEN** the "When to use" block of rf-setup is read
- **THEN** it lists installation and environment error triggers and says that writing tests belongs to the library skills


### Requirement: Companion Skills sections are standard and current

Every shipped skill's `SKILL.md` SHALL have a `Companion Skills` section (level-2 heading, matched case-insensitively) with a Markdown table whose first column is `Need` and whose last column is `Skill`. Every skill name in the table MUST be a currently shipped skill and MUST NOT be the skill itself. Each table SHALL have rows for the skill's boundary siblings, and for `rf-setup` (except in rf-setup), using the row wording from the shared catalogue. Keyword lookup and result analysis SHALL NOT be table rows; the skill SHALL give the `robotcode doc` and `robotcode results` commands in its body and MAY name the robotcode plugin's `robotcode` skill in a sentence after the table.

#### Scenario: No stale cross-references
- **WHEN** the Companion Skills tables of all shipped skills are parsed
- **THEN** every referenced skill name is the `name` of a skill directory under `skills/`, and none of `rf-keyword-builder`, `rf-testcase-builder`, `rf-resource-architect`, `rf-libdoc-search`, `rf-libdoc-explain`, `rf-libdoc`, `rf-results` or `rf-robotcode` appears

#### Scenario: Siblings are cross-linked
- **WHEN** the rf-browser Companion Skills table is read
- **THEN** it has a row naming `rf-selenium`, and the rf-selenium table has a row naming `rf-browser`


### Requirement: Descriptions meet trigger-accuracy thresholds

A description change SHALL be measured with the corrected trigger harness (see skill-eval-harness "Trigger detection and scoring") under the **default skill-listing budget** of the evaluation model. That means no listing-budget override, with every compared variant staged together. Each query runs 3 times and counts as triggered at a trigger rate ≥ 0.5. Every comparison uses the same query set, model, harness version and Claude Code version. Results under the enlarged listing budget of 1M-context models (40000 characters) SHALL be reported next to them but do not gate.

**Re-baseline.** Before any description is edited, the current descriptions SHALL be measured on the train and validation splits under the default budget, and stored as the comparison baseline.

**Tuning.**
- Tuning SHALL use the train split only, with all compact candidates staged together, and at most 5 iterations.
- The candidate set kept is the one with the best train score.
- Validation queries and unretired holdout queries MUST NOT be edited, and MUST NOT be used to choose between candidates.
- Train queries that failed MUST NOT be pasted into a description verbatim.

**Acceptance.** A skill's final description SHALL be accepted when, on the validation split:
- (a) should-trigger recall is ≥ 0.80, should-not-trigger accuracy is ≥ 0.90, and neither is lower than the re-baseline; or
- (b) recall is still below 0.80 after tuning, but it improves on the re-baseline recall by at least 0.25, should-not-trigger accuracy is ≥ 0.90 and not lower than the re-baseline, and the shortfall is recorded in the stored trigger baseline and the change's design.

A skill meeting neither (a) nor (b) SHALL still ship a compact description, because the previous description no longer meets the length rules. The result SHALL be recorded as not meeting the target.

**Near-miss fixes.** A change that adds sibling cues SHALL additionally show both of the following:
- the recorded near-miss queries it targets (moved to the train split) are no longer triggered;
- validation recall of the edited skills and of the named siblings is not lower than the stored trigger baseline.

**Holdout and cross-model.** After acceptance:
- The current holdout split SHALL be run once (3 runs per query) and reported next to the validation result. It does not gate.
- The validation split SHALL be run once on `claude-sonnet-5`, with 1 run per query. It is reported, not gating.

#### Scenario: Below threshold with sufficient improvement is accepted with a recorded shortfall
- **WHEN** the rf-setup compact description reaches validation recall 0.75, where the re-baseline was 0.25, and should-not-trigger accuracy stays 1.00
- **THEN** the description is accepted under rule (b)
- **AND** the stored trigger baseline records rf-setup's shortfall against 0.80

#### Scenario: Below threshold blocks the change
- **WHEN** the rf-requests compact description reaches validation recall 0.50 against a re-baseline of 0.50
- **THEN** it is not accepted under either rule and is recorded as not meeting the target

#### Scenario: No improvement keeps the current description
- **WHEN** the rf-restinstance compact description reaches validation recall 0.25 against a re-baseline of 0.25
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

#### Scenario: Targeted near-miss no longer triggers
- **WHEN** rf-selenium with its sibling cue is measured on the train query "install chromedriver for my SeleniumLibrary tests"
- **THEN** rf-selenium loads in fewer than half of the runs

#### Scenario: Sibling recall protected
- **WHEN** rf-selenium's cue names rf-setup
- **THEN** rf-setup's validation recall is not lower than in the stored trigger baseline


## ADDED Requirements

### Requirement: Trigger accuracy is measured next to the robotcode plugin

The trigger baselines of the nine shipped skills SHALL be re-measured with the robotcode plugin's `robotcode` skill staged in the same session, since users are advised to install both. The re-measurement uses the default listing budget and the same splits and thresholds as "Descriptions meet trigger-accuracy thresholds".

The report SHALL show, per rf-* skill:
- recall and should-not-trigger accuracy, with and without the robotcode skill staged;
- how often the robotcode skill loaded instead.

The query sets SHALL gain near-miss queries that belong to the robotcode skill (run a suite, list tags, summarise a run, look up a keyword's arguments) for `rf-language` and at least two library skills. Those queries SHALL count as correct when the rf-* skill does not load.

#### Scenario: Co-installed measurement reported
- **WHEN** the trigger evaluation runs for this change
- **THEN** the stored baseline has, for each of the nine skills, results with and without the robotcode skill staged, and the robotcode skill's load rate on each skill's should-trigger queries

#### Scenario: robotcode near-miss stays quiet
- **WHEN** the query "list all tests tagged smoke in this project" is run with both plugins staged
- **THEN** `rf-language` loads in fewer than half of the runs

### Requirement: Trigger sets exist only for shipped skills

Trigger query files and baseline entries SHALL exist only for shipped skills. The files and entries for `rf-robotcode`, `rf-libdoc` and `rf-results` SHALL be removed. Queries in the remaining sets that targeted those skills as near-misses SHALL be kept, and re-labelled as robotcode near-misses.

#### Scenario: No trigger file for a retired skill
- **WHEN** `eval/triggers/` is listed
- **THEN** it contains one file per shipped skill and none for `rf-robotcode`, `rf-libdoc` or `rf-results`
