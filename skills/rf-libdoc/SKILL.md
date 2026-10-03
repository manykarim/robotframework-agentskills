---
name: rf-libdoc
description: "Use first, not memory, for exact Robot Framework keyword names, arguments, docs via libdoc. With robotcode: rf-robotcode."
license: Apache-2.0
compatibility: Requires Python 3.8+ with robotframework>=7 in the environment that runs the bundled script; the libraries to inspect must be importable there.
metadata:
  author: manykarim
  version: "2.0.0"
---

# Robot Framework Libdoc

Find keywords for a use case and explain how to call them, from libdoc data of libraries, resources, suites and spec files. Output is JSON only.

> **robotcode first:** check `robotcode --version` once. If it is on PATH, prefer `robotcode libdoc <Lib> list "*text*"`, `robotcode libdoc <Lib> show "<Keyword>"` or the REPL's `.kw <text>` — quicker, and they use the project's `robot.toml`. See `rf-robotcode`. Use `rf-libdoc` when robotcode is not installed, or when you need a ranked search across several sources or the structured JSON contract below.

## When to use

Load this skill first, instead of answering from memory or grepping files, when a Robot Framework answer depends on an exact keyword name, its arguments or its documentation:

- which keyword does something in an installed library (BuiltIn, Collections, SeleniumLibrary, Browser, RequestsLibrary, ...) or in the project's own .resource files;
- what arguments, types or defaults a keyword takes (its signature);
- `No keyword with name '...' found`, or a wrong-argument-count error.

The bundled libdoc script returns exact names, signatures and docs.

Not this skill: writing whole tests belongs to the library skills (`rf-browser`, `rf-requests`, ...). When the robotcode CLI is installed or the user asks for `robotcode libdoc`, use `rf-robotcode`.

## Which command

Run the bundled script through the project environment so the project's libraries are importable. Script paths are relative to this skill's directory (the folder containing this SKILL.md), not to the project.

| Question | Command | `mode` |
|---|---|---|
| Which keyword does X? | `--search "<use case>"` | `search` |
| How do I call keyword X? | `--keyword "<Keyword>"` | `explain` |
| Not sure of the exact name | `--keyword "<guess>" --search "<use case>"` | `explain`, or `fallback` with suggestions |
| What does library X offer? | no `--keyword` / `--search` | `list` |

Find keywords for a use case (ranked; tune with `--weights`, cap with `--limit`):

```bash
uv run python scripts/rf_libdoc.py --library BuiltIn --library OperatingSystem --search "create temp file" --limit 10 --pretty
uv run python scripts/rf_libdoc.py --library SeleniumLibrary --resource resources/common.resource --search "upload file" --weights name=0.5,short_doc=0.3,doc=0.2 --pretty
```

Explain a keyword's arguments:

```bash
uv run python scripts/rf_libdoc.py --library BuiltIn --keyword "Log" --pretty
```

Explain, falling back to search suggestions if the exact name is not found:

```bash
uv run python scripts/rf_libdoc.py --library SeleniumLibrary --keyword "Open Brows" --search "open browser" --pretty
```

List every keyword of a library:

```bash
uv run python scripts/rf_libdoc.py --library String --pretty
```

Project not managed by uv (no `uv.lock`)? Run with the project's interpreter instead: `.venv/bin/python scripts/rf_libdoc.py …` or `poetry run python scripts/rf_libdoc.py …` (see rf-setup).

## Sources and filters

- Sources: `--library`, `--resource`, `--suite`, `--spec` — each repeatable; inputs are aggregated. `--pythonpath` adds import paths.
- Filters: `--tag` (repeatable), `--include-private`, `--exclude-deprecated`.
- Search scores keyword name, `short_doc` and full `doc`.

## Output contract (stable)

- Every call returns `{schema_version, mode, libraries, results, ...}`; `mode` is `"search"`, `"explain"` (exact keyword found), `"fallback"` (no exact match → search suggestions) or `"list"`.
- `results` is a single array; read it without branching on top-level keys. Each item is `{library, keyword, usage, score, reasons}` — `usage` is set on explain/fallback, `score`/`reasons` on search; fields that do not apply are `null`.
- `usage.params` is `[{name, type, default, kind}]` with `kind ∈ required|optional|vararg|kwarg|named_only` (`name` is the bare parameter, no `: type`); `usage.defaults` is keyed by bare name.
- Payload is bounded: `libraries[]` carries only `{name, type, version, scope, doc_format, short_doc}`. Pass `--include-library-doc` to add each library's full `doc`/`source`.
- Keyword `doc` is capped at 4000 characters by default; a cut doc ends with `[… truncated N chars; rerun with --max-doc-chars 0 for full text]`. `--json-out FILE` writes the full JSON to a file and prints only `{written, bytes, mode}`.
- Exit codes: `0` ok (also no matches, or some sources failed — see `errors` in the JSON and the `warning:` lines), `2` usage, `3` Robot Framework missing or older than 7 in the interpreter, `4` no source could be loaded (the `hint:` lines say which package to `uv add`), `1` internal error (`--debug` for a traceback). Diagnostics are `error:`/`warning:`/`hint:` lines on stderr; stdout is empty on failure.

## Companion Skills

| Need | Skill |
|------|-------|
| Discover, run, debug and statically check with the robotcode CLI | `rf-robotcode` |
| Install Robot Framework or a library, fix the environment | `rf-setup` |
| Analyze output.xml results | `rf-results` (or `rf-robotcode`: `robotcode results`) |
