#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = ["robotframework>=7"]
# ///
"""Robot Framework project convention detector for the rf-language skill.

Scans the ``.robot`` and ``.resource`` files under a project directory with the
Robot Framework parser (``robot.api``) and prints one JSON object
(``schema: rf-conventions/1``) describing the conventions new code should
follow: the Robot Framework version and which version-gated features it
supports, separator and assignment style, keyword naming, embedded and typed
arguments, BDD and template usage, tags, legacy constructs (with Robocop rule
ids), resource and variable-file layout and the web library in use.

Run it in the project environment:
``uv run python scripts/rf_conventions.py <project-dir>``.

The script is read-only: it never writes to the project, never imports the
project's libraries and never executes project code.

Top-level keys (always present; undeterminable values are ``null``):
``schema, root, rf, scan, style, keywords, calls, tests, variables, legacy,
layout, libraries, advice``.

``rf.features`` keys (``{min, available}``; ``available`` is ``null`` when the
effective version is unknown): return_statement (5.0); test_tags,
keyword_tags, robot_private (6.0); parseinclude, suite_name_setting,
json_variable_files, mixed_embedded_args (6.1); var_statement, tag_removal,
test_full_name (7.0); scope_suites, bdd_embedded_prefix (7.1); group,
embedded_pattern_flags, template_skip_rows (7.2); typed_arguments (7.3);
secret_type (7.4).

Exit codes: 0 ok (also for a directory without Robot Framework files), 1
internal error, 2 usage, 3 environment (Robot Framework missing or < 7), 4
path missing or not a directory. stdout carries only the JSON result;
diagnostics go to stderr as ``error:`` / ``warning:`` / ``hint:`` lines.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import traceback
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterator, List, NoReturn, Optional, Tuple

# Robot Framework is optional at import time so that --help and usage errors
# work under any interpreter; _require_robot() enforces it after parsing.
try:
    from robot.version import VERSION as _RF_VERSION
except ImportError:  # pragma: no cover - exercised via a bare venv
    _RF_VERSION = None
try:
    from robot.api import Token, get_init_model, get_model, get_resource_model
    from robot.api.parsing import ModelVisitor
    _RF_IMPORT_ERROR: Exception | None = None
except ImportError as _exc:  # pragma: no cover - exercised via a bare venv or an old RF
    Token = None
    get_model = get_resource_model = get_init_model = None
    ModelVisitor = object
    _RF_IMPORT_ERROR = _exc

SCHEMA = "rf-conventions/1"
MIN_RF_MAJOR = 7
EXIT_OK, EXIT_INTERNAL, EXIT_USAGE, EXIT_ENV, EXIT_INPUT = 0, 1, 2, 3, 4
DEFAULT_MAX_FILES = 2000
DEFAULT_MAX_EXAMPLES = 3
SCRIPT_PATH = os.path.abspath(__file__)

SKIP_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", "results", "output",
    "__pycache__", ".robotcode_cache", ".robocop_cache", ".tox", ".nox", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", "pabot_results", "dist", "build", "site-packages",
}
RESOURCE_DIR_CANDIDATES = ("resources", "keywords", "res")
VARIABLE_DIRS = ("variables", "resources/variables", "vars")
VARFILE_EXT = (".py", ".yaml", ".yml", ".json")
BDD = re.compile(r"^(given|when|then|and|but)\s", re.I)
CONTROL_NODES = ("For", "While", "If", "Try")
WEB_LIBRARIES = {"Browser": "rf-browser", "SeleniumLibrary": "rf-selenium"}

#: Version gate: (feature key, minimum version). Mirrors the SKILL.md table.
FEATURES: List[Tuple[str, Tuple[int, int]]] = [
    ("return_statement", (5, 0)),
    ("test_tags", (6, 0)),
    ("keyword_tags", (6, 0)),
    ("robot_private", (6, 0)),
    ("parseinclude", (6, 1)),
    ("suite_name_setting", (6, 1)),
    ("json_variable_files", (6, 1)),
    ("mixed_embedded_args", (6, 1)),
    ("var_statement", (7, 0)),
    ("tag_removal", (7, 0)),
    ("test_full_name", (7, 0)),
    ("scope_suites", (7, 1)),
    ("bdd_embedded_prefix", (7, 1)),
    ("group", (7, 2)),
    ("embedded_pattern_flags", (7, 2)),
    ("template_skip_rows", (7, 2)),
    ("typed_arguments", (7, 3)),
    ("secret_type", (7, 4)),
]

#: Legacy keyword calls: normalized name -> (construct, Robocop 9.x rule id or None).
LEGACY_KEYWORDS: Dict[str, Tuple[str, Optional[str]]] = {
    "runkeywordif": ("Run Keyword If", "DEPR08"),
    "runkeywordunless": ("Run Keyword Unless", "DEPR08"),
    "setvariable": ("Set Variable", "DEPR05"),
    "settestvariable": ("Set Test Variable", "DEPR05"),
    "setsuitevariable": ("Set Suite Variable", "DEPR05"),
    "setglobalvariable": ("Set Global Variable", "DEPR05"),
    "setlocalvariable": ("Set Local Variable", "DEPR05"),
    "createlist": ("Create List", "DEPR06"),
    "createdictionary": ("Create Dictionary", "DEPR06"),
    "exitforloop": ("Exit For Loop", "DEPR09"),
    "exitforloopif": ("Exit For Loop If", "DEPR09"),
    "continueforloop": ("Continue For Loop", "DEPR09"),
    "continueforloopif": ("Continue For Loop If", "DEPR09"),
    "returnfromkeyword": ("Return From Keyword", "DEPR10"),
    "returnfromkeywordif": ("Return From Keyword If", "DEPR10"),
    # Modern forms exist but Robocop 9.1 does not flag these.
    "catenate": ("Catenate", None),
    "setvariableif": ("Set Variable If", None),
}
LEGACY_OTHER = {
    "[Return]": "DEPR11",
    "Force Tags": "DEPR07",
    "Default Tags": None,
    "WITH NAME": "DEPR03",
    "singular section header": "DEPR04",
}
SINGULAR_HEADERS = {"setting", "variable", "test case", "task", "keyword", "comment"}

INPUT_HINT = (
    "pass the project root (the directory holding tests/ and resources/), for example: "
    "uv run python scripts/rf_conventions.py ."
)


class RobotEnvironmentError(RuntimeError):
    """Robot Framework is missing or too old in the running interpreter."""

    def __init__(self, message: str, hints: List[str]) -> None:
        super().__init__(message)
        self.hints = list(hints)


class InputError(RuntimeError):
    """The path to scan does not exist or is not a directory."""

    def __init__(self, message: str, hint: str = INPUT_HINT) -> None:
        super().__init__(message)
        self.hint = hint


def _fail(code: int, error: str, *hints: str) -> NoReturn:
    print(f"error: {error}", file=sys.stderr)
    for hint in hints:
        print(f"hint: {hint}", file=sys.stderr)
    sys.exit(code)


def _warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def _require_robot() -> None:
    """Raise RobotEnvironmentError unless Robot Framework >= 7 is importable."""
    fallback = (
        "not using uv? use the project's interpreter (.venv/bin/python or poetry run python); "
        "see the rf-setup skill"
    )
    try:
        major = int(str(_RF_VERSION).split(".")[0]) if _RF_VERSION else None
    except ValueError:
        major = 0
    if (_RF_IMPORT_ERROR is not None or _RF_VERSION is None) and (major is None or major >= MIN_RF_MAJOR):
        raise RobotEnvironmentError(
            f"Robot Framework is not importable by {sys.executable} ({_RF_IMPORT_ERROR})",
            [
                f"run it through the project environment: uv run python {SCRIPT_PATH} ...",
                "add Robot Framework to the project: uv add robotframework",
                fallback,
            ],
        )
    if major is None or major < MIN_RF_MAJOR:
        raise RobotEnvironmentError(
            f"Robot Framework {_RF_VERSION} found in {sys.executable}; "
            f"robotframework>={MIN_RF_MAJOR} is required",
            [
                f"run it through the project environment: uv run python {SCRIPT_PATH} ...",
                'upgrade Robot Framework in the project: uv add "robotframework>=7"',
                fallback,
            ],
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _norm(name: str) -> str:
    return re.sub(r"[\s_]", "", name).lower()


def _vtuple(version: Optional[str]) -> Optional[Tuple[int, int, int]]:
    if not version:
        return None
    m = re.match(r"(\d+)\.(\d+)(?:\.(\d+))?", version)
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3) or 0))


def _embedded_args(name: str) -> List[str]:
    """Contents of every ``${...}`` in ``name`` (brace-balanced)."""
    out: List[str] = []
    i = 0
    while True:
        start = name.find("${", i)
        if start < 0:
            return out
        depth, j = 1, start + 2
        while j < len(name) and depth:
            if name[j] == "\\":
                j += 2
                continue
            if name[j] == "{":
                depth += 1
            elif name[j] == "}":
                depth -= 1
            j += 1
        out.append(name[start + 2:j - 1])
        i = j


def _strip_embedded(name: str) -> str:
    for arg in _embedded_args(name):
        name = name.replace("${" + arg + "}", "${}", 1)
    return name


def _embedded_kind(arg: str) -> Tuple[bool, bool]:
    """(typed, custom pattern) for the content of one embedded argument."""
    m = re.match(r"^[^:]*", arg)
    rest = arg[m.end():] if m else ""
    typed = rest.startswith(": ")
    if typed:
        tm = re.match(r"^: [^:]+", rest)
        rest = rest[tm.end():] if tm else ""
    return typed, rest.startswith(":")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _dist_version(metadata: Path) -> Optional[str]:
    name = version = None
    for line in _read(metadata).splitlines():
        if line.startswith("Name:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("Version:"):
            version = line.split(":", 1)[1].strip()
        elif not line.strip():
            break
    if name and _norm(name.replace("-", "")) == "robotframework":
        return version
    return None


def _project_env_version(root: Path) -> Optional[str]:
    venv = root / ".venv"
    if not venv.is_dir():
        return None
    candidates = sorted(venv.glob("lib/python*/site-packages/robotframework-*.dist-info/METADATA"))
    candidates += sorted(venv.glob("Lib/site-packages/robotframework-*.dist-info/METADATA"))
    for metadata in candidates:
        version = _dist_version(metadata)
        if version:
            return version
    return None


def _locked_version(root: Path) -> Optional[str]:
    for lock in ("uv.lock", "poetry.lock"):
        text = _read(root / lock) if (root / lock).is_file() else ""
        m = re.search(r'name = "robotframework"\s*\nversion = "([^"]+)"', text)
        if m:
            return m.group(1)
    return None


def _declared_version(root: Path) -> Optional[str]:
    for fname in ("pyproject.toml", "requirements.txt", "requirements-dev.txt"):
        path = root / fname
        if not path.is_file():
            continue
        m = re.search(
            r"""(?:^|["'\s])robotframework\s*(?:\[[^\]]*\])?\s*((?:[<>=!~]=?\s*[\w.*]+\s*,?\s*)+)""",
            _read(path),
            re.M,
        )
        if m:
            return m.group(1).strip().rstrip(",").strip()
    return None


def _iter_files(root: Path, max_files: int, state: Dict[str, bool]) -> Iterator[Path]:
    count = 0
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith("."))
        for fname in sorted(files):
            if fname.endswith((".robot", ".resource")):
                if count >= max_files:
                    state["truncated"] = True
                    return
                count += 1
                yield Path(dirpath) / fname


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


