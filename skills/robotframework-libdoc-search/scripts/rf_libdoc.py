#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Tuple

try:
    from robot import libdoc
except ImportError:
    print('{"error": "robotframework package required. Install with: pip install robotframework"}', file=sys.stderr)
    sys.exit(1)


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Robot Framework libdoc reader")
    parser.add_argument("--library", action="append", default=[], help="Library name (repeatable)")
    parser.add_argument("--resource", action="append", default=[], help="Resource file path (repeatable)")
    parser.add_argument("--suite", action="append", default=[], help="Suite file path (repeatable)")
    parser.add_argument("--spec", action="append", default=[], help="Libdoc spec file path (repeatable)")
    parser.add_argument("--pythonpath", action="append", default=[], help="Extra pythonpath entries")
    parser.add_argument("--keyword", help="Exact keyword name to explain")
    parser.add_argument("--search", help="Search query / use case")
    parser.add_argument("--weights", default="", help="Weights: name=0.6,short_doc=0.25,doc=0.15")
    parser.add_argument("--include-private", action="store_true")
    parser.add_argument("--exclude-deprecated", action="store_true")
    parser.add_argument("--tag", action="append", default=[], help="Filter by required tag (repeatable)")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--name", default="", help="Override library name")
    parser.add_argument("--version", default="", help="Override library version")
    parser.add_argument("--doc-format", default=None, help="Doc format (ROBOT/HTML/TEXT)")
    parser.add_argument(
        "--include-library-doc",
        action="store_true",
        help="Include each library's full prose doc/source in libraries[] (off by default).",
    )
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


SCHEMA_VERSION = 1


def build_response(libs: List[Any], *, keyword: str | None = None, search: str | None = None,
                   weights: Dict[str, float], limit: int = 20,
                   include_private: bool = False, exclude_deprecated: bool = False,
                   tags: List[str] | None = None, include_library_doc: bool = False,
                   load_errors: List[Dict[str, str]] | None = None) -> Dict[str, Any]:
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
    return data


def main() -> None:
    args = parse_args()

    sources = _flatten([args.library, args.resource, args.suite, args.spec])
    if not sources:
        raise SystemExit("Provide --library, --resource, --suite, or --spec")

    if args.pythonpath:
        _apply_pythonpath(args.pythonpath)

    load_errors: List[Dict[str, str]] = []
    libs = _load_docs(args.library, args.resource, args.suite, args.spec, args.name, args.version, args.doc_format, errors=load_errors)
    weights = _parse_weights(args.weights)

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
    )

    if args.pretty:
        print(json.dumps(data, indent=2))
    else:
        print(json.dumps(data, separators=(",", ":")))


if __name__ == "__main__":
    main()
