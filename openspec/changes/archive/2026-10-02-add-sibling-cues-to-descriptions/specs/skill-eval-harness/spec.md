## MODIFIED Requirements

### Requirement: Trigger evaluation query sets

Each shipped skill SHALL have a trigger query set containing should-trigger queries and near-miss should-not-trigger queries. Near misses are queries that are plausibly related but belong to another skill or to no skill.

A set SHALL have at least 8 should-trigger and 8 should-not-trigger queries across the `train` and `validation` splits. Each query SHALL be assigned to `train`, `validation`, or a holdout split named `holdout` or `holdout<N>` (for example `holdout2`).

Holdout splits are optional. They SHALL hold queries written after the last description change and are never used to choose or accept a description. A holdout split whose results have been inspected to diagnose failures SHALL be retired: its queries move to `train`, and a new holdout split with fresh queries is added.

Near-miss queries for a skill SHALL include queries that belong to its closest sibling skills (for example Browser vs SeleniumLibrary, RequestsLibrary vs RESTinstance, results analysis vs robotcode).

#### Scenario: Query set validity
- **WHEN** the harness loads a trigger set with fewer than 8 queries of either polarity in train plus validation, a query without a split, a split that is not `train`, `validation`, `holdout` or `holdout<N>`, or a `skill` that names no shipped skill
- **THEN** loading fails with an error naming the set and the problem

#### Scenario: Sibling near misses present
- **WHEN** the trigger set for the Browser skill is loaded
- **THEN** it contains should-not-trigger queries that are SeleniumLibrary tasks

#### Scenario: Holdout split selectable
- **WHEN** `trigger --split holdout` runs on a set that has holdout queries
- **THEN** only the holdout queries run and they are reported in their own column

#### Scenario: Numbered holdout split selectable
- **WHEN** `trigger --split holdout2` runs on a set that has `holdout2` queries
- **THEN** only those queries run and they are reported in their own `holdout2` column
