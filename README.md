# Agent Skills for Robot Framework

This repo packages Agent Skills that help create and analyze Robot Framework assets (keywords, tests, resources, and results). It also contains example scripts that can be used by agents or humans.

## What is an Agent Skill?

Agent Skills are modular, self-contained packages that include a `SKILL.md` file (instructions) plus optional scripts/resources/assets. Agents load a skill when its name/description matches the user request. Skills are designed for progressive disclosure: only metadata is always available; the full skill body and resources are loaded only when needed.

## Where skills live

This repo keeps skills under the `skills/` directory. Each skill has its own folder with a `SKILL.md` and optional `scripts/`, `references/`, and `assets/` subfolders. 

Common layout:

```
skills/
  <skill-name>/
    SKILL.md
    scripts/
    references/
    assets/
```

## Available skills

- `robotframework-results` – read Robot Framework `output.xml` and produce JSON summaries, details, errors, and timing.
- `robotframework-libdoc-search` – search library/resource keywords by use case via libdoc.
- `robotframework-libdoc-explain` – explain a keyword and its arguments via libdoc.
- `robotframework-keyword-builder` – generate user keywords from structured input.
- `robotframework-testcase-builder` – generate test cases from structured input.
- `robotframework-resource-architect` – propose resource/variable structure and optionally write files.

## Usage pattern

Most skills here are operated via their bundled scripts. Each script takes JSON input and returns JSON output, so it can be called by an agent or from the CLI.

Examples:

```bash
# Keyword builder
python skills/robotframework-keyword-builder/scripts/keyword_builder.py --input keyword.json

# Test case builder
python skills/robotframework-testcase-builder/scripts/testcase_builder.py --input tests.json

# Resource architect
python skills/robotframework-resource-architect/scripts/resource_architect.py --input plan.json --write

# Results reader
python skills/robotframework-results/scripts/rf_results.py --output output.xml --sections summary,details

# Libdoc search
python skills/robotframework-libdoc-search/scripts/rf_libdoc.py --library BuiltIn --search "create file" --pretty
```

## Notes on compatibility

- These skills target Robot Framework 7+.
- For YAML variable files, install `pyyaml` in the active virtual environment.
- When merging multiple `output.xml` files, rebot `--merge` only works if root suite names match; otherwise the results are combined under a new top-level suite. 

## Cross-agent compatibility

Agent Skills are an open standard supported by multiple agent systems. GitHub Copilot recognizes skills from project folders (for example `.github/skills` or `.claude/skills`) and from user-level folders. You can relocate or copy `skills/` to a supported location if needed. 

## Adding new skills

1) Create a new folder under `skills/` with a `SKILL.md` file.
2) Add scripts/resources/assets as needed.
3) Keep `SKILL.md` concise and link to references for large details.

## References

- Anthropic Agent Skills overview
- GitHub Copilot Agent Skills overview