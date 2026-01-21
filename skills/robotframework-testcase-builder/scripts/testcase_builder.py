#!/usr/bin/env python3
import argparse
import json
import re
import sys
from typing import Any, Dict, List, Optional


CONTROL_PREFIXES = ("FOR", "IF", "WHILE", "TRY", "EXCEPT", "ELSE", "END")


def _read_input(path: Optional[str]) -> Dict[str, Any]:
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    raw = sys.stdin.read().strip()
    if not raw:
        raise SystemExit("Provide --input or stdin JSON")
    return json.loads(raw)


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


def _render_test(test: Dict[str, Any], allow_control: bool, warnings: List[str]) -> str:
    lines = [test["name"]]

    doc = test.get("documentation")
    if doc:
        lines.append(f"    [Documentation]    {doc}")

    tags = test.get("tags") or []
    if tags:
        lines.append("    [Tags]    " + "    ".join(tags))

    setup = test.get("setup")
    if setup:
        setup_args = setup.get("args", [])
        lines.append("    [Setup]    " + "    ".join([setup.get("keyword")] + [str(a) for a in setup_args]))

    teardown = test.get("teardown")
    if teardown:
        teardown_args = teardown.get("args", [])
        lines.append("    [Teardown]    " + "    ".join([teardown.get("keyword")] + [str(a) for a in teardown_args]))

    template = test.get("template")
    if template:
        lines.append(f"    [Template]    {template}")
        data_rows = test.get("data_rows") or []
        for row in data_rows:
            lines.append("    " + "    ".join([str(c) for c in row]))
        return "\n".join(lines)

    steps = test.get("steps") or []
    for step in steps:
        rendered = _render_step(step)
        for line in rendered:
            if not allow_control:
                prefix = line.strip().split(" ", 1)[0].upper()
                if prefix in CONTROL_PREFIXES:
                    warnings.append(f"Control structure '{prefix}' found in test '{test['name']}'")
            lines.append("    " + line)

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Robot Framework test case builder")
    parser.add_argument("--input", help="JSON input file")
    parser.add_argument("--allow-control", action="store_true")
    args = parser.parse_args()

    data = _read_input(args.input)
    tests = data.get("tests") or []
    if not tests:
        raise SystemExit("tests array is required")

    warnings: List[str] = []
    suggestions: List[str] = []

    artifacts = []
    for test in tests:
        name = test.get("name", "").strip()
        if not name:
            warnings.append("Test without a name skipped.")
            continue
        if "*" in name or "?" in name:
            warnings.append(f"Test name '{name}' contains wildcard characters.")
        test["name"] = name
        artifacts.append(_render_test(test, args.allow_control, warnings))

    output = {
        "artifact": "\n\n".join(artifacts),
        "warnings": warnings,
        "suggestions": suggestions,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
