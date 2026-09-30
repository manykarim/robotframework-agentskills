#!/usr/bin/env python3
"""Build a description variant root for trigger tuning (tune-skill-descriptions D5).

Copies ``plugins/rf-agentskills`` and ``skills/`` into ``--out`` and replaces the
frontmatter ``description`` (line 3, JSON-quoted) of each skill named in the
candidates file(s). Prints the variant id (a hash of every staged description).

Usage::

    uv run python scripts/build-description-variant.py \\
        --candidates openspec/changes/tune-skill-descriptions/candidates/rf-results.yaml \\
        --out /tmp/variants/rf-results-it1

    uv run rf-skill-eval trigger --variant-root /tmp/variants/rf-results-it1 ...

A candidates file is either a plain ``{rf-skill: "text"}`` mapping (an empty
file gives an identical copy) or a per-skill audit file with ``iterations``
(the ``selected`` iteration is used, else the last one). Texts are staged
byte-exact (design D14): whitespace inside a text, such as the four spaces of
``Library    Browser``, is kept; only leading/trailing whitespace is dropped.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from rf_skill_eval.application.variant import build_variant, load_candidates  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--candidates", type=Path, action="append", default=[],
                        help="candidates YAML (repeatable)")
    parser.add_argument("--out", type=Path, required=True, help="variant root to create")
    parser.add_argument("--repo", type=Path, default=REPO, help="source repository root")
    parser.add_argument("--force", action="store_true", help="replace a non-empty --out")
    args = parser.parse_args(argv)
    try:
        candidates = load_candidates(args.candidates)
        variant = build_variant(args.repo, candidates, args.out, force=args.force)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    replaced = ", ".join(variant.replaced) or "none (identical copy)"
    print(f"replaced: {replaced}", file=sys.stderr)
    print(variant.variant_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