class _Stats:
    def __init__(self, max_examples: int) -> None:
        self.max_examples = max_examples
        self.c: Counter = Counter()
        self.sep: Counter = Counter()
        self.assign: Counter = Counter()
        self.legacy: Counter = Counter()
        self.legacy_ids: Dict[str, Optional[str]] = {}
        self.libs: Counter = Counter()
        self.kw_defs: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        self.examples: Dict[str, List[str]] = defaultdict(list)
        self.res_dirs: Counter = Counter()
        self.var_imports: Counter = Counter()
        self.tags: Counter = Counter()
        self.parse_errors: List[Dict[str, str]] = []

    def example(self, key: str, value: str) -> None:
        if len(self.examples[key]) < self.max_examples:
            self.examples[key].append(value)

    def add_legacy(self, construct: str, rule: Optional[str]) -> None:
        self.legacy[construct] += 1
        self.legacy_ids[construct] = rule


def _values(node: Any) -> List[str]:
    return [t.value for t in node.tokens if t.type == Token.ARGUMENT]


def _make_visitor(stats: _Stats, rel: str, is_resource: bool, pipe_file: bool) -> Any:
    class Visitor(ModelVisitor):  # type: ignore[misc,valid-type]
        def __init__(self) -> None:
            self.in_body = False
            self.in_test = False
            self.file_private = False
            self.suite_template = False

        def generic_visit(self, node: Any) -> None:
            tokens = getattr(node, "tokens", None)
            if tokens is not None and type(node).__name__ not in ("TestCaseName", "KeywordName"):
                prev_data = False
                for tok in tokens:
                    if tok.type == Token.EOL:
                        prev_data = False
                    elif tok.type == Token.SEPARATOR:
                        if self.in_body and prev_data and not pipe_file:
                            stats.sep["tab" if "\t" in tok.value else str(len(tok.value))] += 1
                    else:
                        prev_data = True
                    if tok.type in (Token.ERROR, Token.FATAL_ERROR):
                        stats.c["syntax_errors"] += 1
            super().generic_visit(node)

        # -- settings -----------------------------------------------------
        def visit_SectionHeader(self, node: Any) -> None:
            data = node.data_tokens
            if data:
                name = data[0].value.strip("* ").lower()
                if name in SINGULAR_HEADERS:
                    stats.add_legacy("singular section header", LEGACY_OTHER["singular section header"])
            self.generic_visit(node)

        def visit_LibraryImport(self, node: Any) -> None:
            if node.name:
                stats.libs[node.name] += 1
            if any(t.value.upper() == "WITH NAME" for t in node.tokens):
                stats.add_legacy("WITH NAME", LEGACY_OTHER["WITH NAME"])
            self.generic_visit(node)

        def visit_VariablesImport(self, node: Any) -> None:
            suffix = Path(node.name or "").suffix.lower().lstrip(".")
            kind = {"yml": "yaml"}.get(suffix, suffix) or "module"
            stats.var_imports[kind] += 1
            self.generic_visit(node)

        def visit_TestTags(self, node: Any) -> None:
            setting = node.tokens[0].value if node.tokens else ""
            if _norm(setting).startswith("force"):
                stats.add_legacy("Force Tags", LEGACY_OTHER["Force Tags"])
                stats.c["force_tags"] += 1
            else:
                stats.c["test_tags"] += 1
            self._count_tags(_values(node))
            self.generic_visit(node)

        def visit_ForceTags(self, node: Any) -> None:  # older parsers
            self.visit_TestTags(node)

        def visit_DefaultTags(self, node: Any) -> None:
            stats.add_legacy("Default Tags", LEGACY_OTHER["Default Tags"])
            stats.c["default_tags"] += 1
            self._count_tags(_values(node))
            self.generic_visit(node)

        def visit_KeywordTags(self, node: Any) -> None:
            if any(v.lower() == "robot:private" for v in _values(node)):
                self.file_private = True
            self.generic_visit(node)

        def visit_TestTemplate(self, node: Any) -> None:
            value = (node.value or "").strip()
            if value and value.upper() != "NONE":
                self.suite_template = True
                stats.c["template_suites"] += 1
            self.generic_visit(node)

        def _count_tags(self, values: List[str]) -> None:
            for value in values:
                if value and not value.startswith("-"):
                    stats.tags[_norm(value)] += 1

        # -- variables ----------------------------------------------------
        def visit_Variable(self, node: Any) -> None:
            name = node.name or ""
            if not name:
                return self.generic_visit(node)
            stats.c["section_variables"] += 1
            inner = name[2:-1] if name.endswith("}") else name[2:]
            base = inner.split(":", 1)[0]
            if ": " in inner:
                stats.c["typed_variables"] += 1
            if base != base.upper():
                stats.c["variables_not_upper"] += 1
                stats.example("variables_not_upper", f"{rel}:{node.lineno} {name}")
            self.generic_visit(node)

        # -- tests --------------------------------------------------------
        def visit_TestCase(self, node: Any) -> None:
            stats.c["tests"] += 1
            templated = self.suite_template
            for stmt in node.body:
                if type(stmt).__name__ == "Template":
                    value = (stmt.value or "").strip()
                    if value and value.upper() != "NONE":
                        templated = True
                        stats.c["templated_tests"] += 1
                    else:
                        templated = False
            if not templated and self._has_control(node.body):
                stats.c["control_in_untemplated"] += 1
                stats.example("control_in_untemplated", f"{rel}:{node.lineno} {node.name}")
            self.in_body = self.in_test = True
            self.generic_visit(node)
            self.in_body = self.in_test = False

        def _has_control(self, body: List[Any]) -> bool:
            return any(type(stmt).__name__ in CONTROL_NODES for stmt in body)

        def visit_Tags(self, node: Any) -> None:
            values = _values(node)
            if self.in_test:
                stats.c["tags_settings"] += 1
                self._count_tags(values)
            elif any(v.lower() == "robot:private" for v in values):
                stats.c["private_tagged"] += 1
            self.generic_visit(node)

        # -- keywords -----------------------------------------------------
        def visit_Keyword(self, node: Any) -> None:
            name = node.name or ""
            stats.c["keywords"] += 1
            if is_resource:
                stats.kw_defs[_norm(_strip_embedded(name))].append((name, f"{rel}:{node.lineno}"))
            args = _embedded_args(name)
            if args:
                stats.c["embedded"] += 1
                stats.example("embedded", f"{rel}:{node.lineno} {name}")
                kinds = [_embedded_kind(a) for a in args]
                if any(p for _, p in kinds):
                    stats.c["embedded_with_pattern"] += 1
                typed = sum(1 for t, _ in kinds if t)
                if typed:
                    stats.c["typed_arguments"] += typed
                    stats.c["keywords_with_typed"] += 1
            if BDD.match(name):
                stats.c["bdd_prefixed_names"] += 1
            plain = re.sub(r"\$\{\}", "", _strip_embedded(name))
            words = [w for w in plain.split() if w[:1].isalpha()]
            if "_" in plain:
                stats.c["underscore"] += 1
            elif words:
                stats.c["title_case" if all(w[0].isupper() for w in words) else "other_case"] += 1
            before = stats.c["private_tagged"]
            self.in_body = True
            self.generic_visit(node)
            self.in_body = False
            if self.file_private or stats.c["private_tagged"] > before:
                stats.c["private"] += 1

        def visit_Arguments(self, node: Any) -> None:
            values = _values(node)
            if values:
                stats.c["keywords_with_arguments"] += 1
            typed_here = 0
            for value in values:
                if re.match(r"^[$@&]\{[^}]*: [^}]+\}", value):
                    stats.c["typed_arguments"] += 1
                    typed_here += 1
                    stats.example("typed_arguments", f"{rel}:{node.lineno} {value}")
                elif re.match(r"^[$@&]\{[^}]+\}\s*:\s*\w", value):
                    stats.c["invalid_typed_arguments"] += 1
                    stats.example("invalid_typed_arguments", f"{rel}:{node.lineno} {value}")
            if typed_here:
                stats.c["keywords_with_typed"] += 1
            self.generic_visit(node)

        def visit_ReturnSetting(self, node: Any) -> None:
            stats.add_legacy("[Return]", LEGACY_OTHER["[Return]"])
            self.generic_visit(node)

        # -- statements ---------------------------------------------------
        def visit_Var(self, node: Any) -> None:
            stats.c["var_statements"] += 1
            self.generic_visit(node)

        def visit_KeywordCall(self, node: Any) -> None:
            keyword = node.keyword or ""
            if BDD.match(keyword):
                stats.c["bdd_steps"] += 1
            key = _norm(keyword)
            if key.startswith("builtin."):
                key = key[len("builtin."):]
            info = LEGACY_KEYWORDS.get(key)
            if info:
                stats.add_legacy(*info)
            for tok in node.get_tokens(Token.ASSIGN):
                value = tok.value.rstrip()
                if value.endswith(" ="):
                    stats.assign["name_space_equals"] += 1
                elif value.endswith("="):
                    stats.assign["name_equals"] += 1
                else:
                    stats.assign["no_equals"] += 1
            self.generic_visit(node)

    return Visitor()


