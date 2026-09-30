#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["robotframework>=7"]
# ///
"""Robot Framework Python library checker for the rf-python-library skill.

Loads each project keyword library the way Robot Framework's libdoc does and
prints one JSON object (``schema_version`` 1) with, per library, its metadata
(name, source, scope, version, doc format, API style), its keywords (name,
arguments in libdoc form, line number, has documentation) and findings for
Robot Framework-specific defects: import/init failures, rejected keywords,
"contains no keywords", leaked keywords, public methods hidden by ``@library``,
exposed listener methods, lost signatures, ``str`` in unions, state kept in a
TEST-scope library, output during import, broad ``except``, untyped or
positional-only arguments and missing documentation.

Run it in the project environment:
``uv run python scripts/check_library.py libraries/<Name>.py``.

Safety: loading a library executes its import and ``__init__`` code. The
checker therefore only accepts libraries inside the project root (the working
directory or ``--project-root``), loads each one in a child process of the same
interpreter with a timeout, captures everything that process prints, makes no
network calls itself and writes no files except the ``--json-out`` target. Use
it on your own project code only. Libdoc leaves ``BuiltIn().robot_running``
false, so side effects guarded by it stay inactive.

Exit codes: 0 every library was checked (findings and partial load failures
included), 1 internal error, 2 usage, 3 environment (robotframework>=7 not
importable), 4 input missing or outside the project root, or every library
failed to load. stdout carries only the JSON result; diagnostics go to stderr
as ``error:`` / ``warning:`` / ``hint:`` lines.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import traceback
from importlib.machinery import PathFinder
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional, Tuple

SCHEMA_VERSION = 1
MIN_RF_MAJOR = 7
EXIT_OK, EXIT_INTERNAL, EXIT_USAGE, EXIT_ENV, EXIT_INPUT = 0, 1, 2, 3, 4
DEFAULT_TIMEOUT = 30
DEFAULT_MAX_KEYWORDS = 100
DEFAULT_MAX_FINDINGS = 50
MAX_MESSAGE = 300
MAX_OUTPUT_FINDINGS = 5
SCRIPT_PATH = os.path.abspath(__file__)
SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}

#: The finding ids this checker can report (the contract; messages are not).
FINDING_IDS: Tuple[str, ...] = (
    "import_failed",
    "keyword_creation_failed",
    "no_keywords",
    "leaked_keyword",
    "public_method_not_keyword",
    "listener_method_exposed",
    "signature_lost",
    "union_with_str",
    "state_in_test_scope",
    "output_during_import",
    "broad_except",
    "untyped_argument",
    "positional_only_argument",
    "missing_doc",
    "library_doc_missing",
    "internal",
)

#: Listener API v3 method names (RF 7.x), incl. the start_/end_ body-item methods.
LISTENER_METHODS = frozenset(
    ["start_suite", "end_suite", "start_test", "end_test", "start_keyword", "end_keyword",
     "start_library_keyword", "end_library_keyword", "start_user_keyword", "end_user_keyword",
     "start_invalid_keyword", "end_invalid_keyword", "start_body_item", "end_body_item",
     "log_message", "message", "library_import", "resource_import", "variables_import",
     "output_file", "log_file", "report_file", "xunit_file", "debug_file", "close"]
    + [f"{p}_{item}" for p in ("start", "end") for item in (
        "for", "for_iteration", "while", "while_iteration", "group", "if", "if_branch",
        "try", "try_branch", "var", "break", "continue", "return", "error")]
)

#: RF's own messages while importing a library (not user output).
RF_INTERNAL = re.compile(
    r"^(Imported library |Imported test library |Created keyword |In library '|"
    r"Keyword '.*' could not be run on failure|Library '.*' is a listener)"
)
ADDING_KEYWORD_FAILED = re.compile(r"(Error in|In) library '.*': Adding keyword '.*' failed")
DEFAULT_LIBRARY_DOC = re.compile(r"^Documentation for library ``.*``\.?$")

INPUT_HINT = ("the checker loads project libraries only: pass a .py file or package directory "
              "inside the project root (or --project-root), or an import name found on --pythonpath")
FALLBACK_HINT = ("not using uv? use the project's interpreter (.venv/bin/python or poetry run python); "
                 "see the rf-setup skill")


# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

def _fail(code: int, error: str, *hints: str) -> NoReturn:
    print(f"error: {error}", file=sys.stderr)
    for hint in hints:
        print(f"hint: {hint}", file=sys.stderr)
    sys.exit(code)


def _warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def _cap(text: str, limit: int = MAX_MESSAGE) -> str:
    text = " ".join(str(text).split()) if "\n" in str(text) else str(text)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _require_robot() -> str:
    """Return the Robot Framework version or exit 3 with hints."""
    try:
        from robot.version import VERSION
    except ImportError as exc:
        _fail(EXIT_ENV, f"Robot Framework is not importable by {sys.executable} ({exc})",
              f"run it through the project environment: uv run python {SCRIPT_PATH} ...",
              "add Robot Framework to the project: uv add robotframework",
              FALLBACK_HINT)
    try:
        major = int(str(VERSION).split(".")[0])
    except ValueError:
        major = 0
    if major < MIN_RF_MAJOR:
        _fail(EXIT_ENV, f"Robot Framework {VERSION} found in {sys.executable}; "
                        f"robotframework>={MIN_RF_MAJOR} is required",
              f"run it through the project environment: uv run python {SCRIPT_PATH} ...",
              'upgrade Robot Framework in the project: uv add "robotframework>=7"',
              FALLBACK_HINT)
    return str(VERSION)


# ---------------------------------------------------------------------------
# Input resolution (parent; never imports user code)
# ---------------------------------------------------------------------------

class InputError(RuntimeError):
    def __init__(self, message: str, hint: str = INPUT_HINT) -> None:
        super().__init__(message)
        self.hint = hint


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def _looks_like_path(value: str) -> bool:
    return ("/" in value or "\\" in value or value.endswith(".py")
            or value in (".", "..") or Path(value).exists())


def _find_module(name: str, search: List[str]) -> Optional[Path]:
    """Origin of module ``name`` found on ``search`` without importing anything."""
    locations: Optional[List[str]] = list(search)
    spec = None
    for part in name.split("."):
        if locations is None:
            return None
        spec = PathFinder.find_spec(part, locations)
        if spec is None:
            return None
        locations = list(spec.submodule_search_locations or []) or None
    if spec is None or not spec.origin or spec.origin in ("built-in", "frozen"):
        return None
    return Path(spec.origin)


def resolve_name(name: str, pythonpath: List[str], root: Path) -> Tuple[Path, str]:
    """Resolve an import name (``Inventory``, ``pkg.mod``, ``pkg.mod.Class``) to its file.

    Only ``pythonpath`` entries (all inside the project root) are searched. A
    name found elsewhere (site-packages, stdlib) is refused.
    """
    parts = name.split(".")
    if not all(p.isidentifier() for p in parts):
        raise InputError(f"not a library path or import name: {name}")
    for cut in (len(parts), len(parts) - 1):
        if cut < 1:
            break
        origin = _find_module(".".join(parts[:cut]), pythonpath)
        if origin is not None:
            if not _inside(origin, root):
                break
            return origin.resolve(), name
    elsewhere = None
    for cut in (len(parts), len(parts) - 1):
        if cut >= 1:
            elsewhere = elsewhere or _find_module(".".join(parts[:cut]), sys.path)
    if elsewhere is not None and not _inside(elsewhere, root):
        raise InputError(
            f"'{name}' resolves to {elsewhere}, outside the project root {root}; "
            "only project libraries are checked",
            "for installed third-party libraries use the rf-libdoc skill (or robotcode libdoc) instead",
        )
    raise InputError(
        f"cannot find module '{name}' on the python-path {pythonpath or '[]'}",
        "pass the library file (libraries/<Name>.py) or add its directory with --pythonpath",
    )


def resolve_inputs(inputs: List[str], pythonpath: List[str], root: Path) -> List[Dict[str, Any]]:
    resolved: List[Dict[str, Any]] = []
    for value in inputs:
        if _looks_like_path(value):
            path = Path(value).expanduser()
            if not path.exists():
                raise InputError(f"library not found: {value}",
                                 "check the path; project libraries usually live in libraries/")
            path = path.resolve()
            if not _inside(path, root):
                raise InputError(
                    f"{value} is outside the project root {root}; only project libraries are checked "
                    "(loading a library runs its code)",
                    "run the checker from the project root or pass --project-root; for installed "
                    "libraries use the rf-libdoc skill",
                )
            if path.is_dir():
                init = path / "__init__.py"
                if not init.is_file():
                    raise InputError(f"{value} is a directory without __init__.py (not a library package)")
                origin, own = init, path
            elif path.suffix != ".py":
                raise InputError(f"{value} is not a Python file (.py) or package directory")
            else:
                origin, own = path, path
            resolved.append({"input": value, "spec": str(path), "origin": str(origin),
                             "own": str(own), "extra_path": str(path.parent)})
        else:
            origin, spec = resolve_name(value, pythonpath, root)
            own = origin.parent if origin.name == "__init__.py" else origin
            resolved.append({"input": value, "spec": spec, "origin": str(origin),
                             "own": str(own), "extra_path": None})
    return resolved


# ---------------------------------------------------------------------------
# Worker (child process): load one library and analyse it
# ---------------------------------------------------------------------------

class _Capture:
    """Robot Framework logger that records messages instead of printing them."""

    def __init__(self) -> None:
        self.messages: List[Tuple[str, str]] = []

    def message(self, msg: Any) -> None:
        self.messages.append((str(getattr(msg, "level", "INFO")), str(getattr(msg, "message", msg))))

    log_message = message


def _finding(fid: str, severity: str, message: str, hint: Optional[str] = None,
             keyword: Optional[str] = None) -> Dict[str, Any]:
    return {"id": fid, "severity": severity, "keyword": keyword, "message": _cap(message), "hint": hint}


def _import_failed_hint(message: str) -> str:
    if "ModuleNotFoundError" in message or "No module named" in message:
        return ("add the missing package to the project with its tool (uv add <package>; see rf-setup), "
                "or fix the import / --pythonpath")
    if "RobotNotRunningError" in message:
        return ("BuiltIn() is not usable while libdoc or the checker loads the library: "
                "call BuiltIn() inside keywords, not in __init__ or at import time")
    if message.startswith("Initializing library"):
        return ("__init__ failed: keep __init__ cheap and guard side effects with "
                "BuiltIn().robot_running and not BuiltIn().dry_run_active, or pass --init-arg")
    return "fix the import error; run the module with python to see the full traceback"


def _function_index(tree: ast.Module) -> Dict[int, Tuple[str, Optional[str], ast.AST]]:
    """Line number (def and decorator lines) -> (function name, class name, node)."""
    index: Dict[int, Tuple[str, Optional[str], ast.AST]] = {}

    def add(fn: Any, cls: Optional[str]) -> None:
        for line in [fn.lineno] + [d.lineno for d in fn.decorator_list]:
            index.setdefault(line, (fn.name, cls, fn))

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add(node, None)
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    add(sub, node.name)
    return index


def _self_attr(target: ast.AST) -> Optional[str]:
    """``self.x`` / ``self.x[...]`` / ``self.x.y`` assignment target -> ``x``."""
    node = target
    while isinstance(node, (ast.Subscript, ast.Attribute)):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "self":
            return node.attr
        node = node.value
    return None


def _state_mutations(cls_node: ast.ClassDef) -> List[Tuple[str, str, int]]:
    out: List[Tuple[str, str, int]] = []
    for fn in cls_node.body:
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or fn.name.startswith("_"):
            continue
        for sub in ast.walk(fn):
            targets: List[ast.AST] = []
            if isinstance(sub, ast.Assign):
                targets = list(sub.targets)
            elif isinstance(sub, (ast.AugAssign, ast.AnnAssign)):
                targets = [sub.target]
            hit = next((a for a in (_self_attr(t) for t in targets) if a), None)
            if hit:
                out.append((fn.name, hit, sub.lineno))
                break
    return out


def _is_broad(handler: ast.ExceptHandler) -> bool:
    names: List[ast.AST] = []
    if handler.type is None:
        return True
    names = list(handler.type.elts) if isinstance(handler.type, ast.Tuple) else [handler.type]
    return any(isinstance(n, ast.Name) and n.id in ("Exception", "BaseException") for n in names)


def _broad_excepts(fn: ast.AST) -> List[int]:
    lines = []
    for sub in ast.walk(fn):
        if isinstance(sub, ast.ExceptHandler) and _is_broad(sub):
            if not any(isinstance(n, ast.Raise) for stmt in sub.body for n in ast.walk(stmt)):
                lines.append(sub.lineno)
    return lines


def _library_object(module: Any, requested: str) -> Tuple[Any, Optional[type]]:
    """Mirror RF's selection: named class, class with the module's name, or the single @library class."""
    import inspect
    parts = requested.split(".")
    for name in (parts[-1], module.__name__.split(".")[-1]):
        cls = getattr(module, name, None)
        if inspect.isclass(cls):
            return cls, cls
    from robot.version import VERSION
    if tuple(int(p) for p in re.findall(r"\d+", VERSION)[:2]) < (7, 2):
        return module, None  # before RF 7.2 a module without a same-named class is a module library
    decorated = [c for _, c in inspect.getmembers(module, inspect.isclass)
                 if c.__module__ == module.__name__ and "ROBOT_AUTO_KEYWORDS" in vars(c)]
    if len(decorated) == 1:
        return decorated[0], decorated[0]
    return module, None


def _declares_listener(cls: type, cls_node: Optional[ast.ClassDef]) -> bool:
    if getattr(cls, "ROBOT_LIBRARY_LISTENER", None) is not None:
        return True
    if cls_node is not None:
        for sub in ast.walk(cls_node):
            if isinstance(sub, ast.Assign) and any(
                    (isinstance(t, ast.Attribute) and t.attr == "ROBOT_LIBRARY_LISTENER")
                    or (isinstance(t, ast.Name) and t.id == "ROBOT_LIBRARY_LISTENER")
                    for t in sub.targets):
                return True
    return False


def _norm(name: str) -> str:
    return name.lower().replace(" ", "_")


def _type_is_union_with_str(type_info: Any) -> bool:
    if not type_info or not getattr(type_info, "is_union", False):
        return False
    nested = list(getattr(type_info, "nested", None) or [])
    has_str = any(getattr(n, "type", None) is str for n in nested)
    others = [n for n in nested if getattr(n, "type", None) not in (str, type(None))
              and str(getattr(n, "name", "")) != "None"]
    return has_str and bool(others)


def _analyse(doc: Any, cfg: Dict[str, Any], messages: List[Tuple[str, str]]) -> Dict[str, Any]:
    import inspect
    own = Path(cfg["own"])
    root = Path(cfg["root"])
    findings: List[Dict[str, Any]] = []
    raw_doc = (doc.doc or "").strip()
    has_doc = bool(raw_doc) and not DEFAULT_LIBRARY_DOC.match(raw_doc)

    module = None
    origin = Path(cfg["origin"]).resolve()
    for mod in list(sys.modules.values()):
        f = getattr(mod, "__file__", None)
        if f and Path(f).resolve() == origin:
            module = mod
            break
    obj, cls = (_library_object(module, cfg["spec"]) if module is not None else (None, None))
    if obj is not None and hasattr(obj, "get_keyword_names"):
        api = "dynamic" if hasattr(obj, "run_keyword") else "hybrid"
    else:
        api = "static"

    tree = None
    try:
        tree = ast.parse(origin.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        tree = None
    index = _function_index(tree) if tree is not None else {}
    cls_node = None
    if tree is not None and cls is not None:
        cls_node = next((n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls.__name__), None)

    library = {
        "name": doc.name,
        "source": str(doc.source) if doc.source else None,
        "scope": doc.scope,
        "version": doc.version or None,
        "doc_format": doc.doc_format,
        "api": api,
        "has_doc": has_doc,
        "keyword_count": len(doc.keywords),
        "init_args": list(cfg["init_args"]),
    }

    for level, text in messages:
        if level in ("ERROR", "WARN") and ADDING_KEYWORD_FAILED.search(text):
            findings.append(_finding(
                "keyword_creation_failed", "error", text,
                "fix the keyword definition; library embedded-argument names take no inline types "
                "(use Python type hints on the function arguments)"))
    if not doc.keywords:
        findings.append(_finding(
            "no_keywords", "error", f"library '{doc.name}' contains no keywords",
            "with @library, decorate each keyword method with @keyword (automatic discovery is off); "
            "check keyword_creation_failed findings"))
    if not has_doc:
        findings.append(_finding("library_doc_missing", "info", f"library '{doc.name}' has no documentation",
                                 "add a class or module docstring (libdoc shows it as the introduction)"))

    keywords: List[Dict[str, Any]] = []
    for kw in doc.keywords:
        method = None
        if kw.lineno and kw.source and Path(str(kw.source)).resolve() == origin:
            hit = index.get(kw.lineno)
            method = hit[0] if hit else None
        entry = {"name": kw.name, "args": [str(a) for a in kw.args], "lineno": kw.lineno,
                 "has_doc": bool((kw.doc or "").strip())}
        keywords.append(entry)
        try:
            src = str(kw.source) if kw.source else ""
            known = bool(src) and not src.startswith("<") and Path(src).exists()
            if api == "static":
                leaked = not known or not (Path(src).resolve() == own or _inside(Path(src), own))
            else:
                leaked = bool(src) and (not known or not _inside(Path(src), root))
            if leaked:
                findings.append(_finding(
                    "leaked_keyword", "warning",
                    f"'{kw.name}' is defined in {src or 'an unknown source'}, not in {own.name}",
                    "import modules instead of functions (import os, not from os.path import join), prefix "
                    "helpers with _, or use @library so only @keyword methods become keywords", kw.name))
            if not entry["has_doc"]:
                findings.append(_finding("missing_doc", "info", f"keyword '{kw.name}' has no documentation",
                                         "add a docstring; its first line becomes the short doc", kw.name))
            kinds = [str(a.kind) for a in kw.args]
            if kinds == ["VAR_POSITIONAL", "VAR_NAMED"]:
                findings.append(_finding(
                    "signature_lost", "warning", f"'{kw.name}' only takes *args, **kwargs",
                    "a decorator without functools.wraps hides the real signature (and type conversion)",
                    kw.name))
            if "POSITIONAL_ONLY" in kinds:
                findings.append(_finding(
                    "positional_only_argument", "info",
                    f"'{kw.name}' has positional-only arguments; tests cannot pass them by name",
                    "drop the / marker unless the positional-only form is intended", kw.name))
            for arg in kw.args:
                if str(arg.kind) in ("VAR_POSITIONAL", "VAR_NAMED", "POSITIONAL_ONLY_MARKER",
                                     "NAMED_ONLY_MARKER"):
                    continue
                if _type_is_union_with_str(arg.type):
                    findings.append(_finding(
                        "union_with_str", "warning",
                        f"'{kw.name}' argument '{arg}' contains str: string arguments are never converted",
                        "drop str from the union (or put the converting types only), or convert explicitly",
                        kw.name))
                if not arg.type and arg.required:
                    findings.append(_finding(
                        "untyped_argument", "info", f"'{kw.name}' argument '{arg.name}' has no type hint",
                        "add a type hint to get automatic conversion and documented types", kw.name))
            names = {_norm(kw.name)} | ({method} if method else set())
            if names & LISTENER_METHODS:
                findings.append(_finding(
                    "listener_method_exposed", "warning",
                    f"listener method '{method or kw.name}' is exposed as keyword '{kw.name}'",
                    "register the listener with @library(listener='SELF') / ROBOT_LIBRARY_LISTENER and use "
                    "@library so listener methods are not keywords, or move the listener to its own class",
                    kw.name))
            if method and api == "static" and tree is not None:
                fn = index[kw.lineno][2]
                for line in _broad_excepts(fn):
                    findings.append(_finding(
                        "broad_except", "info",
                        f"'{kw.name}' catches Exception/BaseException (line {line}) without re-raising",
                        "catch specific exceptions; a broad except swallows Robot Framework timeouts "
                        "(robot.errors.TimeoutExceeded on RF >= 7.3, TimeoutError before)", kw.name))
        except Exception as exc:  # RF API differences must not crash the checker
            findings.append(_finding("internal", "info", f"check of '{kw.name}' failed: {type(exc).__name__}: {exc}",
                                     "report this with the Robot Framework version", kw.name))

    if cls is not None and api == "static":
        try:
            findings.extend(_class_checks(cls, cls_node, doc.scope, origin, inspect))
        except Exception as exc:
            findings.append(_finding("internal", "info", f"class checks failed: {type(exc).__name__}: {exc}",
                                     "report this with the Robot Framework version"))

    for level, text in messages:
        if level in ("TRACE", "DEBUG") or RF_INTERNAL.search(text) or ADDING_KEYWORD_FAILED.search(text):
            continue
        findings.append(_output_finding(f"[{level}] {text}"))
    return {"library": library, "keywords": keywords, "findings": findings}


def _output_finding(text: str) -> Dict[str, Any]:
    return _finding(
        "output_during_import", "warning", f"output while importing or initialising the library: {text}",
        "libdoc, --dryrun and every new instance run this code: move it into a keyword or guard it with "
        "BuiltIn().robot_running and not BuiltIn().dry_run_active")


def _class_checks(cls: type, cls_node: Optional[ast.ClassDef], scope: str, origin: Path,
                  inspect: Any) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    listener = _declares_listener(cls, cls_node)
    if vars(cls).get("ROBOT_AUTO_KEYWORDS", True) is False or getattr(cls, "ROBOT_AUTO_KEYWORDS", True) is False:
        for name, member in inspect.getmembers(cls):
            if name.startswith("_") or inspect.isclass(member) or not callable(member):
                continue
            try:
                if Path(inspect.getsourcefile(member) or "").resolve() != origin:
                    continue
            except TypeError:
                continue
            if hasattr(member, "robot_name") or getattr(member, "robot_not_keyword", False):
                continue
            if listener and name in LISTENER_METHODS:
                continue
            findings.append(_finding(
                "public_method_not_keyword", "warning",
                f"public method '{name}' is not a keyword: @library turns off automatic keyword discovery",
                "add @keyword to expose it; mark helpers with @not_keyword or a leading underscore", name))
    if scope == "TEST" and cls_node is not None:
        for method, attr, line in _state_mutations(cls_node):
            findings.append(_finding(
                "state_in_test_scope", "warning",
                f"'{method}' changes self.{attr} (line {line}) but the scope is TEST: a new instance is "
                "created for every test, so this state does not survive to the next test",
                "state that must span tests needs @library(scope='SUITE') or 'GLOBAL' plus a cleanup keyword; "
                "if the state is meant to reset for every test, keep TEST and say so (heuristic warning)", method))
    return findings


def run_worker(cfg_path: str) -> int:
    """Child process entry point: load one library, write the result JSON to cfg['result']."""
    sys.dont_write_bytecode = True
    with open(cfg_path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    result: Dict[str, Any] = {"ok": False}
    try:
        for entry in reversed(cfg["pythonpath"]):
            if entry not in sys.path:
                sys.path.insert(0, entry)
        from robot.output import LOGGER
        LOGGER.unregister_console_logger()
        capture = _Capture()
        LOGGER.register_logger(capture)
        start = len(capture.messages)
        from robot.libdocpkg import LibraryDocumentation
        spec = cfg["spec"] + "".join("::" + a for a in cfg["init_args"])
        try:
            doc = LibraryDocumentation(spec)
        except Exception as exc:
            text = str(exc).strip()
            first = text.splitlines()[0] if text else type(exc).__name__
            result = {"ok": False, "error": first, "hint": _import_failed_hint(first)}
        else:
            result = {"ok": True, **_analyse(doc, cfg, capture.messages[start:])}
    except BaseException as exc:  # noqa: BLE001 - the worker must always report
        result = {"ok": False, "error": f"checker worker failed: {type(exc).__name__}: {exc}",
                  "hint": "re-run with --debug for a traceback", "internal": True,
                  "traceback": traceback.format_exc() if cfg.get("debug") else None}
    with open(cfg["result"], "w", encoding="utf-8") as fh:
        json.dump(result, fh)
    return 0


# ---------------------------------------------------------------------------
# Parent: run one worker per library
# ---------------------------------------------------------------------------

def _load_one(item: Dict[str, Any], pythonpath: List[str], root: Path, init_args: List[str],
              timeout: float, debug: bool) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="rf-check-library-") as tmp:
        cfg_file = Path(tmp) / "config.json"
        result_file = Path(tmp) / "result.json"
        extra = [item["extra_path"]] if item["extra_path"] else []
        cfg = {"spec": item["spec"], "origin": item["origin"], "own": item["own"], "root": str(root),
               "init_args": init_args, "pythonpath": pythonpath + [p for p in extra if p not in pythonpath],
               "result": str(result_file), "debug": debug}
        cfg_file.write_text(json.dumps(cfg), encoding="utf-8")
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
        try:
            proc = subprocess.run([sys.executable, SCRIPT_PATH, "--_worker", str(cfg_file)],
                                  cwd=str(root), capture_output=True, text=True, timeout=timeout,
                                  env=env, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return {"ok": False,
                    "error": f"loading the library timed out after {timeout:g} s (import or __init__ hangs)",
                    "hint": "move slow work (connections, waits) out of import and __init__ into keywords, "
                            "or raise --timeout"}
        data: Dict[str, Any]
        if result_file.is_file():
            data = json.loads(result_file.read_text(encoding="utf-8"))
        else:
            tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-1:]
            data = {"ok": False,
                    "error": f"the library process exited with code {proc.returncode} before reporting"
                             + (f": {_cap(tail[0], 200)}" if tail else ""),
                    "hint": "the library ends the interpreter at import or __init__ (sys.exit/os._exit or a "
                            "crash in a native extension)"}
            return data
        raw = "\n".join(t for t in (proc.stdout.strip(), proc.stderr.strip()) if t)
        if data.get("ok") and raw:
            data["raw_output"] = raw
        if debug and data.get("traceback"):
            sys.stderr.write("".join(f"hint: {ln}\n" for ln in data["traceback"].splitlines()))
        return data


def _bounded(entry: Dict[str, Any], max_keywords: int, max_findings: int) -> Dict[str, Any]:
    findings = sorted(entry["findings"], key=lambda f: SEVERITY_ORDER[f["severity"]])
    keywords = entry["keywords"]
    entry["omitted"] = {"keywords": max(0, len(keywords) - max_keywords),
                        "findings": max(0, len(findings) - max_findings)}
    entry["keywords"] = keywords[:max_keywords]
    entry["findings"] = findings[:max_findings]
    return entry


def check(inputs: List[str], *, init_args: Optional[List[str]] = None, pythonpath: Optional[List[str]] = None,
          project_root: Optional[str] = None, timeout: float = DEFAULT_TIMEOUT,
          max_keywords: int = DEFAULT_MAX_KEYWORDS, max_findings: int = DEFAULT_MAX_FINDINGS,
          debug: bool = False) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Check ``inputs``; return (JSON result, list of load failures). Raises InputError."""
    version = _require_robot()
    root = Path(project_root or os.getcwd()).expanduser()
    if not root.is_dir():
        raise InputError(f"project root not found or not a directory: {root}",
                         "pass the directory that holds libraries/ and tests/ with --project-root")
    root = root.resolve()
    if pythonpath:
        paths: List[str] = []
        for entry in pythonpath:
            p = Path(entry).expanduser()
            p = (p if p.is_absolute() else Path.cwd() / p).resolve()
            if not p.is_dir():
                raise InputError(f"--pythonpath entry not found: {entry}")
            if not _inside(p, root):
                raise InputError(f"--pythonpath entry {entry} is outside the project root {root}",
                                 "only project directories may be added to the python-path")
            paths.append(str(p))
    else:
        paths = [str(root / d) for d in ("libraries", "resources") if (root / d).is_dir()]
    items = resolve_inputs(inputs, paths, root)
    libraries: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    for item in items:
        data = _load_one(item, paths, root, list(init_args or []), timeout, debug)
        if data.get("ok"):
            entry = {"input": item["input"], "library": data["library"], "keywords": data["keywords"],
                     "findings": list(data["findings"])}
            raw = data.get("raw_output")
            if raw:
                seen = {f["message"] for f in entry["findings"] if f["id"] == "output_during_import"}
                for line in [ln for ln in raw.splitlines() if ln.strip()]:
                    f = _output_finding(line.strip())
                    if f["message"] not in seen and not any(line.strip() in s for s in seen):
                        entry["findings"].append(f)
                        seen.add(f["message"])
            outs = [f for f in entry["findings"] if f["id"] == "output_during_import"]
            if len(outs) > MAX_OUTPUT_FINDINGS:
                drop = {id(f) for f in outs[MAX_OUTPUT_FINDINGS:]}
                entry["findings"] = [f for f in entry["findings"] if id(f) not in drop]
        else:
            entry = {"input": item["input"], "library": None, "keywords": [],
                     "findings": [_finding("import_failed", "error", data["error"], data.get("hint"))]}
            failures.append({"input": item["input"], "error": _cap(data["error"]), "hint": data.get("hint")})
        for f in entry["findings"]:
            counts[f["severity"]] = counts.get(f["severity"], 0) + 1
        libraries.append(_bounded(entry, max_keywords, max_findings))
    summary: Dict[str, int] = {"libraries": len(libraries),
                               "loaded": sum(1 for lib in libraries if lib["library"])}
    summary.update({sev: counts.get(sev, 0) for sev in SEVERITY_ORDER})
    result = {"schema_version": SCHEMA_VERSION, "robot_version": version, "libraries": libraries,
              "summary": summary}
    return result, failures


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

