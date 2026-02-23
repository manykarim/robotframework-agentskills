#!/usr/bin/env python3
"""
Local marketplace validation script.
Equivalent to `claude plugin validate .` but runnable without Claude Code.
Validates marketplace.json, SKILL.md frontmatter, directory structure,
Python script compilation, and .robot file syntax.
"""
import json
import os
import sys


def validate_marketplace_json(path: str) -> list[str]:
    errors = []
    if not os.path.exists(path):
        return [f"{path} does not exist"]
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"{path} is not valid JSON: {e}"]

    for field in ["name", "owner", "plugins"]:
        if field not in data:
            errors.append(f"marketplace.json missing required field: {field}")

    if "plugins" in data:
        for i, plugin in enumerate(data["plugins"]):
            for field in ["name", "source", "description"]:
                if field not in plugin:
                    errors.append(f"Plugin #{i} missing field: {field}")
    return errors


def validate_plugin_json(path: str) -> list[str]:
    errors = []
    if not os.path.exists(path):
        return [f"{path} does not exist"]
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"{path} is not valid JSON: {e}"]

    if "name" not in data:
        errors.append(f"plugin.json missing required field: name")
    return errors


def validate_skill_md_files(skills_dir: str) -> list[str]:
    errors = []
    if not os.path.isdir(skills_dir):
        return [f"{skills_dir} does not exist"]
    for skill_name in sorted(os.listdir(skills_dir)):
        skill_path = os.path.join(skills_dir, skill_name)
        if not os.path.isdir(skill_path):
            continue
        skill_md = os.path.join(skill_path, "SKILL.md")
        if not os.path.exists(skill_md):
            errors.append(f"{skill_name}: missing SKILL.md")
            continue
        with open(skill_md) as f:
            content = f.read()
        if not content.startswith("---"):
            errors.append(f"{skill_name}/SKILL.md: missing YAML frontmatter")
            continue
        end = content.find("---", 3)
        if end == -1:
            errors.append(f"{skill_name}/SKILL.md: unclosed frontmatter")
            continue
        fm = content[3:end]
        if "name:" not in fm:
            errors.append(f"{skill_name}/SKILL.md: frontmatter missing 'name'")
        if "description:" not in fm:
            errors.append(f"{skill_name}/SKILL.md: frontmatter missing 'description'")
    return errors


def validate_python_scripts(scripts_dir: str) -> list[str]:
    errors = []
    if not os.path.isdir(scripts_dir):
        return [f"{scripts_dir} does not exist"]
    for f in sorted(os.listdir(scripts_dir)):
        if f.endswith(".py"):
            path = os.path.join(scripts_dir, f)
            try:
                with open(path) as fh:
                    compile(fh.read(), path, "exec")
            except SyntaxError as e:
                errors.append(f"{path}: syntax error: {e}")
    return errors


def validate_robot_files(skills_dir: str) -> list[str]:
    errors = []
    try:
        from robot.api import get_model
    except ImportError:
        return []  # robotframework not installed -- skip .robot validation

    for root, _dirs, files in os.walk(skills_dir):
        for f in files:
            if f.endswith(".robot"):
                path = os.path.join(root, f)
                try:
                    get_model(path)
                except Exception as e:
                    errors.append(f"{path}: parse error: {e}")
    return errors


def main() -> None:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(base)

    plugin_root = os.path.join("plugins", "rf-agentskills")
    skills_dir = os.path.join(plugin_root, "skills")
    scripts_dir = os.path.join(plugin_root, "scripts")

    all_errors: list[str] = []
    checks = [
        ("Marketplace JSON", lambda: validate_marketplace_json(
            os.path.join(".claude-plugin", "marketplace.json"))),
        ("Plugin JSON", lambda: validate_plugin_json(
            os.path.join(plugin_root, ".claude-plugin", "plugin.json"))),
        ("SKILL.md files", lambda: validate_skill_md_files(skills_dir)),
        ("Python scripts", lambda: validate_python_scripts(scripts_dir)),
        (".robot files", lambda: validate_robot_files(skills_dir)),
    ]

    for name, check_fn in checks:
        print(f"Checking {name}...")
        errs = check_fn()
        if errs:
            for e in errs:
                print(f"  FAIL: {e}")
            all_errors.extend(errs)
        else:
            print(f"  PASS")

    print()
    if all_errors:
        print(f"FAILED: {len(all_errors)} error(s) found")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
