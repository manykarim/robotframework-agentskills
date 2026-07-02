#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional


RESOURCE_DIR_CANDIDATES = ["resources", "keywords", "res"]


def _read_input(path: Optional[str]) -> Dict[str, Any]:
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    raw = sys.stdin.read().strip()
    if not raw:
        raise SystemExit("Provide --input or stdin JSON")
    return json.loads(raw)


def _detect_resource_dir(project_root: str) -> str:
    for candidate in RESOURCE_DIR_CANDIDATES:
        path = os.path.join(project_root, candidate)
        if os.path.isdir(path):
            return candidate
    return "resources"


def _resource_file(name: str) -> str:
    base = name.strip().replace(" ", "_").lower()
    return f"{base}.resource"


def _write_file(path: str, content: str, overwrite: bool, warnings: List[str]) -> None:
    if os.path.exists(path) and not overwrite:
        warnings.append(f"Skipped existing file: {path}")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _resource_content(libraries: List[str], resources: List[str]) -> str:
    lines = ["*** Settings ***"]
    for lib in libraries:
        lines.append(f"Library    {lib}")
    for res in resources:
        lines.append(f"Resource    {res}")
    lines.append("")
    lines.append("*** Keywords ***")
    lines.append("Example Keyword")
    lines.append("    [Documentation]    TODO: describe behavior")
    lines.append("    Log    TODO: implement")
    return "\n".join(lines) + "\n"


def _variables_content(fmt: str) -> str:
    if fmt == "yaml":
        return "# variables.yaml\nURL: http://example.local\n"
    if fmt == "python":
        return "URL = 'http://example.local'\n"
    return "*** Variables ***\n${URL}    http://example.local\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Robot Framework resource architect")
    parser.add_argument("--input", help="JSON input file")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    data = _read_input(args.input)

    project_root = data.get("project_root", ".")
    domains = data.get("domains") or []
    libraries = data.get("libraries") or []
    environments = data.get("environments") or []
    resource_naming = data.get("resource_naming", "by-domain")
    variables_format = data.get("variables_format", "resource").lower()

    warnings: List[str] = []
    suggestions: List[str] = []

    resource_dir_name = _detect_resource_dir(project_root)
    resource_dir = os.path.join(project_root, resource_dir_name)

    if variables_format not in ("resource", "yaml", "python"):
        warnings.append(f"Unknown variables_format '{variables_format}', defaulting to resource")
        variables_format = "resource"

    if variables_format == "yaml":
        suggestions.append("Install pyyaml if you need to parse YAML variable files.")

    directories = [resource_dir]
    files: List[Dict[str, Any]] = []

    common_resource = os.path.join(resource_dir, "common.resource")
    files.append({
        "path": common_resource,
        "content": _resource_content(libraries, []),
    })

    domain_resources = []
    if resource_naming == "by-domain":
        for domain in domains:
            filename = _resource_file(domain)
            domain_path = os.path.join(resource_dir, filename)
            domain_resources.append(domain_path)
            files.append({
                "path": domain_path,
                "content": _resource_content([], ["common.resource"]),
            })
    else:
        suggestions.append("resource_naming not 'by-domain' is not fully implemented; using common.resource only.")

    if environments:
        variables_dir = os.path.join(resource_dir, "variables")
        directories.append(variables_dir)
        ext = ".resource" if variables_format == "resource" else ".yaml" if variables_format == "yaml" else ".py"
        for env in environments:
            filename = f"{env}{ext}"
            files.append({
                "path": os.path.join(variables_dir, filename),
                "content": _variables_content(variables_format),
            })

    if args.write:
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        for item in files:
            _write_file(item["path"], item["content"], args.overwrite, warnings)

    output = {
        "directories": directories,
        "files": files,
        "warnings": warnings,
        "suggestions": suggestions,
        "meta": {
            "resource_dir": resource_dir_name,
            "resource_naming": resource_naming,
        },
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
