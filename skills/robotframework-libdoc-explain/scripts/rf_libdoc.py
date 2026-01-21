#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from typing import Any, Dict, Iterable, List, Tuple

from robot import libdoc


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


def _parse_keyword_args(arg_list: List[str]) -> Dict[str, Any]:
    required = []
    optional = []
    varargs = []
    kwargs = []
    defaults: Dict[str, str] = {}

    for arg in arg_list:
        if arg.startswith("**"):
            kwargs.append(arg[2:])
            continue
        if arg.startswith("*"):
            varargs.append(arg[1:])
            continue
        if "=" in arg:
            name, default = arg.split("=", 1)
            name = name.strip()
            default = default.strip()
            optional.append(name)
            defaults[name] = default
            continue
        required.append(arg.strip())

    return {
        "raw": arg_list,
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


def _library_meta(lib: Any) -> Dict[str, Any]:
    return {
        "name": lib.name,
        "type": lib.type,
        "version": lib.version,
        "doc": lib.doc,
        "source": str(lib.source) if lib.source is not None else None,
        "scope": getattr(lib, "scope", None),
        "doc_format": getattr(lib, "doc_format", None),
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
               name: str, version: str, doc_format: str) -> List[Any]:
    docs = []
    for lib in libraries:
        docs.append(libdoc.LibraryDocumentation(lib, name=name or None, version=version or None, doc_format=doc_format))
    for resource in resources:
        docs.append(libdoc.LibraryDocumentation(resource, name=name or None, version=version or None, doc_format=doc_format))
    for suite in suites:
        docs.append(libdoc.LibraryDocumentation(suite, name=name or None, version=version or None, doc_format=doc_format))
    for spec in specs:
        docs.append(libdoc.LibraryDocumentation(spec, name=name or None, version=version or None, doc_format=doc_format))
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
            matches.append(
                {
                    "library": {"name": lib.name, "type": lib.type},
                    "keyword": _keyword_to_dict(kw),
                    "score": round(score, 4),
                    "reasons": reasons,
                }
            )
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
                matches.append({
                    "library": _library_meta(lib),
                    "keyword": _keyword_to_dict(kw),
            "usage": _parse_keyword_args(_stringify_args(list(kw.args or []))),
                })
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
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    sources = _flatten([args.library, args.resource, args.suite, args.spec])
    if not sources:
        raise SystemExit("Provide --library, --resource, --suite, or --spec")

    if args.pythonpath:
        _apply_pythonpath(args.pythonpath)

    libs = _load_docs(args.library, args.resource, args.suite, args.spec, args.name, args.version, args.doc_format)
    weights = _parse_weights(args.weights)

    data: Dict[str, Any] = {
        "libraries": [_library_meta(lib) for lib in libs],
    }

    if args.keyword:
        matches = _find_keyword(libs, args.keyword, args.include_private, args.exclude_deprecated, args.tag)
        if matches:
            data["keyword_matches"] = matches
        else:
            query = args.search or args.keyword
            data["matches"] = _search_keywords(
                libs,
                query,
                weights,
                args.limit,
                args.include_private,
                args.exclude_deprecated,
                args.tag,
            )
            if not data["matches"]:
                data["hint"] = "No keyword matches found. Try a broader search or adjust weights."
    elif args.search:
        data["query"] = args.search
        data["matches"] = _search_keywords(
            libs,
            args.search,
            weights,
            args.limit,
            args.include_private,
            args.exclude_deprecated,
            args.tag,
        )
        if not data["matches"]:
            data["hint"] = "No keyword matches found. Try a broader search or adjust weights."
    else:
        data["keywords"] = [
            _keyword_to_dict(kw)
            for lib in libs
            for kw in _filter_keywords(list(lib.keywords or []), args.include_private, args.exclude_deprecated, args.tag)
        ]

    if args.pretty:
        print(json.dumps(data, indent=2))
    else:
        print(json.dumps(data, separators=(",", ":")))


if __name__ == "__main__":
    main()
