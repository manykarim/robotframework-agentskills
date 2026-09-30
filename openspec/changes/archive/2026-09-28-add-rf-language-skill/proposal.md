## Why

After `retire-generator-skills`, nothing in the bundle teaches an agent how to write Robot Framework *code* in `.robot` and `.resource` files: test cases and suites, user keywords, resource files and variables. Agents write it from memory and make mistakes that `robot --dryrun` does not catch (checked on RF 7.1.1 and 7.4.2):
- `Kw  arg =x` silently becomes the positional value `"arg =x"`;
- `Select team ${city} ${team}` binds `city=Los` for "Select team Los Angeles Lakers";
- `${count: int}` passes the dry run on RF 7.1 and fails at run time, and `${count}: int` is invalid on every version;
- `Test Setup` in `__init__.robot` naming a keyword that the child suites do not import fails with "No keyword with name … found";
- copy-pasted tests where a template fits, BDD steps defined with a `Given` prefix, invented `robot:` tags, and legacy `Force Tags`, `[Return]`, `Run Keyword If` and `Set Suite Variable` keep getting written.

Two parallel changes (`add-rf-test-design-skill`, `add-rf-keyword-design-skill`) planned two skills for this, split along the file sections, with a trigger-overlap gate to decide whether to merge them. The user decided to merge them up front (decision 2, 2026-09-27): one skill, `rf-language`, replaces both planned skills and both change folders. Neither was implemented.

## What Changes

- **New guidance skill `rf-language`** at `skills/rf-language/` (directory == `name`, per `align-skill-names-with-spec`). It covers the Robot Framework language as written in `.robot` and `.resource` files:
  - test cases in three styles: keyword-driven, BDD (Given/When/Then with prefix-free step keywords) and data-driven (`Test Template` / `[Template]`, one test per row vs many rows per test, column headers, FOR and embedded-argument templates);
  - suite settings, setup/teardown precedence and failure behaviour, `__init__.robot` rules, suite ordering with `NN__` prefixes;
  - `Test Tags`, `[Tags]  -tag`, tag patterns, reserved `robot:` tags and test selection options;
  - user-keyword anatomy (settings order per Robocop ORD02, naming), every argument form, typed arguments gated to RF ≥ 7.3, embedded arguments (greedy-match trap, quoting, custom patterns, conflicts, BDD step definitions);
  - `RETURN`, `VAR` and scopes, variable priority, control structures inside keywords (and out of test bodies);
  - `.resource` layout, keyword-name conflicts, `robot:private`, and Python/YAML/JSON variable files per environment;
  - a legacy→modern migration table with Robocop 9.x rule IDs;
  - one validation loop (dry run → robocop → targeted real run → results) with the merged list of dry-run blind spots.
- **One `SKILL.md`** (hard limit 500 lines, target ≤ 300) with a single version-gate block, Step 0 via the skill's own `rf_conventions` script, a style decision table, test skeletons, the keyword anatomy, gotchas from both planned skills, the agent workflow, a gated reference table and Companion Skills.
- **Ten references**, merged and de-duplicated: `styles.md`, `templates.md`, `suites-and-init.md`, `tags-and-selection.md`, `arguments.md`, `embedded-arguments.md`, `variables-and-scopes.md`, `control-structures.md`, `resources-and-variable-files.md`, `migration.md`. Each topic has one home. Each reference over 100 lines has a table of contents.
- **Bundled script `scripts/rf_conventions.py`** (deterministic, read-only, `robot.api` parser, JSON `schema: rf-conventions/1`). It detects the project's RF version and feature availability, separator and assignment style, keyword casing, embedded/typed/invalid-typed/private keywords, BDD and template usage, tag settings and vocabulary, duplicate keyword names, legacy constructs with Robocop IDs, resource/variable-file layout and the web library in use. It follows the `skill-script-execution` contract. Step 0 calls the skill's own script, so there is no cross-skill path problem.
- **MCP tool `rf_conventions`** in the plugin's `rf-tools` server, returning the script's JSON, for subagents.
- **rf-setup `references/project-layout.md`** is updated (setup-skill delta, carried over from the keyword-design change): pointer to `rf-language` instead of the retired resource architect, `libraries/` on the python-path, PyYAML for YAML variable files, and plain `robot` ignoring `robot.toml`.
- **Frontmatter** follows `align-skill-names-with-spec` (`license`, `compatibility`, `metadata`) and the `sharpen-skill-descriptions` template. One description (≤ 1024 characters, target about 600) covers test-case styles and keyword/resource/variable design and draws the boundary with `rf-python-library` and the library skills.
- **Examples** in `assets/examples/` are dry-runnable and labelled "RF 7.0+" (user decision 5: no RF 6.1-compatible rewrites); the typed-argument example is labelled "RF 7.3+".
- **Eval assets** in the `strengthen-skill-eval-harness` format:
  - five narrow tasks (data-driven conversion, BDD scenarios, smoke tags plus suite setup, the "Los Angeles Lakers" embedded-argument task, per-environment YAML variable files) and two adversarial tasks (`Force Tags` requested; typed `int` argument requested on an RF 7.1-pinned project), all with objective graders;
  - fixtures `sut-language-tests`, `sut-language-keywords` and `sut-rf71`;
  - hidden grader suites plus a custom grader module;
  - optional `args` and `expected_tests` on the harness `robot_pass` / `robot_dryrun` checks, if the harness does not have them yet;
  - one trigger set `eval/triggers/rf-language.yaml` with ≥ 10 should-trigger and ≥ 10 should-not-trigger queries.