def _scan_file(path: Path, root: Path, stats: _Stats) -> None:
    rel = path.relative_to(root).as_posix()
    pipe_file = any(line.startswith("| ") for line in _read(path).splitlines())
    if path.name == "__init__.robot":
        model = get_init_model(str(path), data_only=False)
        stats.c["init_files"] += 1
        is_resource = False
    elif path.suffix == ".resource":
        model = get_resource_model(str(path), data_only=False)
        stats.res_dirs[path.parent.relative_to(root).as_posix()] += 1
        is_resource = True
    else:
        model = get_model(str(path), data_only=False)
        is_resource = False
    _make_visitor(stats, rel, is_resource, pipe_file).visit(model)


def _features(effective: Optional[Tuple[int, int, int]]) -> Dict[str, Dict[str, Any]]:
    return {
        key: {"min": f"{mv[0]}.{mv[1]}", "available": (None if effective is None else effective[:2] >= mv)}
        for key, mv in FEATURES
    }


def _advice(data: Dict[str, Any]) -> List[Dict[str, str]]:
    rf = data["rf"]
    eff = _vtuple(rf["effective"])
    kw = data["keywords"]
    advice: List[Dict[str, str]] = []

    def add(ident: str, text: str) -> None:
        advice.append({"id": ident, "text": text})

    if eff is not None and eff[:2] < (7, 3) and data["scan"]["files"]:
        add("no-typed-arguments",
            f"Robot Framework {rf['effective']} is older than 7.3: do not write ${{name: type}} in "
            "[Arguments], VAR, FOR or the Variables section (it passes the dry run and fails at run "
            "time); keep arguments untyped and convert explicitly, for example with Convert To Integer.")
    with_args = kw["with_arguments"]
    if eff is not None and eff[:2] >= (7, 3) and with_args and kw["with_typed_arguments"] * 2 < with_args:
        add("use-typed-arguments",
            f"Robot Framework {rf['effective']} supports typed user-keyword arguments; "
            f"{kw['with_typed_arguments']} of {with_args} keywords with arguments use them. "
            "Type new arguments that are not strings, for example ${count: int}.")
    if kw["invalid_typed_arguments"]:
        add("fix-invalid-typed-arguments",
            f"{kw['invalid_typed_arguments']} argument(s) use the invalid form ${{name}}: type; write "
            "${name: type} on RF 7.3+ or drop the type and convert explicitly.")
    if kw["definitions"] and kw["embedded"] * 4 >= kw["definitions"]:
        add("follow-embedded-style",
            f"{kw['embedded']} of {kw['definitions']} keywords use embedded arguments; write new "
            "keywords of the same kind with embedded arguments, quoting adjacent ones or giving "
            "them a pattern.")
    dups = kw["duplicate_names"]["count"]
    if dups:
        add("resolve-duplicate-keywords",
            f"{dups} keyword name(s) are defined in more than one resource file; qualify calls "
            "(resource.Keyword Name), rename one of them, or use Set Library Search Order; check "
            "with robocop check --no-cache -s KW06.")
    legacy = data["legacy"]
    if legacy:
        ids = sorted({item["robocop"] for item in legacy if item["robocop"]})
        total = sum(item["count"] for item in legacy)
        text = f"{total} legacy construct(s) in {len(legacy)} kind(s); replace them with the modern forms"
        if ids:
            text += " and check with: robocop check --no-cache " + " ".join(f"-s {i}" for i in ids)
        add("migrate-legacy", text + ".")
    web = data["libraries"]["web_library"]
    if isinstance(web, str):
        add("web-library",
            f"Web tests use {web}; write new web keywords with {web} (see the {WEB_LIBRARIES[web]} skill).")
    elif isinstance(web, list):
        add("mixed-web-libraries",
            "Both Browser and SeleniumLibrary are imported; keep each suite on one of them and write "
            "new web tests with the one the surrounding files use.")
    return advice[:8]


