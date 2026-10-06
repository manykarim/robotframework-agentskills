#!/usr/bin/env python3
"""Build one upload-ready ZIP per skill for Claude Desktop / claude.ai.

Claude loads custom skills uploaded under Customize -> Skills -> Upload a
skill; each archive holds the skill folder at its root (``rf-browser/SKILL.md``
...). The archives are byte-identical to what ``rf-agentskills install
--agent claude-desktop`` writes (same builder, deterministic timestamps).

Usage::

    python scripts/build-skill-zips.py --out dist/skill-zips
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "installer" / "src"))

from rf_agentskills.skillzip import skill_zip_bytes  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--skills", type=Path, default=REPO / "skills", help="skills root")
    parser.add_argument("--out", type=Path, required=True, help="output directory")
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    count = 0
    for skill_dir in sorted(p for p in args.skills.iterdir() if (p / "SKILL.md").is_file()):
        (args.out / f"{skill_dir.name}.zip").write_bytes(skill_zip_bytes(skill_dir))
        count += 1
    print(f"{count} skill archives in {args.out}")
    return 0 if count else 1


if __name__ == "__main__":
    raise SystemExit(main())
