#!/usr/bin/env python3
"""
Robot Framework Tools MCP Server

An MCP (Model Context Protocol) server that exposes the skills' Python scripts
as structured tools. This allows Claude Code to call RF utilities directly as
tool invocations rather than constructing bash commands.

Design decisions:
  - Uses the MCP SDK's stdio transport for Claude Code integration.
  - Wraps each skill script as MCP tools: rf_libdoc_search and
    rf_libdoc_explain (skill rf-libdoc, scripts/rf_libdoc.py),
    rf_results_analyze (skill rf-results, scripts/rf_results.py),
    rf_conventions (skill rf-language, scripts/rf_conventions.py) and
    rf_check_library (skill rf-python-library, scripts/check_library.py). Scripts are
    located relative to this file in each skill's own scripts/ directory:
    <plugin_root>/skills/<skill>/scripts/<name>.py.
  - All tools return the scripts' JSON unchanged.
  - Execution strategy per call:
      * in-process (fast, cached modules) when this server's interpreter can
        import Robot Framework >= 7 and every library the request names;
      * otherwise the same script runs in a subprocess with the PROJECT
        interpreter detected from the working directory: a uv project
        (uv.lock + uv on PATH -> `uv run --frozen python`), then `.venv`,
        then $VIRTUAL_ENV. Timeout 120 s; the script's exit codes 3/4 become
        tool errors carrying the script's `hint:` lines.
  - rf_check_library ALWAYS runs as a subprocess (project interpreter, else
    this server's interpreter when it has Robot Framework): the checker imports
    the user's library code, which must never be imported into this
    long-lived process (stale modules after edits, sys.path pollution, side
    effects). The project root is the server's working directory.
  - Script errors never terminate the server.

Usage:
  This server is registered in the plugin's .mcp.json and started automatically
  by Claude Code when the plugin is loaded. It only needs the `mcp` package.
  When the interpreter that starts it (python3 on PATH) lacks `mcp` -- the
  normal case on a fresh machine -- it re-launches itself once through
  `uv run --no-project --with "mcp>=1,<2"`; without uv it exits with a hint.

  Manual start for testing:
    python servers/rf-tools-server.py
"""

import json
import os
import shutil
import subprocess
import sys
import importlib.util
from typing import Any, Dict, List, Optional, Sequence


# ---------------------------------------------------------------------------
# MCP SDK imports -- the server gracefully degrades if mcp is not installed.
# ---------------------------------------------------------------------------
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
    HAS_MCP = True
except ImportError:
    HAS_MCP = False


# ---------------------------------------------------------------------------
# Resolve script paths relative to this server file.
# ---------------------------------------------------------------------------
_SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
_PLUGIN_ROOT = os.path.dirname(_SERVER_DIR)
_SKILLS_DIR = os.path.join(_PLUGIN_ROOT, "skills")

_SCRIPT_PATHS = {
    "rf_libdoc": os.path.join(_SKILLS_DIR, "rf-libdoc", "scripts", "rf_libdoc.py"),
    "rf_results": os.path.join(_SKILLS_DIR, "rf-results", "scripts", "rf_results.py"),
    "rf_conventions": os.path.join(_SKILLS_DIR, "rf-language", "scripts", "rf_conventions.py"),
    "check_library": os.path.join(_SKILLS_DIR, "rf-python-library", "scripts", "check_library.py"),
}

CONVENTIONS_HINT = (
    "pass the project root (the directory holding tests/ and resources/) as 'path', "
    "or omit it to scan the working directory"
)

SUBPROCESS_TIMEOUT = 120
MIN_RF_MAJOR = 7

ENV_HINTS = (
    "add Robot Framework to the project: uv add robotframework",
    "not using uv? create the project environment (.venv) or activate it before starting "
    "Claude Code; see the rf-setup skill",
)