def run(root: Any = ".", max_files: int = DEFAULT_MAX_FILES,
        max_examples: int = DEFAULT_MAX_EXAMPLES) -> Dict[str, Any]:
    """Scan ``root`` and return the rf-conventions/1 dictionary.

    Raises :class:`InputError` when ``root`` is missing or not a directory and
    :class:`RobotEnvironmentError` when Robot Framework >= 7 is unavailable.
    """
    _require_robot()
    path = Path(root).expanduser()
    if not path.exists():
        raise InputError(f"path not found: {root}")
    if not path.is_dir():
        raise InputError(f"not a directory: {root}")
    path = path.resolve()
    max_examples = max(0, int(max_examples))
    stats = _Stats(max_examples)
    state = {"truncated": False}
    files = 0
    for fpath in _iter_files(path, max(0, int(max_files)), state):
        files += 1
        try:
            _scan_file(fpath, path, stats)
        except Exception as exc:  # parser failure on one file must not abort the scan
            if len(stats.parse_errors) < max_examples:
                stats.parse_errors.append({"file": fpath.relative_to(path).as_posix(),
                                           "error": str(exc).splitlines()[0][:200] if str(exc) else type(exc).__name__})
            stats.c["parse_failures"] += 1

    installed = str(_RF_VERSION) if _RF_VERSION else None
    project_env = _project_env_version(path)
    locked = _locked_version(path)
    effective, source = None, None
    for src, value in (("project_env", project_env), ("locked", locked), ("installed", installed)):
        if value and _vtuple(value):
            effective, source = value, src
            break

    c = stats.c
    dups = [(k, v) for k, v in stats.kw_defs.items() if len({loc.split(":")[0] for _, loc in v}) > 1]
    web = [lib for lib in WEB_LIBRARIES if stats.libs.get(lib)]
    if stats.res_dirs:
        resource_dir: Optional[str] = stats.res_dirs.most_common(1)[0][0]
    else:
        resource_dir = next((d for d in RESOURCE_DIR_CANDIDATES if (path / d).is_dir()), None)
    varfiles = sorted(
        p.relative_to(path).as_posix()
        for d in VARIABLE_DIRS if (path / d).is_dir()
        for p in (path / d).rglob("*")
        if p.is_file() and p.suffix.lower() in VARFILE_EXT and "__pycache__" not in p.parts
    )
    data: Dict[str, Any] = {
        "schema": SCHEMA,
        "root": str(path),
        "rf": {
            "installed": installed,
            "project_env": project_env,
            "locked": locked,
            "declared": _declared_version(path),
            "effective": effective,
            "effective_source": source,
            "features": _features(_vtuple(effective)),
        },
        "scan": {
            "files": files,
            "truncated": state["truncated"],
            "parse_errors": stats.parse_errors,
            "syntax_errors": c["syntax_errors"],
        },
        "style": {
            "separator": {
                "dominant": stats.sep.most_common(1)[0][0] if stats.sep else None,
                "counts": dict(stats.sep.most_common(5)),
            },
            "assignment": {
                "dominant": stats.assign.most_common(1)[0][0] if stats.assign else None,
                "counts": {k: stats.assign.get(k, 0) for k in ("name_equals", "name_space_equals", "no_equals")},
            },
            "keyword_case": {"title_case": c["title_case"], "other": c["other_case"],
                             "underscore": c["underscore"]},
        },
        "keywords": {
            "definitions": c["keywords"],
            "with_arguments": c["keywords_with_arguments"],
            "with_typed_arguments": c["keywords_with_typed"],
            "embedded": c["embedded"],
            "embedded_with_pattern": c["embedded_with_pattern"],
            "typed_arguments": c["typed_arguments"],
            "invalid_typed_arguments": c["invalid_typed_arguments"],
            "private": c["private"],
            "bdd_prefixed_names": c["bdd_prefixed_names"],
            "duplicate_names": {
                "count": len(dups),
                "examples": [
                    {"name": v[0][0], "defined_in": [loc for _, loc in v][:max_examples]}
                    for _, v in dups[:max_examples]
                ],
            },
            "examples": {key: stats.examples.get(key, [])
                         for key in ("embedded", "typed_arguments", "invalid_typed_arguments")},
        },
        "calls": {"bdd_steps": c["bdd_steps"], "var_statements": c["var_statements"]},
        "tests": {
            "count": c["tests"],
            "template_suites": c["template_suites"],
            "templated_tests": c["templated_tests"],
            "tag_settings": {"test_tags": c["test_tags"], "force_tags": c["force_tags"],
                             "default_tags": c["default_tags"], "tags": c["tags_settings"]},
            "top_tags": [{"tag": t, "count": n} for t, n in stats.tags.most_common(10)],
            "control_in_untemplated": c["control_in_untemplated"],
            "examples": stats.examples.get("control_in_untemplated", []),
        },
        "variables": {
            "section_variables": c["section_variables"],
            "not_uppercase": c["variables_not_upper"],
            "typed": c["typed_variables"],
            "examples": stats.examples.get("variables_not_upper", []),
        },
        "legacy": [{"construct": k, "count": n, "robocop": stats.legacy_ids.get(k)}
                   for k, n in sorted(stats.legacy.items(), key=lambda kv: (-kv[1], kv[0]))],
        "layout": {
            "resource_dirs": dict(stats.res_dirs.most_common(5)),
            "resource_dir": resource_dir,
            "variable_files": varfiles[:10],
            "variable_imports": dict(sorted(stats.var_imports.items())),
            "libraries_dir": (path / "libraries").is_dir(),
            "init_files": c["init_files"],
            "robot_toml": (path / "robot.toml").is_file(),
        },
        "libraries": {
            "imports": dict(stats.libs.most_common(10)),
            "web_library": web[0] if len(web) == 1 else (web or None),
        },
        "advice": [],
    }
    data["advice"] = _advice(data)
    return data


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