EPILOG = """\
examples:
  uv run python scripts/check_library.py libraries/Inventory.py
  uv run python scripts/check_library.py libraries/*.py --pretty
  uv run python scripts/check_library.py Client --init-arg https://staging.example.com --pythonpath libraries
  uv run python scripts/check_library.py libraries/Inventory.py --json-out results/check_library.json

The script path is relative to the rf-python-library skill directory; library
paths are relative to the project root (the working directory). Not using uv?
Run it with the project's interpreter (.venv/bin/python or poetry run python);
see rf-setup. Loading a library runs its import and __init__ code: check your
own project libraries only.
exit codes: 0 checked (findings do not change it), 1 internal error, 2 usage,
3 environment (robotframework>=7 missing), 4 input missing or outside the
project root, or every library failed to load.
"""


class _Parser(argparse.ArgumentParser):
    """argparse with ``error:``/``hint:`` stderr lines and exit code 2."""

    def error(self, message: str) -> NoReturn:  # type: ignore[override]
        _fail(EXIT_USAGE, message, f"see the options and examples: uv run python {SCRIPT_PATH} --help")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        description="Check Robot Framework keyword libraries written in Python and print JSON on stdout.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("inputs", nargs="+", metavar="LIBRARY",
                        help="library .py file, package directory or import name (e.g. Inventory)")
    parser.add_argument("--init-arg", action="append", default=[], metavar="VALUE",
                        help="library init argument (repeatable; only with a single LIBRARY)")
    parser.add_argument("--pythonpath", action="append", default=[], metavar="DIR",
                        help="python-path entry inside the project (repeatable; default: libraries/ and "
                             "resources/ if they exist, plus the library file's directory)")
    parser.add_argument("--project-root", metavar="DIR",
                        help="only libraries inside DIR are loaded (default: the working directory)")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, metavar="SECONDS",
                        help=f"per-library load timeout (default {DEFAULT_TIMEOUT})")
    parser.add_argument("--max-keywords", type=int, default=DEFAULT_MAX_KEYWORDS, metavar="N",
                        help=f"keywords listed per library (default {DEFAULT_MAX_KEYWORDS}; cut -> omitted.keywords)")
    parser.add_argument("--max-findings", type=int, default=DEFAULT_MAX_FINDINGS, metavar="N",
                        help=f"findings per library (default {DEFAULT_MAX_FINDINGS}; cut -> omitted.findings)")
    parser.add_argument("--json-out", metavar="FILE",
                        help="write the JSON result to FILE; stdout gets {written, bytes, mode}")
    parser.add_argument("--pretty", action="store_true", help="indent the JSON output")
    parser.add_argument("--debug", action="store_true", help="print a traceback on internal errors")
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
    print(json.dumps({"written": json_out, "bytes": len(payload), "mode": "check_library"}))


