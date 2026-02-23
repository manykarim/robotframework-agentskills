#!/usr/bin/env python3
"""
Robot Framework Tools MCP Server

An MCP (Model Context Protocol) server that exposes the plugin's Python scripts
as structured tools. This allows Claude Code to call RF utilities directly as
tool invocations rather than constructing bash commands.

Design decisions:
  - Uses the MCP SDK's stdio transport for Claude Code integration.
  - Wraps each Python script (rf_libdoc.py, rf_results.py, keyword_builder.py,
    testcase_builder.py, resource_architect.py) as a separate MCP tool.
  - All tools return JSON (matching the scripts' existing output format).
  - Input validation is handled at the MCP schema level before invoking scripts.
  - Scripts are imported as modules rather than spawned as subprocesses to avoid
    startup overhead and to share the Python interpreter.
  - Falls back gracefully if robotframework is not installed.

Usage:
  This server is registered in the plugin's .mcp.json and started automatically
  by Claude Code when the plugin is loaded.

  Manual start for testing:
    python servers/rf-tools-server.py
"""

import json
import os
import sys
import importlib.util
import tempfile
from io import StringIO
from typing import Any, Dict, List, Optional


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
    "rf_libdoc": os.path.join(_SKILLS_DIR, "robotframework-libdoc-search", "scripts", "rf_libdoc.py"),
    "rf_results": os.path.join(_SKILLS_DIR, "robotframework-results", "scripts", "rf_results.py"),
    "keyword_builder": os.path.join(_SKILLS_DIR, "robotframework-keyword-builder", "scripts", "keyword_builder.py"),
    "testcase_builder": os.path.join(_SKILLS_DIR, "robotframework-testcase-builder", "scripts", "testcase_builder.py"),
    "resource_architect": os.path.join(_SKILLS_DIR, "robotframework-resource-architect", "scripts", "resource_architect.py"),
}