EPILOG = """\
examples:
  uv run python scripts/rf_conventions.py .
  uv run python scripts/rf_conventions.py path/to/project --max-examples 5 --pretty
  uv run python scripts/rf_conventions.py . --max-files 500 --json-out results/conventions.json

Paths to the script are relative to the rf-language skill directory; PATH is the
project to scan. Not using uv? Run with the project's interpreter (.venv/bin/python
or poetry run python); see rf-setup.
exit codes: 0 ok (also when no .robot/.resource files exist), 1 internal error,
2 usage, 3 environment (robotframework>=7 missing), 4 path missing or not a directory.
"""


class _Parser(argparse.ArgumentParser):
    """argparse with ``error:``/``hint:`` stderr lines and exit code 2."""

    def error(self, message: str) -> NoReturn:  # type: ignore[override]
        _fail(EXIT_USAGE, message,
              f"see the options and examples: uv run python {SCRIPT_PATH} --help")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        description="Detect a Robot Framework project's conventions and print them as JSON on stdout.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("path", nargs="?", default=".", help="Project directory to scan (default: .)")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES,
                        help=f"Scan at most N .robot/.resource files (default {DEFAULT_MAX_FILES}; sets scan.truncated)")
    parser.add_argument("--max-examples", type=int, default=DEFAULT_MAX_EXAMPLES,
                        help=f"Examples per list (default {DEFAULT_MAX_EXAMPLES}; 0 = none)")
    parser.add_argument("--json-out", metavar="FILE",
                        help="Write the JSON result to FILE; stdout gets {written, bytes, mode}")
    parser.add_argument("--pretty", action="store_true", help="Indent the JSON output")
    parser.add_argument("--debug", action="store_true", help="Print a traceback on internal errors")
    return parser