class ToolError(Exception):
    """A tool failure with actionable hints (returned to the client, never fatal)."""

    def __init__(self, message: str, hints: Sequence[str] = (), exit_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.hints = list(hints)
        self.exit_code = exit_code

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {"error": str(self)}
        if self.hints:
            data["hints"] = self.hints
        if self.exit_code is not None:
            data["exit_code"] = self.exit_code
        return data


_MODULE_CACHE: Dict[str, Any] = {}
_IMPORTABLE_CACHE: Dict[str, bool] = {}
_ROBOT_OK: Optional[bool] = None


def _load_module(name: str, path: str):
    """Dynamically import a Python module from a file path, with caching."""
    if name in _MODULE_CACHE:
        return _MODULE_CACHE[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _MODULE_CACHE[name] = module
    return module


# ---------------------------------------------------------------------------
# Execution strategy: in-process capability check + project interpreter
# ---------------------------------------------------------------------------

def _robot_ok() -> bool:
    """True when this interpreter has Robot Framework >= 7 (cached)."""
    global _ROBOT_OK
    if _ROBOT_OK is None:
        try:
            if importlib.util.find_spec("robot") is None:
                _ROBOT_OK = False
            else:
                from robot.version import VERSION
                _ROBOT_OK = int(str(VERSION).split(".")[0]) >= MIN_RF_MAJOR
        except Exception:
            _ROBOT_OK = False
    return _ROBOT_OK


def _library_importable(name: str) -> bool:
    """Whether library ``name`` can be imported by this interpreter (cached).

    Only module-style library names are checked; file paths (resources,
    ``.py`` files, specs) are resolved by the script itself.
    """
    base = name.split("::", 1)[0].strip()
    if not base or "/" in base or "\\" in base or base.endswith(
        (".py", ".resource", ".robot", ".xml", ".json", ".libspec")
    ):
        return True
    if base in _IMPORTABLE_CACHE:
        return _IMPORTABLE_CACHE[base]
    ok = False
    for candidate in (base, f"robot.libraries.{base}"):
        try:
            if importlib.util.find_spec(candidate) is not None:
                ok = True
                break
        except (ImportError, ValueError):
            continue
    _IMPORTABLE_CACHE[base] = ok
    return ok


def _can_run_in_process(libraries: Sequence[str] = ()) -> bool:
    return _robot_ok() and all(_library_importable(lib) for lib in libraries)


def _project_python(cwd: Optional[str] = None) -> Optional[List[str]]:
    """Command prefix for the project interpreter, detected from ``cwd``.

    Order: uv project (``uv.lock`` and ``uv`` on PATH) -> ``.venv`` ->
    ``$VIRTUAL_ENV``. Returns ``None`` when nothing is found.
    """
    cwd = cwd or os.getcwd()
    uv = shutil.which("uv")
    if uv and os.path.isfile(os.path.join(cwd, "uv.lock")):
        return [uv, "run", "--frozen", "python"]
    rel = ("Scripts", "python.exe") if os.name == "nt" else ("bin", "python")
    venv_py = os.path.join(cwd, ".venv", *rel)
    if os.path.isfile(venv_py):
        return [venv_py]
    venv = os.environ.get("VIRTUAL_ENV")
    if venv:
        candidate = os.path.join(venv, *rel)
        if os.path.isfile(candidate):
            return [candidate]
    return None


def _parse_stderr(stderr: str) -> Dict[str, Any]:
    errors, hints = [], []
    for line in (stderr or "").splitlines():
        if line.startswith("error: "):
            errors.append(line[len("error: "):])
        elif line.startswith("hint: "):
            hints.append(line[len("hint: "):])
    return {"errors": errors, "hints": hints}


def _run_subprocess(script: str, args: List[str], cwd: Optional[str] = None,
                    prefix: Optional[List[str]] = None, timeout: int = SUBPROCESS_TIMEOUT) -> Dict[str, Any]:
    """Run ``script`` with the project interpreter (or ``prefix``) and return its JSON."""
    prefix = prefix or _project_python(cwd)
    if prefix is None:
        raise ToolError(
            f"Robot Framework >= {MIN_RF_MAJOR} (or a requested library) is not importable by the "
            f"MCP server's interpreter ({sys.executable}) and no project environment "
            "(uv.lock, .venv or $VIRTUAL_ENV) was found in the working directory",
            ENV_HINTS,
            exit_code=3,
        )
    cmd = prefix + [script] + args
    try:
        proc = subprocess.run(
            cmd, cwd=cwd or os.getcwd(), capture_output=True, text=True,
            timeout=timeout, stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        raise ToolError(f"script timed out after {timeout}s: {' '.join(cmd)}",
                        ["narrow the request (fewer libraries / sections) and retry"])
    except OSError as exc:
        raise ToolError(f"could not start the project interpreter {prefix[0]}: {exc}", ENV_HINTS)
    if proc.returncode != 0:
        diag = _parse_stderr(proc.stderr)
        message = "; ".join(diag["errors"]) or (proc.stderr.strip() or f"exit code {proc.returncode}")
        raise ToolError(message, diag["hints"] or ENV_HINTS, exit_code=proc.returncode)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ToolError(f"script printed invalid JSON: {exc}", ["re-run the script with --debug"])


def _libdoc_in_process(libraries: List[str], resources: List[str], **kwargs: Any) -> Dict[str, Any]:
    mod = _load_module("rf_libdoc", _SCRIPT_PATHS["rf_libdoc"])
    load_errors: List[Dict[str, str]] = []
    libs = mod._load_docs(
        libraries=libraries,
        resources=resources,
        suites=[],
        specs=[],
        name="",
        version="",
        doc_format=None,
        errors=load_errors,
    )
    if not libs and load_errors:
        raise ToolError(
            "none of the requested source(s) could be loaded: "
            + "; ".join(f"{e['source']}: {mod._first_line(e['error'])}" for e in load_errors),
            [mod._source_hint(e["source"]) for e in load_errors],
            exit_code=4,
        )
    return mod.build_response(libs, load_errors=load_errors, **kwargs)


def _libdoc_args(libraries: List[str], resources: List[str], *, keyword: Optional[str] = None,
                 search: Optional[str] = None, weights: str = "", limit: int = 20,
                 include_private: bool = False, exclude_deprecated: bool = False,
                 tags: Optional[List[str]] = None, include_library_doc: bool = False,
                 max_doc_chars: Optional[int] = None) -> List[str]:
    args: List[str] = []
    for lib in libraries:
        args += ["--library", lib]
    for res in resources:
        args += ["--resource", res]
    if keyword:
        args += ["--keyword", keyword]
    if search:
        args += ["--search", search]
    if weights:
        args += ["--weights", weights]
    args += ["--limit", str(limit)]
    if include_private:
        args.append("--include-private")
    if exclude_deprecated:
        args.append("--exclude-deprecated")
    for tag in tags or []:
        args += ["--tag", tag]
    if include_library_doc:
        args.append("--include-library-doc")
    if max_doc_chars is not None:
        args += ["--max-doc-chars", str(max_doc_chars)]
    return args


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def tool_libdoc_search(
    libraries: List[str],
    search: str,
    resources: Optional[List[str]] = None,
    weights: Optional[str] = None,
    limit: int = 20,
    include_private: bool = False,
    exclude_deprecated: bool = False,
    tags: Optional[List[str]] = None,
    include_library_doc: bool = False,
    max_doc_chars: Optional[int] = None,
) -> Dict[str, Any]:
    """Search Robot Framework libraries for keywords matching a use case.

    Returns the unified rf_libdoc schema: ``{schema_version, mode, libraries,
    results, ...}`` (mode ``search``). Library prose ``doc`` is omitted unless
    ``include_library_doc=True``.
    """
    resources = resources or []
    if not _can_run_in_process(libraries):
        return _run_subprocess(_SCRIPT_PATHS["rf_libdoc"], _libdoc_args(
            libraries, resources, search=search, weights=weights or "", limit=limit,
            include_private=include_private, exclude_deprecated=exclude_deprecated,
            tags=tags, include_library_doc=include_library_doc, max_doc_chars=max_doc_chars,
        ))
    mod = _load_module("rf_libdoc", _SCRIPT_PATHS["rf_libdoc"])
    extra = {} if max_doc_chars is None else {"max_doc_chars": max_doc_chars}
    return _libdoc_in_process(
        libraries, resources,
        search=search,
        weights=mod._parse_weights(weights or ""),
        limit=limit,
        include_private=include_private,
        exclude_deprecated=exclude_deprecated,
        tags=tags or [],
        include_library_doc=include_library_doc,
        **extra,
    )


def tool_libdoc_explain(
    libraries: List[str],
    keyword: str,
    resources: Optional[List[str]] = None,
    search_fallback: Optional[str] = None,
    include_private: bool = False,
    exclude_deprecated: bool = False,
    include_library_doc: bool = False,
    max_doc_chars: Optional[int] = None,
) -> Dict[str, Any]:
    """Explain a Robot Framework keyword with full argument details.

    Returns the unified rf_libdoc schema (mode ``explain`` on an exact match,
    else ``fallback`` with search suggestions).
    """
    resources = resources or []
    if not _can_run_in_process(libraries):
        return _run_subprocess(_SCRIPT_PATHS["rf_libdoc"], _libdoc_args(
            libraries, resources, keyword=keyword, search=search_fallback, limit=10,
            include_private=include_private, exclude_deprecated=exclude_deprecated,
            include_library_doc=include_library_doc, max_doc_chars=max_doc_chars,
        ))
    mod = _load_module("rf_libdoc", _SCRIPT_PATHS["rf_libdoc"])
    extra = {} if max_doc_chars is None else {"max_doc_chars": max_doc_chars}
    return _libdoc_in_process(
        libraries, resources,
        keyword=keyword,
        search=search_fallback,
        weights=mod._parse_weights(""),
        limit=10,
        include_private=include_private,
        exclude_deprecated=exclude_deprecated,
        include_library_doc=include_library_doc,
        **extra,
    )


def tool_results_analyze(
    output: Optional[str] = None,
    outputs: Optional[List[str]] = None,
    sections: str = "summary",
    merge: bool = False,
    name: str = "",
    include_keyword_timing: bool = False,
    max_slowest_tests: int = 10,
    max_slowest_keywords: int = 10,
    limit: int = 50,
) -> Dict[str, Any]:
    """Parse Robot Framework output.xml and return structured results."""
    paths: List[str] = []
    if output:
        paths.append(output)
    if outputs:
        paths.extend(outputs)
    if not paths:
        return {"error": "Provide 'output' or 'outputs' parameter."}

    for p in paths:
        if not os.path.exists(p):
            return {"error": f"File not found: {p}",
                    "hints": ["run the tests first or pass the correct output.xml path"]}

    if not _can_run_in_process():
        args: List[str] = []
        if output:
            args += ["--output", output]
        if outputs:
            args += ["--outputs", *outputs]
        args += ["--sections", sections, "--limit", str(limit),
                 "--max-slowest-tests", str(max_slowest_tests),
                 "--max-slowest-keywords", str(max_slowest_keywords)]
        if merge:
            args.append("--merge")
        if name:
            args += ["--name", name]
        if include_keyword_timing:
            args.append("--include-keyword-timing")
        return _run_subprocess(_SCRIPT_PATHS["rf_results"], args)

    mod = _load_module("rf_results", _SCRIPT_PATHS["rf_results"])
    parsed_sections = mod._parse_sections(sections)
    if not parsed_sections:
        return {"error": "No valid sections requested. Use: summary, details, errors, timing, or all."}

    try:
        result, merged = mod._load_result(paths, merge, name)
    except Exception as e:
        return {"error": f"Failed to load output file(s): {e}"}

    visitor = mod.CollectVisitor(include_keywords=include_keyword_timing)
    result.visit(visitor)

    return mod.build_output(
        result, visitor, parsed_sections, include_keyword_timing,
        max_slowest_tests, max_slowest_keywords, paths, merged, limit=limit,
    )


def tool_conventions(
    path: Optional[str] = None,
    max_examples: int = 3,
    max_files: int = 2000,
) -> Dict[str, Any]:
    """Detect a Robot Framework project's conventions (rf-conventions/1 JSON).

    Returns exactly what ``rf_conventions.py <path> --max-examples N
    --max-files N`` prints. ``path`` defaults to the server's working directory.
    """
    target = os.path.abspath(os.path.expanduser(path or os.getcwd()))
    if not os.path.exists(target):
        raise ToolError(f"path not found: {path}", [CONVENTIONS_HINT], exit_code=4)
    if not os.path.isdir(target):
        raise ToolError(f"not a directory: {path}", [CONVENTIONS_HINT], exit_code=4)
    if not _can_run_in_process():
        return _run_subprocess(
            _SCRIPT_PATHS["rf_conventions"],
            [target, "--max-examples", str(max_examples), "--max-files", str(max_files)],
            cwd=target,
        )
    mod = _load_module("rf_conventions", _SCRIPT_PATHS["rf_conventions"])
    try:
        return mod.run(target, max_files=max_files, max_examples=max_examples)
    except mod.InputError as exc:
        raise ToolError(str(exc), [exc.hint], exit_code=4)


def tool_check_library(
    libraries: List[str],
    init_args: Optional[List[str]] = None,
    pythonpath: Optional[List[str]] = None,
    max_keywords: int = 100,
    max_findings: int = 50,
    timeout: float = 30,
) -> Dict[str, Any]:
    """Check project keyword libraries (check_library.py JSON, schema_version 1).

    Always a subprocess, never in-process: the checker imports and initialises
    the user's library code. Project root = this server's working directory.
    """
    if not libraries or not isinstance(libraries, list):
        raise ToolError("'libraries' must be a non-empty list of library files or import names",
                        ["for example: {\"libraries\": [\"libraries/Inventory.py\"]}"], exit_code=2)
    cwd = os.getcwd()
    args: List[str] = [str(lib) for lib in libraries]
    for value in init_args or []:
        args += ["--init-arg", str(value)]
    for entry in pythonpath or []:
        args += ["--pythonpath", str(entry)]
    args += ["--max-keywords", str(int(max_keywords)), "--max-findings", str(int(max_findings)),
             "--timeout", str(timeout)]
    prefix = _project_python(cwd) or ([sys.executable] if _robot_ok() else None)
    budget = int(float(timeout) * len(libraries)) + 30
    return _run_subprocess(_SCRIPT_PATHS["check_library"], args, cwd=cwd, prefix=prefix,
                           timeout=max(budget, SUBPROCESS_TIMEOUT))


# ---------------------------------------------------------------------------
# MCP Server definition
# ---------------------------------------------------------------------------

def create_server() -> "Server":
    """Create and configure the MCP server with all RF tools."""
    server = Server("rf-tools")

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name="rf_libdoc_search",
                description=(
                    "Search Robot Framework library keywords by use case. "
                    "Finds keywords whose name, short_doc, or doc match the search query. "
                    "Use this to discover which keywords are available for an automation task."
                ),
                inputSchema={
                    "type": "object",
                    "required": ["libraries", "search"],
                    "properties": {
                        "libraries": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Library names to search (e.g., ['BuiltIn', 'Browser'])",
                        },
                        "search": {
                            "type": "string",
                            "description": "Search query describing the desired action (e.g., 'click button')",
                        },
                        "resources": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional resource file paths to also search",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results (default 20)",
                            "default": 20,
                        },
                        "include_private": {
                            "type": "boolean",
                            "description": "Include private keywords",
                            "default": False,
                        },
                        "exclude_deprecated": {
                            "type": "boolean",
                            "description": "Exclude deprecated keywords",
                            "default": False,
                        },
                        "max_doc_chars": {
                            "type": "integer",
                            "description": "Cap each keyword doc at N characters (default 4000; 0 = full text)",
                        },
                    },
                },
            ),
            Tool(
                name="rf_libdoc_explain",
                description=(
                    "Explain a Robot Framework keyword with full argument details. "
                    "Returns the keyword's documentation, required/optional arguments, "
                    "defaults, and usage information."
                ),
                inputSchema={
                    "type": "object",
                    "required": ["libraries", "keyword"],
                    "properties": {
                        "libraries": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Library names to search in",
                        },
                        "keyword": {
                            "type": "string",
                            "description": "Exact keyword name to explain",
                        },
                        "resources": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional resource file paths",
                        },
                        "search_fallback": {
                            "type": "string",
                            "description": "Fallback search query if exact match not found",
                        },
                        "max_doc_chars": {
                            "type": "integer",
                            "description": "Cap each keyword doc at N characters (default 4000; 0 = full text)",
                        },
                    },
                },
            ),
            Tool(
                name="rf_results_analyze",
                description=(
                    "Parse Robot Framework output.xml files and return structured JSON results. "
                    "Supports summary totals, detailed suite/test breakdowns, tag statistics, "
                    "execution errors, failed test messages, and timing analysis."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "output": {
                            "type": "string",
                            "description": "Path to a single output.xml file",
                        },
                        "outputs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Paths to multiple output.xml files to merge/combine",
                        },
                        "sections": {
                            "type": "string",
                            "description": "Comma-separated sections: summary, details, errors, timing, or all",
                            "default": "summary",
                        },
                        "merge": {
                            "type": "boolean",
                            "description": "Use rebot merge behavior for multiple outputs",
                            "default": False,
                        },
                        "include_keyword_timing": {
                            "type": "boolean",
                            "description": "Include keyword-level timing data",
                            "default": False,
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Cap test entries in details (failed first) and each errors list (default 50; 0 = unlimited)",
                            "default": 50,
                        },
                    },
                },
            ),
            Tool(
                name="rf_conventions",
                description=(
                    "Detect a Robot Framework project's conventions before writing .robot or "
                    ".resource code: RF version and available features (typed arguments, VAR, "
                    "GROUP...), separator and assignment style, keyword naming, embedded and typed "
                    "arguments, BDD and template usage, tags, legacy constructs with Robocop rule "
                    "ids, resource/variable-file layout and the web library in use. Read-only."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Project directory to scan (default: the working directory)",
                        },
                        "max_examples": {
                            "type": "integer",
                            "description": "Examples per list (default 3; 0 = none)",
                            "default": 3,
                        },
                        "max_files": {
                            "type": "integer",
                            "description": "Scan at most N .robot/.resource files (default 2000)",
                            "default": 2000,
                        },
                    },
                },
            ),
            Tool(
                name="rf_check_library",
                description=(
                    "Check Robot Framework keyword libraries written in Python (the project's own "
                    "libraries/*.py) before running tests: keywords with arguments, scope and API "
                    "style, plus findings such as import/init failures, 'contains no keywords', "
                    "leaked imported functions, methods hidden by @library, lost signatures, str in "
                    "unions and state kept in a TEST-scope library. Runs the library's import and "
                    "__init__ in a child process of the project environment; only paths inside the "
                    "working directory are accepted."
                ),
                inputSchema={
                    "type": "object",
                    "required": ["libraries"],
                    "properties": {
                        "libraries": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Library .py files, package directories or import names "
                                           "(e.g. ['libraries/Inventory.py'])",
                        },
                        "init_args": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Library init arguments (only with a single library)",
                        },
                        "pythonpath": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Python-path entries inside the project "
                                           "(default: libraries/ and resources/)",
                        },
                        "max_keywords": {
                            "type": "integer",
                            "description": "Keywords listed per library (default 100)",
                            "default": 100,
                        },
                        "max_findings": {
                            "type": "integer",
                            "description": "Findings per library (default 50)",
                            "default": 50,
                        },
                        "timeout": {
                            "type": "number",
                            "description": "Per-library load timeout in seconds (default 30)",
                            "default": 30,
                        },
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        try:
            if name == "rf_libdoc_search":
                result = tool_libdoc_search(**arguments)
            elif name == "rf_libdoc_explain":
                result = tool_libdoc_explain(**arguments)
            elif name == "rf_results_analyze":
                result = tool_results_analyze(**arguments)
            elif name == "rf_conventions":
                result = tool_conventions(**arguments)
            elif name == "rf_check_library":
                result = tool_check_library(**arguments)
            else:
                result = {"error": f"Unknown tool: {name}"}

            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2),
            )]
        except ToolError as e:
            return [TextContent(type="text", text=json.dumps(e.to_dict(), indent=2))]
        except (Exception, SystemExit) as e:
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )]

    return server


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

