#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional


SECTION_KEYWORDS = re.compile(r"^\*\*\*\s*Keywords\s*\*\*\*$", re.IGNORECASE)
SECTION_ANY = re.compile(r"^\*\*\*\s*.+\s*\*\*\*$")


def _read_input(path: Optional[str]) -> Dict[str, Any]:
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    raw = sys.stdin.read().strip()
    if not raw:
        raise SystemExit("Provide --input or stdin JSON")
    return json.loads(raw)


def _title_case(name: str) -> str:
    if not name:
        return name
    return " ".join([part[:1].upper() + part[1:] for part in name.split()])


def _detect_embedded_style(project_root: str) -> bool:
    for root, _, files in os.walk(project_root):
        for filename in files:
            if not (filename.endswith(".robot") or filename.endswith(".resource")):
                continue
            path = os.path.join(root, filename)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    in_keywords = False
                    for line in fh:
                        stripped = line.strip()
                        if not stripped or stripped.startswith("#"):
                            continue
                        if SECTION_KEYWORDS.match(stripped):
                            in_keywords = True
                            continue
                        if SECTION_ANY.match(stripped):
                            in_keywords = False
                            continue
                        if in_keywords:
                            if "${" in stripped or "@{" in stripped or "&{" in stripped:
                                return True
            except OSError:
                continue
    return False


def _format_arguments(arguments: List[Dict[str, Any]]) -> List[str]:
    rendered = []
    for arg in arguments:
        name = arg.get("name", "").strip()
        default = arg.get("default")
        if not name:
            continue
        var = f"${{{name}}}"
        if default is not None:
            var = f"${{{name}}}={default}"
        rendered.append(var)
    return rendered


def _format_doc(description: str, arguments: List[Dict[str, Any]]) -> str:
    doc = (description or "").replace("\n", "\\n").strip()
    typed = [a for a in arguments if a.get("type")]
    if typed:
        parts = [f"{a['name']}: {a['type']}" for a in typed if a.get("name")]
        if parts:
            suffix = "Arguments: " + ", ".join(parts)
            if doc:
                doc = f"{doc} | {suffix}"
            else:
                doc = suffix
    return doc


def _render_step(step: Dict[str, Any]) -> List[str]:
    if "line" in step:
        return [step["line"]]
    keyword = step.get("keyword")
    args = step.get("args", [])
    assigns = step.get("assign", [])
    if not keyword:
        return []
    parts = []
    if assigns:
        parts.extend([str(a) for a in assigns])
    parts.append(keyword)
    parts.extend([str(a) for a in args])
    return ["    ".join(parts)]


def _render_keyword_block(name: str, data: Dict[str, Any], warnings: List[str]) -> str:
    lines = [name]
    description = _format_doc(data.get("description", ""), data.get("arguments", []))
    if description:
        lines.append(f"    [Documentation]    {description}")

    tags = data.get("tags", [])
    if tags:
        lines.append("    [Tags]    " + "    ".join(tags))

    args = _format_arguments(data.get("arguments", []))
    if args:
        lines.append("    [Arguments]    " + "    ".join(args))

    setup = data.get("setup")
    if setup:
        if not setup.get("keyword"):
            warnings.append("Setup provided without keyword.")
        setup_args = setup.get("args", [])
        lines.append("    [Setup]    " + "    ".join([setup.get("keyword")] + [str(a) for a in setup_args]))

    teardown = data.get("teardown")
    if teardown:
        if not teardown.get("keyword"):
            warnings.append("Teardown provided without keyword.")
        teardown_args = teardown.get("args", [])
        lines.append("    [Teardown]    " + "    ".join([teardown.get("keyword")] + [str(a) for a in teardown_args]))

    timeout = data.get("timeout")
    if timeout:
        lines.append(f"    [Timeout]    {timeout}")

    steps = data.get("steps") or []
    if not steps:
        steps = [{"keyword": "Log", "args": ["TODO: implement steps"]}]
        warnings.append("No steps provided. Added TODO Log step.")

    for step in steps:
        for rendered in _render_step(step):
            lines.append("    " + rendered)

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Robot Framework keyword builder")
    parser.add_argument("--input", help="JSON input file")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--detect-embedded", action="store_true")
    parser.add_argument("--force-embedded", action="store_true")
    args = parser.parse_args()

    data = _read_input(args.input)
    warnings: List[str] = []
    suggestions: List[str] = []
    meta: Dict[str, Any] = {}

    keyword_name = data.get("keyword_name", "").strip()
    if not keyword_name:
        raise SystemExit("keyword_name is required")

    if data.get("visibility") == "private" and not keyword_name.startswith("_"):
        keyword_name = f"_{keyword_name}"

    embedded_detected = False
    if args.detect_embedded:
        embedded_detected = _detect_embedded_style(args.project_root)
        meta["embedded_style_detected"] = embedded_detected

    if args.force_embedded and "${" not in keyword_name:
        warnings.append("force-embedded set but keyword_name has no embedded arguments.")
    if embedded_detected and "${" not in keyword_name and not args.force_embedded:
        suggestions.append("Project uses embedded-argument keywords; consider embedding arguments in keyword_name.")

    if keyword_name == _title_case(keyword_name):
        pass
    else:
        suggestions.append("Consider Title Case for keyword name.")

    style = data.get("style", "simple")
    steps = data.get("steps") or []
    if style == "retry-aware":
        if len(steps) == 1 and "keyword" in steps[0]:
            step = steps[0]
            data["steps"] = [
                {
                    "keyword": "Wait Until Keyword Succeeds",
                    "args": ["3x", "1s", step["keyword"]] + step.get("args", []),
                }
            ]
        else:
            warnings.append("retry-aware style requires a single step; keeping steps as-is.")

    artifact = _render_keyword_block(keyword_name, data, warnings)

    output = {
        "artifact": artifact,
        "warnings": warnings,
        "suggestions": suggestions,
        "meta": meta,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
