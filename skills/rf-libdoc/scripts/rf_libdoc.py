#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = ["robotframework>=7"]
# ///
"""Robot Framework libdoc reader for the rf-libdoc skill.

Run it in the project environment so the project's libraries are importable:
``uv run python scripts/rf_libdoc.py --library Browser --search "click"``.

Exit codes: 0 ok (also no matches / partial load failures), 1 internal error,
2 usage, 3 environment (Robot Framework missing or < 7), 4 no source could be
loaded. stdout carries only the JSON result; diagnostics go to stderr as
``error:`` / ``warning:`` / ``hint:`` lines.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import traceback
from typing import Any, Dict, Iterable, List, NoReturn, Tuple

# Robot Framework is imported lazily (see _require_robot) so that --help and
# usage errors work under any interpreter.
libdoc: Any = None

MIN_RF_MAJOR = 7
EXIT_OK, EXIT_INTERNAL, EXIT_USAGE, EXIT_ENV, EXIT_INPUT = 0, 1, 2, 3, 4
DEFAULT_MAX_DOC_CHARS = 4000
SCRIPT_PATH = os.path.abspath(__file__)

# Library import name -> PyPI package to `uv add` when the import fails.
LIBRARY_PACKAGES = {
    "Browser": "robotframework-browser",
    "SeleniumLibrary": "robotframework-seleniumlibrary",
    "AppiumLibrary": "robotframework-appiumlibrary",
    "RequestsLibrary": "robotframework-requests",
    "REST": "RESTinstance",
    "PlatynUI": "robotframework-PlatynUI",
}

ENV_HINTS = (
    f"run it through the project environment: uv run python {SCRIPT_PATH} ...",
    "add Robot Framework to the project: uv add robotframework",
    "not using uv? use the project's interpreter (.venv/bin/python or poetry run python); see the rf-setup skill",
)


class RobotEnvironmentError(RuntimeError):
    """Robot Framework is missing or too old in the running interpreter."""

    def __init__(self, message: str, hints: Iterable[str] = ENV_HINTS) -> None:
        super().__init__(message)
        self.hints = list(hints)


def _fail(code: int, error: str, *hints: str) -> NoReturn:
    """Print ``error:``/``hint:`` lines to stderr and exit with ``code``.

    stdout stays empty on every non-zero exit.
    """
    print(f"error: {error}", file=sys.stderr)
    for hint in hints:
        print(f"hint: {hint}", file=sys.stderr)
    sys.exit(code)


def _warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def _require_robot() -> Any:
    """Import Robot Framework (>= 7) or raise RobotEnvironmentError."""
    global libdoc
    if libdoc is not None:
        return libdoc
    try:
        from robot import libdoc as _libdoc
        from robot.version import VERSION as version
    except ImportError as exc:
        raise RobotEnvironmentError(
            f"Robot Framework is not importable by {sys.executable} ({exc})"
        ) from exc
    try:
        major = int(version.split(".")[0])
    except ValueError:
        major = 0
    if major < MIN_RF_MAJOR:
        raise RobotEnvironmentError(
            f"Robot Framework {version} found in {sys.executable}; "
            f"robotframework>={MIN_RF_MAJOR} is required",
            (
                f"run it through the project environment: uv run python {SCRIPT_PATH} ...",
                "upgrade Robot Framework in the project: uv add \"robotframework>=7\"",
                "not using uv? use the project's interpreter (.venv/bin/python or poetry run python); see the rf-setup skill",
            ),
        )
    libdoc = _libdoc
    return libdoc


def _first_line(text: str) -> str:
    return (text or "").strip().splitlines()[0] if (text or "").strip() else ""


def _source_hint(source: str) -> str:
    package = LIBRARY_PACKAGES.get(source)
    if package:
        return f"add {source} to the project environment: uv add {package} (then re-run with uv run python ...)"
    if source.endswith((".resource", ".robot", ".txt", ".xml", ".json", ".libspec")) or os.sep in source or "/" in source:
        return f"check that the file exists relative to the current directory: {source}"
    return (
        f"make sure {source} is importable in the project environment "
        "(uv add <package>, or --pythonpath for a local library) and run with uv run python ..."
    )


TOKEN_RE = re.compile(r"[a-z0-9]+")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text.lower()).replace("_", "")


def _tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower())


def _token_overlap(query_tokens: List[str], text: str) -> float:
    if not query_tokens:
        return 0.0
    text_tokens = set(_tokenize(text))
    if not text_tokens:
        return 0.0
    matches = sum(1 for t in query_tokens if t in text_tokens)
    return matches / len(query_tokens)


def _parse_weights(raw: str) -> Dict[str, float]:
    weights = {"name": 0.6, "short_doc": 0.25, "doc": 0.15}
    if not raw:
        return weights
    for part in raw.split(","):
        if not part.strip():
            continue
        key, value = part.split("=", 1)
        weights[key.strip()] = float(value.strip())
    total = sum(weights.values())
    if total <= 0:
        return weights
    return {k: v / total for k, v in weights.items()}


def _stringify_args(arg_list: List[Any]) -> List[str]:
    return [str(arg) for arg in (arg_list or [])]


def _split_arg(arg: str) -> Tuple[str, str | None, str | None]:
    """Split a raw libdoc arg string into (name, type, default).

    Handles ``name``, ``name: Type``, ``name=default``, and
    ``name: Type = default``. The ``name`` is returned without any leading
    ``*``/``**`` sigil; ``type`` and ``default`` are ``None`` when absent.
    """
    body = arg
    default: str | None = None
    if "=" in body:
        body, default = body.split("=", 1)
        body = body.strip()
        default = default.strip()
    name = body
    typ: str | None = None
    if ":" in body:
        name, typ = body.split(":", 1)
        name = name.strip()
        typ = typ.strip()
    return name.strip(), typ, default


def _parse_keyword_args(arg_list: List[str]) -> Dict[str, Any]:
    """Structured argument breakdown.

    Each entry in ``params`` is ``{name, type, default, kind}`` with a bare
    parameter name (no ``: type`` annotation). ``kind`` is one of
    ``required``, ``optional``, ``vararg``, ``kwarg``, ``named_only``.
    Arguments that appear after a ``*``/vararg sentinel are keyword-only and
    are tagged ``named_only`` (distinct from ordinary ``optional``).

    ``required``/``optional`` (clean names) and ``defaults`` (keyed by bare
    name) are kept for convenience/back-reference; ``raw`` preserves the
    verbatim libdoc strings.
    """
    params: List[Dict[str, Any]] = []
    required: List[str] = []
    optional: List[str] = []
    varargs: List[str] = []
    kwargs: List[str] = []
    defaults: Dict[str, str] = {}
    seen_star = False  # any *args / bare * → following positionals are keyword-only

    for arg in arg_list:
        if arg.startswith("**"):
            name, typ, _ = _split_arg(arg[2:])
            kwargs.append(name)
            params.append({"name": name, "type": typ, "default": None, "kind": "kwarg"})
            seen_star = True
            continue
        if arg.startswith("*"):
            inner = arg[1:]
            seen_star = True
            if not inner.strip():
                # bare ``*`` sentinel: marks the start of keyword-only args,
                # not a parameter of its own.
                continue
            name, typ, _ = _split_arg(inner)
            varargs.append(name)
            params.append({"name": name, "type": typ, "default": None, "kind": "vararg"})
            continue

        name, typ, default = _split_arg(arg)
        if default is not None:
            kind = "named_only" if seen_star else "optional"
            optional.append(name)
            defaults[name] = default
        else:
            kind = "named_only" if seen_star else "required"
            (optional if seen_star else required).append(name)
        params.append({"name": name, "type": typ, "default": default, "kind": kind})

    return {
        "raw": arg_list,
        "params": params,
        "required": required,
        "optional": optional,
        "varargs": varargs,
        "kwargs": kwargs,
        "defaults": defaults,
    }


def _keyword_to_dict(keyword: Any) -> Dict[str, Any]:
    args = _stringify_args(list(keyword.args or []))
    return {
        "name": keyword.name,
        "args": args,
        "doc": keyword.doc,
        "short_doc": keyword.short_doc,
        "tags": list(keyword.tags or []),
        "deprecated": bool(keyword.deprecated),
        "source": str(keyword.source) if keyword.source is not None else None,
        "lineno": keyword.lineno,
        "private": bool(keyword.private),
    }


def _truncate_doc(doc: str | None, max_chars: int) -> str | None:
    """Cut ``doc`` to about ``max_chars`` at a paragraph or line boundary.

    ``max_chars <= 0`` means unlimited. A truncated doc ends with a marker
    naming the omitted character count and the flag that shows everything.
    """
    if not doc or max_chars <= 0 or len(doc) <= max_chars:
        return doc
    head = doc[:max_chars]
    cut = head.rfind("\n\n")
    if cut < max_chars // 2:
        cut = head.rfind("\n")
    if cut < max_chars // 2:
        cut = max_chars
    kept = doc[:cut].rstrip()
    omitted = len(doc) - len(kept)
    return (
        f"{kept}\n\n[… truncated {omitted} chars; "
        "rerun with --max-doc-chars 0 for full text]"
    )


def _library_meta(lib: Any, include_doc: bool = False) -> Dict[str, Any]:
    """Top-level library metadata.

    The full prose ``doc`` (tens of KB for libraries like Browser) and
    ``source`` are omitted by default — a search/explain response should be
    bounded by the matched keywords, not fixed library overhead. Pass
    ``include_doc=True`` (CLI ``--include-library-doc``) to restore them.
    """
    meta: Dict[str, Any] = {
        "name": lib.name,
        "type": lib.type,
        "version": lib.version,
        "scope": getattr(lib, "scope", None),
        "doc_format": getattr(lib, "doc_format", None),
        "short_doc": getattr(lib, "short_doc", None),
    }
    if include_doc:
        meta["doc"] = lib.doc
        meta["source"] = str(lib.source) if lib.source is not None else None
    return meta


def _library_ref(lib: Any) -> Dict[str, Any]:
    """Minimal per-result library reference — never carries prose ``doc``."""
    return {"name": lib.name, "type": lib.type, "version": lib.version}


def _make_result(lib: Any, keyword: Any, *, usage: Any = None,
                 score: Any = None, reasons: Any = None) -> Dict[str, Any]:
    """One uniform result item. Fields that don't apply to the mode are
    ``None`` (or empty) rather than absent, so consumers never branch on
    shape."""
    return {
        "library": _library_ref(lib),
        "keyword": _keyword_to_dict(keyword),
        "usage": usage,
        "score": score,
        "reasons": reasons,
    }


def _score_keyword(query: str, keyword: Any, weights: Dict[str, float]) -> Tuple[float, List[str]]:
    query = query.strip()
    if not query:
        return 0.0, []
    reasons = []

    normalized_query = _normalize(query)
    normalized_name = _normalize(keyword.name)
    if normalized_query == normalized_name:
        return 1.0, ["exact name match"]

    query_tokens = _tokenize(query)
    name_score = 0.0
    if normalized_query in normalized_name:
        name_score = 0.85
        reasons.append("query substring in name")
    else:
        overlap = _token_overlap(query_tokens, keyword.name)
        if overlap > 0:
            name_score = overlap
            reasons.append("name token match")

    short_doc_score = _token_overlap(query_tokens, keyword.short_doc or "")
    if short_doc_score > 0:
        reasons.append("short_doc token match")

    doc_score = _token_overlap(query_tokens, keyword.doc or "")
    if doc_score > 0:
        reasons.append("doc token match")

    score = (
        weights.get("name", 0.0) * name_score
        + weights.get("short_doc", 0.0) * short_doc_score
        + weights.get("doc", 0.0) * doc_score
    )
    return score, reasons


def _flatten(values: Iterable[List[str]]) -> List[str]:
    out = []
    for group in values:
        out.extend(group)
    return out


def _apply_pythonpath(paths: List[str]) -> None:
    for raw in paths:
        for item in raw.split(os.pathsep):
            if item and item not in sys.path:
                sys.path.insert(0, item)


def _load_docs(libraries: List[str], resources: List[str], suites: List[str], specs: List[str],
               name: str, version: str, doc_format: str,
               errors: List[Dict[str, str]] | None = None) -> List[Any]:
    docs = []
    all_sources = (
        list(libraries) + list(resources) + list(suites) + list(specs)
    )
    _require_robot()
    for src in all_sources:
        try:
            docs.append(libdoc.LibraryDocumentation(src, name=name or None, version=version or None, doc_format=doc_format))
        except Exception as e:
            if errors is not None:
                errors.append({"source": src, "error": str(e)})
    return docs


def _filter_keywords(keywords: List[Any], include_private: bool, exclude_deprecated: bool, tags: List[str]) -> List[Any]:
    filtered = []
    tag_set = {t.lower() for t in tags}
    for kw in keywords:
        if not include_private and getattr(kw, "private", False):
            continue
        if exclude_deprecated and getattr(kw, "deprecated", False):
            continue
        if tag_set:
            kw_tags = {str(t).lower() for t in list(getattr(kw, "tags", []) or [])}
            if not tag_set.issubset(kw_tags):
                continue
        filtered.append(kw)
    return filtered


def _search_keywords(libs: List[Any], query: str, weights: Dict[str, float], limit: int,
                     include_private: bool, exclude_deprecated: bool, tags: List[str]) -> List[Dict[str, Any]]:
    matches = []
    for lib in libs:
        keywords = _filter_keywords(list(lib.keywords or []), include_private, exclude_deprecated, tags)
        for kw in keywords:
            score, reasons = _score_keyword(query, kw, weights)
            if score <= 0:
                continue
            matches.append(_make_result(lib, kw, score=round(score, 4), reasons=reasons))
    matches.sort(key=lambda m: m["score"], reverse=True)
    return matches[:limit]


def _find_keyword(libs: List[Any], keyword_name: str, include_private: bool,
                 exclude_deprecated: bool, tags: List[str]) -> List[Dict[str, Any]]:
    matches = []
    normalized = _normalize(keyword_name)
    for lib in libs:
        keywords = _filter_keywords(list(lib.keywords or []), include_private, exclude_deprecated, tags)
        for kw in keywords:
            if _normalize(kw.name) == normalized:
                usage = _parse_keyword_args(_stringify_args(list(kw.args or [])))
                matches.append(_make_result(lib, kw, usage=usage))
    return matches


EPILOG = """\
examples:
  uv run python scripts/rf_libdoc.py --library BuiltIn --library OperatingSystem --search "create temp file" --limit 10
  uv run python scripts/rf_libdoc.py --library Browser --keyword "Fill Text"
  uv run python scripts/rf_libdoc.py --library SeleniumLibrary --keyword "Open Brows" --search "open browser"
  uv run python scripts/rf_libdoc.py --library String
  uv run python scripts/rf_libdoc.py --library SeleniumLibrary --keyword "Input Text" --max-doc-chars 0 --json-out results/input_text.json