def emit(data: Dict[str, Any], *, pretty: bool, json_out: Optional[str]) -> None:
    text = json.dumps(data, indent=2) if pretty else json.dumps(data, separators=(",", ":"))
    if not json_out:
        print(text)
        return
    os.makedirs(os.path.dirname(os.path.abspath(json_out)), exist_ok=True)
    payload = (text + "\n").encode("utf-8")
    with open(json_out, "wb") as fh:
        fh.write(payload)
    print(json.dumps({"written": json_out, "bytes": len(payload), "mode": "conventions"}))


def _run_cli(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.max_files < 1:
        parser.error("--max-files must be >= 1")
    if args.max_examples < 0:
        parser.error("--max-examples must be >= 0")
    try:
        _require_robot()
    except RobotEnvironmentError as exc:
        _fail(EXIT_ENV, str(exc), *exc.hints)
    try:
        data = run(args.path, max_files=args.max_files, max_examples=args.max_examples)
    except InputError as exc:
        _fail(EXIT_INPUT, str(exc), exc.hint)
    if data["scan"]["files"] == 0:
        _warn(f"no .robot or .resource files found under {data['root']}")
    if data["scan"]["truncated"]:
        _warn(f"scan stopped after {args.max_files} files (scan.truncated); raise --max-files to scan more")
    emit(data, pretty=args.pretty, json_out=args.json_out)
    return EXIT_OK


def main(argv: Optional[List[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        code = _run_cli(args, parser)
    except SystemExit:
        raise
    except Exception as exc:
        if args.debug:
            traceback.print_exc(file=sys.stderr)
        _fail(EXIT_INTERNAL, f"internal: {type(exc).__name__}: {exc}",
              "re-run with --debug for a traceback")
    sys.exit(code)


if __name__ == "__main__":
    main()
