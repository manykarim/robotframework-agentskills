#!/usr/bin/env python3
"""Validate SKILL.md frontmatter against the agentskills.io specification.

Stdlib-only (PyYAML is used for parsing when it is importable). Checks every
skill directory of the selected distribution channel(s):

  root    skills/
  plugin  plugins/rf-agentskills/skills/
  vscode  vscode-extension/skills/

Rules (spec capability ``skill-metadata-conformance``):

  frontmatter        SKILL.md exists and starts with a closed ``---`` block
  name-missing       ``name`` is present
  name-charset       lowercase ASCII letters, digits, single inner hyphens
  name-length        1-64 characters
  name-prefix        starts with ``rf-`` (this repository's identifier scheme)
  name-dir-mismatch  ``name`` equals the containing directory
  description-*      present, non-empty, at most 1024 characters
  compatibility-*    present, non-empty, at most 500 characters
  xml-tag            no XML/HTML tag in ``name`` or ``description``
  unknown-key        only name/description/license/compatibility/metadata/allowed-tools
  license            ``license: Apache-2.0``
  metadata-*         ``metadata`` is a string->string map with ``author`` and ``version``
  version-mismatch   ``metadata.version`` equals the repository ``VERSION``
  channel-mismatch   (--channel all) the three channels hold the same skill names

Output: one ``path: rule: detail`` line per violation; exit 1 if any.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

CHANNELS = {
    "root": Path("skills"),
    "plugin": Path("plugins/rf-agentskills/skills"),
    "vscode": Path("vscode-extension/skills"),
}
ALLOWED_KEYS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
REQUIRED_METADATA = ("author", "version")
LICENSE = "Apache-2.0"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TAG_RE = re.compile(r"</?[A-Za-z][A-Za-z0-9_:-]*(?:\s[^<>]*)?/?>")
MAX_NAME, MAX_DESCRIPTION, MAX_COMPATIBILITY = 64, 1024, 500


class FrontmatterError(ValueError):
    pass


# ── Frontmatter parsing ─────────────────────────────────────────────────────

def split_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError("SKILL.md does not start with a '---' frontmatter block")
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:i])
    raise FrontmatterError("frontmatter block is not closed with '---'")


_KEY_RE = re.compile(r"^(?P<key>[A-Za-z0-9_-]+):(?:[ \t]+(?P<value>.*?))?[ \t]*$")
_INT_RE = re.compile(r"^[-+]?(?:0|[1-9][0-9]*|0x[0-9a-fA-F]+|0o[0-7]+)$")
_FLOAT_RE = re.compile(r"^[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)(?:[eE][-+]?[0-9]+)?$|^[-+]?\.(?:inf|Inf|INF)$|^\.(?:nan|NaN|NAN)$")


def _scalar(raw: str):
    """Resolve a single-line YAML scalar the way the YAML core schema does."""
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        escapes = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "/": "/", "0": "\0"}
        return re.sub(r"\\(.)", lambda m: escapes.get(m.group(1), m.group(0)), raw[1:-1])
    if len(raw) >= 2 and raw[0] == raw[-1] == "'":
        return raw[1:-1].replace("''", "'")
    if raw[:1] in ("[", "{", "&", "*", "!", "|", ">", "@", "`"):
        raise FrontmatterError(f"unsupported YAML construct: {raw[:20]!r}")
    if raw in ("", "~", "null", "Null", "NULL"):
        return None
    if raw in ("true", "True", "TRUE"):
        return True
    if raw in ("false", "False", "FALSE"):
        return False
    if _INT_RE.match(raw):
        return int(raw, 0)
    if _FLOAT_RE.match(raw):
        return float(raw)
    return raw


def _block_scalar(indicator: str, body: list[str]) -> str:
    style, chomp = indicator[0], indicator[1:2]
    indent = min((len(line) - len(line.lstrip()) for line in body if line.strip()), default=0)
    lines = [line[indent:] if line.strip() else "" for line in body]
    while lines and not lines[-1]:
        lines.pop()
    if style == "|":
        text = "\n".join(lines)
    else:  # folded: single newlines become spaces, blank lines stay newlines
        text, prev_blank = "", True
        for line in lines:
            if not line:
                text += "\n"
                prev_blank = True
            else:
                text += ("" if prev_blank else " ") + line
                prev_blank = False
    return text if chomp == "-" else text + "\n"


def parse_minimal(fm: str) -> dict:
    """YAML subset: flat scalars (plain, quoted, multi-line plain, block |/>),
    plus one level of nested ``key: value`` mappings."""
    lines = fm.splitlines()
    data: dict = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        if line[0] in " \t":
            raise FrontmatterError(f"unexpected indentation: {line.strip()[:40]!r}")
        m = _KEY_RE.match(line)
        if not m:
            raise FrontmatterError(f"cannot parse line: {line[:40]!r}")
        key, value = m.group("key"), m.group("value") or ""
        if key in data:
            raise FrontmatterError(f"duplicate key: {key}")
        i += 1
        body = []
        while i < len(lines) and (not lines[i].strip() or lines[i][0] in " \t"):
            body.append(lines[i])
            i += 1
        while body and not body[-1].strip():
            body.pop()
        if re.fullmatch(r"[|>][-+]?", value):
            data[key] = _block_scalar(value, body)
        elif value:
            if body:  # multi-line plain scalar
                if value[0] in "\"'":
                    raise FrontmatterError(f"multi-line quoted scalar for {key!r} is not supported")
                data[key] = " ".join([value.strip()] + [b.strip() for b in body if b.strip()])
            else:
                data[key] = _scalar(value)
        elif body:
            nested: dict = {}
            for b in body:
                if not b.strip():
                    continue
                nm = _KEY_RE.match(b.strip())
                if not nm:
                    raise FrontmatterError(f"cannot parse nested line under {key!r}: {b.strip()[:40]!r}")
                nested[nm.group("key")] = _scalar(nm.group("value") or "")
            data[key] = nested
        else:
            data[key] = None
    return data


def parse_frontmatter(text: str, use_yaml: bool = True) -> dict:
    fm = split_frontmatter(text)
    if use_yaml:
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError:
            use_yaml = False
    if use_yaml:
        try:
            data = yaml.safe_load(fm)
        except yaml.YAMLError as exc:
            raise FrontmatterError(f"invalid YAML: {exc}") from exc
        data = {} if data is None else data
    else:
        data = parse_minimal(fm)
    if not isinstance(data, dict):
        raise FrontmatterError("frontmatter is not a mapping")
    return data


# ── Rules ───────────────────────────────────────────────────────────────────

def _text(data: dict, key: str) -> str | None:
    value = data.get(key)
    return value if isinstance(value, str) else None


def validate_skill(skill_dir: Path, version: str | None, use_yaml: bool = True) -> list[tuple[str, str]]:
    """Return (rule, detail) violations for one skill directory."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [("frontmatter", "SKILL.md is missing")]
    try:
        data = parse_frontmatter(skill_md.read_text(encoding="utf-8"), use_yaml=use_yaml)
    except FrontmatterError as exc:
        return [("frontmatter", str(exc))]

    out: list[tuple[str, str]] = []
    for key in sorted(set(map(str, data)) - ALLOWED_KEYS):
        out.append(("unknown-key", f"top-level key {key!r} is not allowed"))

    name = _text(data, "name")
    if not name:
        out.append(("name-missing", "'name' is missing or not a string"))
    else:
        if len(name) > MAX_NAME:
            out.append(("name-length", f"{len(name)} characters (max {MAX_NAME})"))
        if not NAME_RE.match(name):
            out.append(("name-charset", f"{name!r}: use a-z, 0-9 and single inner hyphens"))
        if not name.startswith("rf-"):
            out.append(("name-prefix", f"{name!r} does not start with 'rf-'"))
        if name != skill_dir.name:
            out.append(("name-dir-mismatch", f"name {name!r} != directory {skill_dir.name!r}"))
        if TAG_RE.search(name):
            out.append(("xml-tag", "'name' contains an XML/HTML tag"))

    description = _text(data, "description")
    if description is None or not description.strip():
        out.append(("description-missing", "'description' is missing or empty"))
    else:
        if len(description) > MAX_DESCRIPTION:
            out.append(("description-length", f"{len(description)} characters (max {MAX_DESCRIPTION})"))
        tag = TAG_RE.search(description)
        if tag:
            out.append(("xml-tag", f"'description' contains {tag.group(0)!r}"))

    if "compatibility" not in data:
        out.append(("compatibility-missing", "'compatibility' is missing"))
    else:
        compat = _text(data, "compatibility")
        if compat is None or not compat.strip():
            out.append(("compatibility-missing", "'compatibility' is empty or not a string"))
        elif len(compat) > MAX_COMPATIBILITY:
            out.append(("compatibility-length", f"{len(compat)} characters (max {MAX_COMPATIBILITY})"))

    if data.get("license") != LICENSE:
        out.append(("license", f"'license' must be {LICENSE!r} (got {data.get('license')!r})"))

    metadata = data.get("metadata")
    if metadata is None:
        out.append(("metadata-missing", "'metadata' is missing"))
    elif not isinstance(metadata, dict):
        out.append(("metadata-type", "'metadata' must be a mapping"))
    else:
        for k, v in metadata.items():
            if not isinstance(k, str) or not isinstance(v, str):
                out.append(("metadata-type", f"metadata {k!r}: {v!r} is not a string->string entry (quote it)"))
        for k in REQUIRED_METADATA:
            if k not in metadata:
                out.append(("metadata-missing", f"metadata.{k} is missing"))
        if version is not None and isinstance(metadata.get("version"), str) and metadata["version"] != version:
            out.append(("version-mismatch", f"metadata.version {metadata['version']!r} != VERSION {version!r}"))
    return out