#: Set on the re-launched process so a missing `mcp` cannot loop.
_BOOTSTRAP_ENV = "RF_TOOLS_MCP_BOOTSTRAPPED"
_MCP_REQUIREMENT = "mcp>=1,<2"


def _bootstrap_command() -> Optional[List[str]]:
    """Command that re-runs this server in an interpreter with `mcp`, or None."""
    if os.environ.get(_BOOTSTRAP_ENV):
        return None
    uv = shutil.which("uv")
    if uv is None:
        return None
    # --no-project: never resolve (or modify) the user's project from its CWD.
    return [uv, "run", "--quiet", "--no-project", "--with", _MCP_REQUIREMENT,
            "python", os.path.abspath(__file__)]


def _relaunch_with_mcp() -> Optional[int]:
    """Re-run the server with `mcp` via uv; returns its exit code (None: not possible).

    POSIX replaces this process so the client keeps one PID on its stdio;
    Windows has no real exec, so the child inherits stdio and we wait for it.
    """
    cmd = _bootstrap_command()
    if cmd is None:
        return None
    env = dict(os.environ, **{_BOOTSTRAP_ENV: "1"})
    if os.name == "posix":
        os.execvpe(cmd[0], cmd, env)
    return subprocess.call(cmd, env=env)


async def main():
    """Run the MCP server on stdio."""
    if not HAS_MCP:
        print(
            "rf-tools: the MCP SDK (`mcp` package) is not installed for "
            f"{sys.executable}, and uv was not found to provide it.\n"
            "Fix: install uv (https://docs.astral.sh/uv/) -- the server then fetches "
            f"'{_MCP_REQUIREMENT}' itself -- or run `{sys.executable} -m pip install "
            f"\"{_MCP_REQUIREMENT}\"`.",
            file=sys.stderr,
        )
        sys.exit(1)

    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    if not HAS_MCP:
        code = _relaunch_with_mcp()
        if code is not None:
            sys.exit(code)
    asyncio.run(main())