def _load_module(name: str, path: str):
    """Dynamically import a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _capture_stdout(func, *args, **kwargs) -> str:
    """Capture stdout from a function call and return it as a string."""
    old_stdout = sys.stdout
    sys.stdout = StringIO()
    try:
        func(*args, **kwargs)
        return sys.stdout.getvalue()
    finally:
        sys.stdout = old_stdout


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
) -> Dict[str, Any]:
    """Search Robot Framework libraries for keywords matching a use case."""
    mod = _load_module("rf_libdoc", _SCRIPT_PATHS["rf_libdoc"])

    load_errors: List[Dict[str, str]] = []
    libs = mod._load_docs(
        libraries=libraries,
        resources=resources or [],
        suites=[],
        specs=[],
        name="",
        version="",
        doc_format=None,
        errors=load_errors,
    )
    parsed_weights = mod._parse_weights(weights or "")

    data: Dict[str, Any] = {
        "libraries": [mod._library_meta(lib) for lib in libs],
    }
    if load_errors:
        data["errors"] = load_errors

    data["query"] = search
    data["matches"] = mod._search_keywords(
        libs, search, parsed_weights, limit,
        include_private, exclude_deprecated, tags or [],
    )
    if not data["matches"]:
        data["hint"] = "No keyword matches found. Try a broader search or adjust weights."

    return data


def tool_libdoc_explain(
    libraries: List[str],
    keyword: str,
    resources: Optional[List[str]] = None,
    search_fallback: Optional[str] = None,
    include_private: bool = False,
    exclude_deprecated: bool = False,
) -> Dict[str, Any]:
    """Explain a Robot Framework keyword with full argument details."""
    mod = _load_module("rf_libdoc", _SCRIPT_PATHS["rf_libdoc"])

    load_errors: List[Dict[str, str]] = []
    libs = mod._load_docs(
        libraries=libraries,
        resources=resources or [],
        suites=[],
        specs=[],
        name="",
        version="",
        doc_format=None,
        errors=load_errors,
    )

    data: Dict[str, Any] = {
        "libraries": [mod._library_meta(lib) for lib in libs],
    }
    if load_errors:
        data["errors"] = load_errors

    matches = mod._find_keyword(libs, keyword, include_private, exclude_deprecated, [])
    if matches:
        data["keyword_matches"] = matches
    elif search_fallback:
        weights = mod._parse_weights("")
        data["matches"] = mod._search_keywords(
            libs, search_fallback, weights, 10,
            include_private, exclude_deprecated, [],
        )
        if not data["matches"]:
            data["hint"] = "No keyword matches found."
    else:
        data["hint"] = f"Keyword '{keyword}' not found. Try providing a search_fallback."

    return data


def tool_results_analyze(
    output: Optional[str] = None,
    outputs: Optional[List[str]] = None,
    sections: str = "summary",
    merge: bool = False,
    name: str = "",
    include_keyword_timing: bool = False,
    max_slowest_tests: int = 10,
    max_slowest_keywords: int = 10,
) -> Dict[str, Any]:
    """Parse Robot Framework output.xml and return structured results."""
    mod = _load_module("rf_results", _SCRIPT_PATHS["rf_results"])

    paths: List[str] = []
    if output:
        paths.append(output)
    if outputs:
        paths.extend(outputs)
    if not paths:
        return {"error": "Provide 'output' or 'outputs' parameter."}

    for p in paths:
        if not os.path.exists(p):
            return {"error": f"File not found: {p}"}

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
        max_slowest_tests, max_slowest_keywords, paths, merged,
    )


def tool_keyword_builder(
    keyword_name: str,
    steps: List[Dict[str, Any]],
    description: str = "",
    arguments: Optional[List[Dict[str, Any]]] = None,
    tags: Optional[List[str]] = None,
    setup: Optional[Dict[str, Any]] = None,
    teardown: Optional[Dict[str, Any]] = None,
    return_value: Optional[Any] = None,
    style: str = "simple",
    detect_embedded: bool = False,
    project_root: str = ".",
) -> Dict[str, Any]:
    """Generate a Robot Framework user keyword from structured input."""
    data = {
        "keyword_name": keyword_name,
        "description": description,
        "arguments": arguments or [],
        "tags": tags or [],
        "steps": steps,
        "style": style,
    }
    if setup:
        data["setup"] = setup
    if teardown:
        data["teardown"] = teardown
    if return_value is not None:
        data["return_value"] = return_value

    # Write to temp file and invoke the script's main logic
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, tmp)
    tmp.close()

    try:
        old_argv = sys.argv
        sys.argv = ["keyword_builder.py", "--input", tmp.name]
        if detect_embedded:
            sys.argv.extend(["--detect-embedded", "--project-root", project_root])

        output = _capture_stdout(
            _load_module("keyword_builder", _SCRIPT_PATHS["keyword_builder"]).main
        )
        return json.loads(output)
    except SystemExit:
        return {"error": "keyword_name is required"}
    finally:
        sys.argv = old_argv
        os.unlink(tmp.name)


def tool_testcase_builder(
    tests: List[Dict[str, Any]],
    style: str = "keyword-driven",
    allow_control: bool = False,
) -> Dict[str, Any]:
    """Generate Robot Framework test cases from structured input."""
    data = {
        "style": style,
        "tests": tests,
    }

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, tmp)
    tmp.close()

    try:
        old_argv = sys.argv
        sys.argv = ["testcase_builder.py", "--input", tmp.name]
        if allow_control:
            sys.argv.append("--allow-control")

        output = _capture_stdout(
            _load_module("testcase_builder", _SCRIPT_PATHS["testcase_builder"]).main
        )
        return json.loads(output)
    except SystemExit:
        return {"error": "tests array is required"}
    finally:
        sys.argv = old_argv
        os.unlink(tmp.name)


def tool_resource_architect(
    domains: List[str],
    libraries: Optional[List[str]] = None,
    environments: Optional[List[str]] = None,
    project_root: str = ".",
    resource_naming: str = "by-domain",
    variables_format: str = "resource",
    write: bool = False,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Design Robot Framework resource file layout for a project."""
    data = {
        "project_root": project_root,
        "domains": domains,
        "libraries": libraries or [],
        "environments": environments or [],
        "resource_naming": resource_naming,
        "variables_format": variables_format,
    }

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, tmp)
    tmp.close()

    try:
        old_argv = sys.argv
        sys.argv = ["resource_architect.py", "--input", tmp.name]
        if write:
            sys.argv.append("--write")
        if overwrite:
            sys.argv.append("--overwrite")

        output = _capture_stdout(
            _load_module("resource_architect", _SCRIPT_PATHS["resource_architect"]).main
        )
        return json.loads(output)
    except SystemExit:
        return {"error": "Input data is required"}
    finally:
        sys.argv = old_argv
        os.unlink(tmp.name)


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
                    },
                },
            ),
            Tool(
                name="rf_keyword_builder",
                description=(
                    "Generate a Robot Framework user keyword from structured input. "
                    "Produces valid RF keyword syntax with arguments, documentation, "
                    "tags, setup/teardown, and steps."
                ),
                inputSchema={
                    "type": "object",
                    "required": ["keyword_name", "steps"],
                    "properties": {
                        "keyword_name": {
                            "type": "string",
                            "description": "Name of the keyword (Title Case recommended)",
                        },
                        "steps": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Keyword steps: [{\"keyword\": \"Click\", \"args\": [\"#btn\"]}]",
                        },
                        "description": {
                            "type": "string",
                            "description": "Keyword documentation string",
                        },
                        "arguments": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Arguments: [{\"name\": \"url\", \"type\": \"str\", \"default\": null}]",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Keyword tags",
                        },
                        "return_value": {
                            "description": "Return value variable(s)",
                        },
                        "style": {
                            "type": "string",
                            "description": "Keyword style: simple or retry-aware",
                            "default": "simple",
                        },
                    },
                },
            ),
            Tool(
                name="rf_testcase_builder",
                description=(
                    "Generate Robot Framework test cases from structured input. "
                    "Supports keyword-driven and template-driven test styles."
                ),
                inputSchema={
                    "type": "object",
                    "required": ["tests"],
                    "properties": {
                        "tests": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "Test definitions with name, steps, tags, etc.",
                        },
                        "style": {
                            "type": "string",
                            "description": "Test style: keyword-driven or template",
                            "default": "keyword-driven",
                        },
                        "allow_control": {
                            "type": "boolean",
                            "description": "Allow control structures (FOR, IF) in test steps",
                            "default": False,
                        },
                    },
                },
            ),
            Tool(
                name="rf_resource_architect",
                description=(
                    "Design a Robot Framework resource file layout for a project. "
                    "Proposes directory structure, resource files by domain, and "
                    "environment-specific variable files."
                ),
                inputSchema={
                    "type": "object",
                    "required": ["domains"],
                    "properties": {
                        "domains": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Business domains (e.g., ['auth', 'orders', 'payments'])",
                        },
                        "libraries": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "RF libraries to include in resource imports",
                        },
                        "environments": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Environments for variable files (e.g., ['dev', 'qa', 'staging'])",
                        },
                        "project_root": {
                            "type": "string",
                            "description": "Project root path",
                            "default": ".",
                        },
                        "variables_format": {
                            "type": "string",
                            "description": "Variable file format: resource, yaml, or python",
                            "default": "resource",
                        },
                        "write": {
                            "type": "boolean",
                            "description": "Actually write files to disk",
                            "default": False,
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
            elif name == "rf_keyword_builder":
                result = tool_keyword_builder(**arguments)
            elif name == "rf_testcase_builder":
                result = tool_testcase_builder(**arguments)
            elif name == "rf_resource_architect":
                result = tool_resource_architect(**arguments)
            else:
                result = {"error": f"Unknown tool: {name}"}

            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2),
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )]

    return server


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    """Run the MCP server on stdio."""
    if not HAS_MCP:
        print(
            "MCP SDK not installed. Install with: pip install mcp\n"
            "The server requires the 'mcp' package to run.",
            file=sys.stderr,
        )
        sys.exit(1)

    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
