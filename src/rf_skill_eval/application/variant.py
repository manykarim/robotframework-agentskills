"""Description variants for trigger tuning (tune-skill-descriptions, design D5).

A *variant root* is a directory holding ``plugins/rf-agentskills`` (staged by
``trigger --variant-root``) and ``skills/`` (the name list the validators
read), copied from the repository with some skills' frontmatter
``description`` replaced by candidate texts. Nothing in the repository's own
``skills/`` is edited.

The *variant id* is a short hash of every skill's description in the staged
plugin, so it is stable for identical input and equal for two roots that
carry the same descriptions (an empty candidates file yields the shipped id).
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PLUGIN_REL = Path("plugins") / "rf-agentskills"
VARIANT_FILE = "variant.json"
MAX_DESCRIPTION = 1024
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".venv", "node_modules")


def _frontmatter(skill_md: Path) -> dict[str, Any]:
    m = _FRONTMATTER_RE.match(skill_md.read_text(encoding="utf-8"))
    if not m:
        return {}
    data = yaml.safe_load(m.group(1))
    return data if isinstance(data, dict) else {}


def skill_descriptions(skills_dir: Path) -> dict[str, str]:
    """``{skill name: description}`` for every ``<skills_dir>/*/SKILL.md``."""
    out: dict[str, str] = {}
    if not skills_dir.is_dir():
        return out
    for md in sorted(skills_dir.glob("*/SKILL.md")):
        fm = _frontmatter(md)
        if fm.get("name"):
            out[str(fm["name"])] = str(fm.get("description", ""))
    return out


def description_set_id(skills_dir: Path) -> str:
    """12-hex-digit hash of the ``{name: description}`` set under ``skills_dir``."""
    canonical = json.dumps(skill_descriptions(skills_dir), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def variant_id_for(plugin_root: Path) -> str:
    """Variant id of a plugin root (``<plugin_root>/skills``)."""
    return description_set_id(plugin_root / "skills")


def load_candidates(paths: Iterable[Path]) -> dict[str, str]:
    """Merge candidate files into ``{skill: description}``.

    Accepted shapes per file:

    * a plain mapping ``{rf-skill: "description text"}`` (empty = no change);
    * the per-skill audit file ``candidates/<skill>.yaml``:
      ``{skill: rf-x, iterations: [{iteration: k, text: ...}, ...], selected: k}``.
      The ``selected`` iteration is used, else the last one.

    Texts are kept byte-exact apart from leading/trailing whitespace; whitespace
    inside a text (``Library    Browser``) is never collapsed.
    """
    out: dict[str, str] = {}
    for path in paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path}: candidates must be a mapping")
        if "iterations" in data:
            skill, text = _from_audit(path, data)
            pairs: Mapping[str, Any] = {skill: text}
        else:
            pairs = data
        for skill, raw in pairs.items():
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError(f"{path}: candidate for {skill!r} must be a non-empty string")
            # Byte-exact inside (design D14): runs of spaces such as the four in
            # ``Library    Browser`` are kept. Only the outer whitespace a YAML
            # block scalar adds (a trailing newline) is dropped.
            text = raw.strip()
            if skill in out and out[skill] != text:
                raise ValueError(f"{path}: {skill!r} has conflicting candidates")
            out[str(skill)] = text
    return out


def _from_audit(path: Path, data: Mapping[str, Any]) -> tuple[str, str]:
    skill = data.get("skill")
    iterations = data.get("iterations") or []
    if not isinstance(skill, str) or not isinstance(iterations, list) or not iterations:
        raise ValueError(f"{path}: audit file needs 'skill' and a non-empty 'iterations' list")
    selected = data.get("selected")
    if selected is None:
        chosen = iterations[-1]
    else:
        matches = [it for it in iterations if isinstance(it, dict) and it.get("iteration") == selected]
        if not matches:
            raise ValueError(f"{path}: selected iteration {selected!r} not found")
        chosen = matches[0]
    if not isinstance(chosen, dict) or not isinstance(chosen.get("text"), str):
        raise ValueError(f"{path}: iteration without a 'text'")
    return skill, chosen["text"]


def replace_description(skill_md: Path, text: str) -> None:
    """Rewrite frontmatter line 3 as ``description: <JSON-quoted text>``."""
    if len(text) > MAX_DESCRIPTION:
        raise ValueError(f"{skill_md}: candidate is {len(text)} characters (max {MAX_DESCRIPTION})")
    raw = skill_md.read_bytes().decode("utf-8")
    lines = raw.split("\n")
    if len(lines) < 4 or lines[0] != "---" or not lines[2].startswith("description: "):
        raise ValueError(f"{skill_md}: line 3 is not the frontmatter 'description:'")
    lines[2] = "description: " + json.dumps(text, ensure_ascii=False)
    skill_md.write_bytes("\n".join(lines).encode("utf-8"))


@dataclass(frozen=True)
class Variant:
    root: Path
    variant_id: str
    replaced: tuple[str, ...]


def build_variant(
    repo_root: Path, candidates: Mapping[str, str], out: Path, *, force: bool = False
) -> Variant:
    """Copy ``plugins/rf-agentskills`` and ``skills/`` to ``out`` with ``candidates`` applied."""
    plugin_src = repo_root / PLUGIN_REL
    skills_src = repo_root / "skills"
    if not (plugin_src / "skills").is_dir() or not skills_src.is_dir():
        raise ValueError(f"{repo_root}: no plugins/rf-agentskills/skills or skills/ to copy")
    if out.exists():
        if not force and any(out.iterdir()):
            raise ValueError(f"{out} exists and is not empty (use --force to replace it)")
        shutil.rmtree(out)
    out.mkdir(parents=True)
    plugin_dst = out / PLUGIN_REL
    shutil.copytree(plugin_src, plugin_dst, ignore=_IGNORE, symlinks=True)
    shutil.copytree(skills_src, out / "skills", ignore=_IGNORE, symlinks=True)

    dirs = _name_dirs(plugin_dst / "skills")
    root_dirs = _name_dirs(out / "skills")
    unknown = sorted(set(candidates) - set(dirs))
    if unknown:
        shutil.rmtree(out)
        raise ValueError(f"candidates name unknown skill(s): {unknown} (known: {sorted(dirs)})")
    for skill, text in sorted(candidates.items()):
        replace_description(plugin_dst / "skills" / dirs[skill] / "SKILL.md", text)
        if skill in root_dirs:
            replace_description(out / "skills" / root_dirs[skill] / "SKILL.md", text)

    vid = variant_id_for(plugin_dst)
    (out / VARIANT_FILE).write_text(
        json.dumps(
            {
                "variant_id": vid,
                "source": str(repo_root.resolve()),
                "candidates": dict(sorted(candidates.items())),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return Variant(root=out, variant_id=vid, replaced=tuple(sorted(candidates)))


def _name_dirs(skills_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for md in sorted(skills_dir.glob("*/SKILL.md")):
        name = _frontmatter(md).get("name")
        if name:
            out[str(name)] = md.parent.name
    return out
