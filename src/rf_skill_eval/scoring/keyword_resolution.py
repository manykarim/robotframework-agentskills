"""Static keyword resolution for the ``keywords_resolve`` check (design D8).

Used where a library cannot run on the CI runner (AppiumLibrary without a
device, PlatynUI without a desktop session). The suite is parsed with
``robot.api.get_model``; every keyword call must resolve against:

1. user keywords defined in the suite files and their (recursive) resources,
   embedded arguments included;
2. the libdoc JSON specs passed to the check (committed per fixture under
   ``specs/``), for libraries the suite imports;
3. Robot Framework standard libraries the suite imports (BuiltIn always).

A library import that is neither a standard library nor covered by a spec is
reported as unresolved: the check cannot vouch for its keywords, so it fails.

The approach mirrors ``scripts/check-skill-keywords.py`` (repository QA for
the skills' own examples) but is self-contained: the harness package must not
import repository scripts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

_STANDARD_LIBRARIES = frozenset(
    {
        "BuiltIn",
        "Collections",
        "DateTime",
        "Dialogs",
        "OperatingSystem",
        "Process",
        "Screenshot",
        "String",
        "Telnet",
        "XML",
    }
)
_GHERKIN = re.compile(r"^(given|when|then|and|but)\s+", re.IGNORECASE)


def normalize(name: str) -> str:
    return re.sub(r"[\s_]+", "", name).lower()


@dataclass(frozen=True)
class _KeywordSet:
    plain: frozenset[str]
    embedded: tuple[re.Pattern[str], ...]

    def matches(self, name: str) -> bool:
        if normalize(name) in self.plain:
            return True
        return any(p.fullmatch(name) for p in self.embedded)


def _embedded_pattern(name: str) -> re.Pattern[str] | None:
    if "${" not in name:
        return None
    try:
        from robot.running.arguments.embedded import EmbeddedArguments
    except ImportError:  # pragma: no cover - robot is a harness dependency
        return None
    emb = EmbeddedArguments.from_name(name)
    if emb is None:
        return None
    pattern: re.Pattern[str] = emb.name
    return pattern


def _keyword_set(names: list[str]) -> _KeywordSet:
    plain: set[str] = set()
    embedded: list[re.Pattern[str]] = []
    for n in names:
        pat = _embedded_pattern(n)
        if pat is not None:
            embedded.append(pat)
        else:
            plain.add(normalize(n))
    return _KeywordSet(frozenset(plain), tuple(embedded))


@lru_cache(maxsize=64)
def _libdoc(source: str) -> tuple[str, tuple[str, ...]]:
    """(library name, keyword names) for a spec path or standard library."""
    from robot.libdocpkg import LibraryDocumentation

    doc = LibraryDocumentation(source)
    return str(doc.name), tuple(str(kw.name) for kw in doc.keywords)


@dataclass
class _Parsed:
    calls: list[tuple[str, str]] = field(default_factory=list)  # (keyword, location)
    user_keywords: list[str] = field(default_factory=list)
    libraries: list[str] = field(default_factory=list)
    resource_names: list[str] = field(default_factory=list)
    unresolved_imports: list[str] = field(default_factory=list)


def _make_visitor(path: Path, parsed: _Parsed, resources: list[Path]) -> Any:
    from robot.api.parsing import ModelVisitor

    rel = path.name

    def fixture(self: Any, node: Any) -> None:
        name = getattr(node, "name", None)
        if name and name.upper() != "NONE":
            parsed.calls.append((str(name), f"{rel}:{node.lineno}"))

    class Visitor(ModelVisitor):  # type: ignore[misc]
        visit_SuiteSetup = fixture  # noqa: N815
        visit_SuiteTeardown = fixture  # noqa: N815
        visit_TestSetup = fixture  # noqa: N815
        visit_TestTeardown = fixture  # noqa: N815
        visit_Setup = fixture  # noqa: N815
        visit_Teardown = fixture  # noqa: N815

        def visit_LibraryImport(self, node: Any) -> None:  # noqa: N802
            parsed.libraries.append(str(node.name))

        def visit_ResourceImport(self, node: Any) -> None:  # noqa: N802
            raw = str(node.name).replace("${CURDIR}", str(path.parent))
            candidate = Path(raw) if Path(raw).is_absolute() else path.parent / raw
            if candidate.is_file():
                resources.append(candidate)
                parsed.resource_names.append(candidate.stem)
            else:
                parsed.unresolved_imports.append(f"Resource {node.name} ({rel})")

        def visit_Keyword(self, node: Any) -> None:  # noqa: N802
            parsed.user_keywords.append(str(node.name))
            self.generic_visit(node)

        def visit_KeywordCall(self, node: Any) -> None:  # noqa: N802
            if node.keyword:
                parsed.calls.append((str(node.keyword), f"{rel}:{node.lineno}"))

    return Visitor()


def _visit_file(path: Path, parsed: _Parsed, seen: set[Path]) -> None:
    from robot.api import get_model

    real = path.resolve()
    if real in seen:
        return
    seen.add(real)
    model = get_model(str(path)) if path.suffix == ".robot" else _resource_model(path)
    resources: list[Path] = []
    _make_visitor(path, parsed, resources).visit(model)
    for res in resources:
        _visit_file(res, parsed, seen)


def _resource_model(path: Path) -> Any:
    from robot.api import get_resource_model

    return get_resource_model(str(path))


@dataclass
class ResolutionResult:
    calls: int = 0
    library_calls: int = 0
    unknown: list[str] = field(default_factory=list)
    unresolved_imports: list[str] = field(default_factory=list)
    missing_required: list[str] = field(default_factory=list)
    min_calls: int = 1
    parse_error: str = ""

    @property
    def ok(self) -> bool:
        return (
            not self.parse_error
            and not self.unknown
            and not self.unresolved_imports
            and not self.missing_required
            and self.library_calls >= self.min_calls
        )

    def summary(self) -> str:
        parts = [f"calls={self.calls} library_calls={self.library_calls}"]
        if self.parse_error:
            parts.append(f"parse error: {self.parse_error}")
        if self.missing_required:
            parts.append(f"required library not imported: {self.missing_required}")
        if self.unresolved_imports:
            parts.append(f"unresolved imports: {self.unresolved_imports}")
        if self.unknown:
            parts.append(f"unknown keywords: {self.unknown[:10]}")
        if self.library_calls < self.min_calls:
            parts.append(f"expected >= {self.min_calls} library keyword calls")
        return "; ".join(parts)


def _library_sets(
    imported: list[str], specs: dict[str, tuple[str, ...]], result: ResolutionResult
) -> dict[str, _KeywordSet]:
    sets: dict[str, _KeywordSet] = {}
    for lib in imported:
        if lib in sets:
            continue
        if lib in specs:
            sets[lib] = _keyword_set(list(specs[lib]))
        elif lib in _STANDARD_LIBRARIES:
            sets[lib] = _keyword_set(list(_libdoc(lib)[1]))
        else:
            result.unresolved_imports.append(f"Library {lib} (no libdoc spec given)")
    return sets


def _candidates(raw: str, owners: set[str]) -> list[str]:
    name = _GHERKIN.sub("", raw)
    out = [name]
    if "." in name:
        prefix, _, rest = name.rpartition(".")
        if normalize(prefix) in owners:
            out.append(rest)
    return out


def _resolve_calls(
    parsed: _Parsed, library_sets: dict[str, _KeywordSet], result: ResolutionResult
) -> None:
    user = _keyword_set(parsed.user_keywords)
    owners = {normalize(n) for n in [*library_sets, *parsed.resource_names]}
    for raw, where in parsed.calls:
        if raw.startswith(("${", "@{", "&{")):
            continue  # keyword name held in a variable: not statically resolvable
        result.calls += 1
        candidates = _candidates(raw, owners)
        if any(user.matches(c) for c in candidates):
            continue
        hit = next(
            (lib for lib, ks in library_sets.items() if any(ks.matches(c) for c in candidates)),
            None,
        )
        if hit is None:
            result.unknown.append(f"{raw} ({where})")
        elif hit not in _STANDARD_LIBRARIES:
            result.library_calls += 1


def resolve_suite_keywords(
    suite: Path,
    spec_paths: list[Path],
    *,
    min_calls: int = 1,
    required_libraries: tuple[str, ...] = (),
) -> ResolutionResult:
    """Resolve every keyword call in ``suite`` (a file or a directory)."""
    result = ResolutionResult(min_calls=min_calls)
    files = sorted(p for p in suite.rglob("*.robot") if p.is_file()) if suite.is_dir() else [suite]
    if not files:
        result.parse_error = f"no .robot files under {suite}"
        return result
    parsed = _Parsed()
    seen: set[Path] = set()
    try:
        for f in files:
            _visit_file(f, parsed, seen)
    except Exception as exc:  # robot parser errors are data errors for the agent
        result.parse_error = f"{type(exc).__name__}: {exc}"
        return result
    specs = dict(_libdoc(str(sp)) for sp in spec_paths)
    imported = ["BuiltIn", *parsed.libraries]
    result.missing_required = [r for r in required_libraries if r not in imported]
    library_sets = _library_sets(imported, specs, result)
    result.unresolved_imports.extend(parsed.unresolved_imports)
    _resolve_calls(parsed, library_sets, result)
    return result