def skill_dirs(channel_dir: Path) -> list[Path]:
    if not channel_dir.is_dir():
        return []
    return sorted(p for p in channel_dir.iterdir() if p.is_dir() and not p.name.startswith((".", "_")))


def validate(repo_root: Path, channels: list[str], use_yaml: bool = True) -> list[str]:
    version_file = repo_root / "VERSION"
    version = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else None
    lines: list[str] = []
    names: dict[str, set[str]] = {}
    for channel in channels:
        channel_dir = repo_root / CHANNELS[channel]
        if not channel_dir.is_dir():
            lines.append(f"{CHANNELS[channel].as_posix()}: channel-missing: directory does not exist")
            continue
        dirs = skill_dirs(channel_dir)
        names[channel] = {d.name for d in dirs}
        for d in dirs:
            rel = (CHANNELS[channel] / d.name / "SKILL.md").as_posix()
            lines.extend(f"{rel}: {rule}: {detail}" for rule, detail in validate_skill(d, version, use_yaml))
    if len(names) > 1:
        union = set().union(*names.values())
        for channel, present in names.items():
            for missing in sorted(union - present):
                lines.append(f"{CHANNELS[channel].as_posix()}/{missing}: channel-mismatch: "
                             f"skill exists in another channel but not in {channel}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--channel", choices=[*CHANNELS, "all"], default="all",
                        help="distribution channel to validate (default: all)")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="repository root (default: this script's repository)")
    parser.add_argument("--no-yaml", action="store_true", help="use the built-in parser even if PyYAML is installed")
    args = parser.parse_args(argv)
    channels = list(CHANNELS) if args.channel == "all" else [args.channel]
    violations = validate(args.repo_root, channels, use_yaml=not args.no_yaml)
    for line in violations:
        print(line)
    if violations:
        print(f"{len(violations)} violation(s)", file=sys.stderr)
        return 1
    print(f"OK: skills valid in channel(s): {', '.join(channels)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
