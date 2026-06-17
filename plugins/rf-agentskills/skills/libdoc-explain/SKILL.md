---
name: libdoc-explain
description: Explain Robot Framework keywords and their arguments from library/resource/suite documentation. Use when asked how to use a keyword, what arguments it takes, or to retrieve detailed keyword docs from libdoc across one or more libraries/resources.
---

# Robot Framework Libdoc Explain

Use this skill to retrieve detailed keyword docs and argument usage from Robot Framework libraries/resources/suites. Output JSON only.

## Command

Explain a keyword in standard libraries:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rf_libdoc.py" --library BuiltIn --keyword "Log" --pretty
```

Explain across multiple sources:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rf_libdoc.py" --library SeleniumLibrary --resource resources/common.resource --keyword "Open Browser" --pretty
```

Fallback to search if exact keyword not found:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rf_libdoc.py" --library SeleniumLibrary --keyword "Open Brows" --search "open browser" --pretty
```

## Notes
- Use `--library`, `--resource`, `--suite`, or `--spec` (repeatable). Inputs are aggregated.
- **Output contract (stable):** every call returns `{schema_version, mode, libraries, results, ...}`.
  - `mode` is `"explain"` (exact keyword found), `"fallback"` (no exact match → search suggestions), `"search"`, or `"list"`.
  - `results` is a single array; read it without branching on top-level keys. Each item is `{library, keyword, usage, score, reasons}` — `usage` is populated on explain/fallback, `score`/`reasons` on search; non-applicable fields are `null`.
  - `usage.params` is `[{name, type, default, kind}]` with `kind ∈ required|optional|vararg|kwarg|named_only` (`name` is the bare param, no `: type`); `usage.defaults` is keyed by bare name.
- **Payload is bounded:** library prose `doc` is **not** included by default. Pass `--include-library-doc` to add each library's full `doc`/`source` to `libraries[]`.
- Use `--tag`, `--include-private`, `--exclude-deprecated` as filters.