Paths are relative to the rf-libdoc skill directory. Not using uv? Run with the
project's interpreter (.venv/bin/python or poetry run python); see rf-setup.
exit codes: 0 ok (incl. no matches / partial load failures), 1 internal error,
2 usage, 3 environment (robotframework>=7 missing), 4 no source could be loaded.
"""


class _Parser(argparse.ArgumentParser):
    """argparse with ``error:``/``hint:`` stderr lines and exit code 2."""

    def error(self, message: str) -> NoReturn:  # type: ignore[override]
        _fail(EXIT_USAGE, message,
              f"see the options and examples: uv run python {SCRIPT_PATH} --help")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        description="Robot Framework libdoc reader: search keywords, explain a keyword's arguments, "
                    "or list a library's keywords. Prints JSON to stdout.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--library", action="append", default=[], help="Library name (repeatable)")
    parser.add_argument("--resource", action="append", default=[], help="Resource file path (repeatable)")
    parser.add_argument("--suite", action="append", default=[], help="Suite file path (repeatable)")
    parser.add_argument("--spec", action="append", default=[], help="Libdoc spec file path (repeatable)")
    parser.add_argument("--pythonpath", action="append", default=[], help="Extra pythonpath entries")
    parser.add_argument("--keyword", help="Exact keyword name to explain")
    parser.add_argument("--search", help="Search query / use case")
    parser.add_argument("--weights", default="", help="Weights: name=0.6,short_doc=0.25,doc=0.15")
    parser.add_argument("--include-private", action="store_true", help="Include private keywords")
    parser.add_argument("--exclude-deprecated", action="store_true", help="Exclude deprecated keywords")
    parser.add_argument("--tag", action="append", default=[], help="Filter by required tag (repeatable)")
    parser.add_argument("--limit", type=int, default=20, help="Maximum search results (default 20)")
    parser.add_argument(
        "--max-doc-chars",
        type=int,
        default=DEFAULT_MAX_DOC_CHARS,
        help=f"Cap each keyword doc at N characters (default {DEFAULT_MAX_DOC_CHARS}; 0 = unlimited)",
    )
    parser.add_argument("--name", default="", help="Override library name")
    parser.add_argument("--version", default="", help="Override library version")
    parser.add_argument("--doc-format", default=None, help="Doc format (ROBOT/HTML/TEXT)")
    parser.add_argument(
        "--include-library-doc",
        action="store_true",
        help="Include each library's full prose doc/source in libraries[] (off by default).",
    )
    parser.add_argument("--json-out", metavar="FILE",
                        help="Write the JSON result to FILE; stdout gets {written, bytes, mode}")
    parser.add_argument("--pretty", action="store_true", help="Indent the JSON output")
    parser.add_argument("--debug", action="store_true", help="Print a traceback on internal errors")
    return parser


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


SCHEMA_VERSION = 1


def build_response(libs: List[Any], *, keyword: str | None = None, search: str | None = None,
                   weights: Dict[str, float], limit: int = 20,
                   include_private: bool = False, exclude_deprecated: bool = False,
                   tags: List[str] | None = None, include_library_doc: bool = False,
                   load_errors: List[Dict[str, str]] | None = None,
                   max_doc_chars: int = DEFAULT_MAX_DOC_CHARS) -> Dict[str, Any]:
    """Build the unified response: ``{schema_version, mode, libraries, results, ...}``.

    Shared by the CLI and the rf-tools MCP server so both emit one identical
    shape. ``mode`` ∈ ``explain`` | ``fallback`` | ``search`` | ``list``;
    ``results`` is a single array of uniform items.
    """
    tags = tags or []
    data: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "mode": "list",
        "libraries": [_library_meta(lib, include_doc=include_library_doc) for lib in libs],
        "results": [],
    }
    if load_errors:
        data["errors"] = load_errors

    if keyword:
        results = _find_keyword(libs, keyword, include_private, exclude_deprecated, tags)
        if results:
            data["mode"] = "explain"
            data["results"] = results
        else:
            data["mode"] = "fallback"
            data["query"] = search or keyword
            data["results"] = _search_keywords(
                libs, data["query"], weights, limit, include_private, exclude_deprecated, tags
            )
            if not data["results"]:
                data["hint"] = "No keyword matches found. Try a broader search or adjust weights."
    elif search:
        data["mode"] = "search"
        data["query"] = search
        data["results"] = _search_keywords(
            libs, search, weights, limit, include_private, exclude_deprecated, tags
        )
        if not data["results"]:
            data["hint"] = "No keyword matches found. Try a broader search or adjust weights."
    else:
        data["mode"] = "list"
        data["results"] = [
            _make_result(lib, kw)
            for lib in libs
            for kw in _filter_keywords(list(lib.keywords or []), include_private, exclude_deprecated, tags)
        ]
    if max_doc_chars and max_doc_chars > 0:
        for item in data["results"]:
            kw = item.get("keyword") or {}
            kw["doc"] = _truncate_doc(kw.get("doc"), max_doc_chars)
    return data


def emit(data: Dict[str, Any], *, pretty: bool, json_out: str | None, mode: str) -> None:
    """Print ``data`` as JSON, or write it to ``json_out`` and print a summary."""
    text = json.dumps(data, indent=2) if pretty else json.dumps(data, separators=(",", ":"))
    if not json_out:
        print(text)
        return
    parent = os.path.dirname(os.path.abspath(json_out))
    os.makedirs(parent, exist_ok=True)
    payload = (text + "\n").encode("utf-8")
    with open(json_out, "wb") as fh:
        fh.write(payload)
    print(json.dumps({"written": json_out, "bytes": len(payload), "mode": mode}))


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    sources = _flatten([args.library, args.resource, args.suite, args.spec])
    if not sources:
        parser.error("provide at least one of --library, --resource, --suite or --spec")
    if args.limit < 0:
        parser.error("--limit must be >= 0")
    try:
        weights = _parse_weights(args.weights)
    except ValueError:
        parser.error(f"invalid --weights {args.weights!r}; expected e.g. name=0.6,short_doc=0.25,doc=0.15")

    try:
        _require_robot()
    except RobotEnvironmentError as exc:
        _fail(EXIT_ENV, str(exc), *exc.hints)

    if args.pythonpath:
        _apply_pythonpath(args.pythonpath)

    load_errors: List[Dict[str, str]] = []
    libs = _load_docs(args.library, args.resource, args.suite, args.spec, args.name, args.version,
                      args.doc_format, errors=load_errors)
    if not libs:
        for err in load_errors:
            print(f"error: could not load {err['source']}: {_first_line(err['error'])}", file=sys.stderr)
        _fail(
            EXIT_INPUT,
            f"none of the {len(sources)} requested source(s) could be loaded by {sys.executable}",
            *[_source_hint(err["source"]) for err in load_errors],
        )
    for err in load_errors:
        _warn(f"could not load {err['source']}: {_first_line(err['error'])} (details in the JSON 'errors' list)")

    data = build_response(
        libs,
        keyword=args.keyword,
        search=args.search,
        weights=weights,
        limit=args.limit,
        include_private=args.include_private,
        exclude_deprecated=args.exclude_deprecated,
        tags=args.tag,
        include_library_doc=args.include_library_doc,
        load_errors=load_errors,
        max_doc_chars=args.max_doc_chars,
    )
    emit(data, pretty=args.pretty, json_out=args.json_out, mode=data["mode"])
    return EXIT_OK


def main(argv: List[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        code = run(args, parser)
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - exercised via --debug tests
        if args.debug:
            traceback.print_exc(file=sys.stderr)
        _fail(EXIT_INTERNAL, f"internal: {type(exc).__name__}: {exc}",
              "re-run with --debug for a traceback")
    sys.exit(code)


if __name__ == "__main__":
    main()