def _run_cli(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.max_keywords < 0:
        parser.error("--max-keywords must be >= 0")
    if args.max_findings < 0:
        parser.error("--max-findings must be >= 0")
    if args.timeout <= 0:
        parser.error("--timeout must be > 0")
    if args.init_arg and len(args.inputs) > 1:
        parser.error("--init-arg applies to a single LIBRARY; check libraries with init arguments one by one")
    try:
        data, failures = check(args.inputs, init_args=args.init_arg, pythonpath=args.pythonpath,
                               project_root=args.project_root, timeout=args.timeout,
                               max_keywords=args.max_keywords, max_findings=args.max_findings,
                               debug=args.debug)
    except InputError as exc:
        _fail(EXIT_INPUT, str(exc), exc.hint)
    if failures and len(failures) == len(data["libraries"]):
        for fail in failures:
            print(f"error: {fail['input']}: {fail['error']}", file=sys.stderr)
        hints = list(dict.fromkeys(f["hint"] for f in failures if f.get("hint")))
        for hint in hints or [INPUT_HINT]:
            print(f"hint: {hint}", file=sys.stderr)
        return EXIT_INPUT
    for fail in failures:
        _warn(f"{fail['input']}: {fail['error']}")
    emit(data, pretty=args.pretty, json_out=args.json_out)
    return EXIT_OK


def main(argv: Optional[List[str]] = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--_worker"] and len(argv) == 2:
        sys.exit(run_worker(argv[1]))
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        code = _run_cli(args, parser)
    except SystemExit:
        raise
    except Exception as exc:
        if args.debug:
            traceback.print_exc(file=sys.stderr)
        _fail(EXIT_INTERNAL, f"internal: {type(exc).__name__}: {exc}", "re-run with --debug for a traceback")
    sys.exit(code)


if __name__ == "__main__":
    main()