- **Distribution and cross-references**: sync to plugin, VS Code and installer assets; a `language` Companion Skills catalogue row added to rf-setup, rf-robotcode and the six library skills; the context-injection hook skill list; the subagents `rf-test-architect`, `rf-keyword-consultant` and `rf-migration-guide` (routing text owned by `modernize-plugin-agents-and-hooks`); README; CHANGELOG entries under the release cycle's single unreleased version.
- **Removed plans**: the change folders `add-rf-test-design-skill` and `add-rf-keyword-design-skill` are deleted. Their skills `rf-test-design` and `rf-keyword-design` are never shipped.

## Capabilities

### New Capabilities
- `language-skill`: the `rf-language` agent skill for writing and reviewing Robot Framework test cases, suites, user keywords, resource files and variables. It defines the required content (styles, templates, setup/teardown, tags and selection, `__init__.robot` rules, keyword anatomy, arguments, embedded arguments, variables, control structures, resources and variable files, migration table), the gotchas, the version gate, the validation loop, the `rf_conventions` script and MCP tool, the boundaries with sibling skills, the eval tasks and trigger set, and distribution to every channel.

### Modified Capabilities
- `setup-skill`: the project-layout reference points to `rf-language` for keyword, resource-file and variable-file design, marks `libraries/` on the python-path for project keyword libraries, states that YAML variable files need PyYAML, and states that plain `robot` ignores `robot.toml`.

## Impact

- **New**:
  - `skills/rf-language/`: `SKILL.md`, 10 references, `assets/examples/`, `scripts/rf_conventions.py`;
  - `tests/test_language_skill.py`, `tests/test_rf_conventions.py`, fixtures under `tests/fixtures/language/`;
  - `eval/fixtures/{sut-language-tests,sut-language-keywords,sut-rf71}/`, `eval/graders/language/`, `src/rf_skill_eval/scoring/custom/language.py`;
  - 7 task YAMLs and `eval/triggers/rf-language.yaml`.
- **Edited**:
  - `skills/rf-setup/references/project-layout.md` and the Companion Skills tables of rf-setup, rf-robotcode, rf-browser, rf-selenium, rf-appium, rf-requests, rf-restinstance and rf-platynui (one row each);
  - `plugins/rf-agentskills/servers/rf-tools-server.py` (new tool) and its tests;
  - `plugins/rf-agentskills/scripts/maybe_inject_rf_context.mjs` (skill list) and `tests/test_hook_scripts.py`;
  - `plugins/rf-agentskills/agents/{rf-test-architect,rf-keyword-consultant,rf-migration-guide}.md` (only the skill id, if `modernize-plugin-agents-and-hooks` has not rewritten them yet);
  - `src/rf_skill_eval/scoring/deterministic.py` (`args` / `expected_tests`, if missing);
  - `README.md`, `installer/CHANGELOG.md`, `vscode-extension/CHANGELOG.md`.
- **Generated by sync**: `plugins/rf-agentskills/skills/rf-language/` (with its own `scripts/`), `vscode-extension/skills/rf-language/`, `vscode-extension/package.json` `chatSkills`, installer `_assets/`.
- **Dependencies**: runtime `robotframework>=7` in the project environment for the script; robocop optional. Dev/CI: `robotframework-robocop>=9.1,<10` (fail-soft) for the rule-ID test, `uv` for the RF 7.1.1 parity test and grader, `pyyaml` in the eval environment.
- **Ordering**: after `retire-generator-skills`, `merge-libdoc-skills`, `align-skill-names-with-spec`, `harden-skill-script-execution`, `strengthen-skill-eval-harness`, `sharpen-skill-descriptions` and `restructure-library-skills`; before `add-rf-python-library-skill` and `modernize-plugin-agents-and-hooks`, which route to `rf-language`.
