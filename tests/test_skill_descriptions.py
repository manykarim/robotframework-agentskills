"""Skill triggering contract (openspec change ``sharpen-skill-descriptions``, design D7;
extended by ``tune-skill-descriptions``: D8, then the compact contract D11/D12).

Static checks, no network, no model calls:

* every shipped skill's frontmatter ``description`` is *compact* (D11): at most
  160 characters; names Robot Framework (or RF) and the skill's library, tool
  or file; carries a load cue starting with "Use" or "Load"; names at most 2
  keyword/API names; no meta-phrasing ("Guide AI agents", "Helps the AI"); and
  all shipped ``- <name>: <description>`` listing lines together fit in 1700
  characters. Portability rules (<= 1024 characters, no XML tags, only shipped
  skill names, never itself) apply on their own;
* every SKILL.md body has a ``## When to use`` block within its first 20 lines
  that names the sibling skill(s) with their signal and lists the concrete
  trigger terms that no longer fit in the description (D12; this replaces the
  description-level boundary check);
* every ``## Companion Skills`` table uses rows from the shared catalogue
  (design D4), names only shipped skills (never itself, never a retired one) and
  has the required rows for that skill;
* every shipped skill has ``eval/triggers/<name>.yaml`` with >= 8 should-trigger
  and >= 8 should-not-trigger queries in both splits, and no query leaks a skill id.

The trigger-set shape duplicates the eval-harness loader on purpose so this runs
in the plain ``pytest tests/`` job without harness extras.

``add-rf-language-skill`` added the ``language`` catalogue key and the
rf-language entries; ``add-rf-python-library-skill`` added the
``python-library`` key and the rf-python-library entries.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO / "skills"
TRIGGERS = REPO / "eval" / "triggers"

# ── compact contract constants (tune-skill-descriptions D11/D12) ────────────
#
# Claude Code shows skill descriptions only while they fit the skill-listing
# budget: context window x 4 x 1% characters (SLASH_COMMAND_TOOL_CHAR_BUDGET
# overrides it), i.e. 8000 for 200k-context models. Bundled skills keep their
# descriptions first; the other skills keep theirs in alphabetical order while
# they still fit and are listed by name only after that.
#
# LISTING_ROOM is the room left for the rf-* descriptions, measured on
# 2026-10-02 with Claude Code 2.1.286 and claude-haiku-4-5 at the default
# budget of 8000: 99 trigger sessions all gave 1423, with the bundled
# ``plugin-authoring`` skill listed in every session (it was 1600 on 2026-10-01
# before that skill appeared, and 1734 with 2.1.284 on 2026-09-29). Claude Code spends
# that room on ": <description>" per shown skill, so the test sums exactly that
# and allows 95% of the room (MAX_DESCRIPTION_TEXT) as a margin for the next
# Claude Code update.
#
# To re-measure (after a Claude Code upgrade or a change in bundled skills):
# run one trigger session (``rf-skill-eval trigger --skills rf-results --split
# validation --runs 1``), open ``<run>/session.jsonl``, find the attachment with
# ``"type": "skill_listing"`` and compute
#     budget - (len(content) - sum(len(": " + d) for each shown rf-* description d))
# which is the room left for the rf-* descriptions. Update the three LISTING_*
# constants below.
LISTING_ROOM = 1423
LISTING_ROOM_CLAUDE_CODE = "2.1.286"
LISTING_ROOM_MEASURED = "2026-10-02"
MAX_DESCRIPTION_TEXT = int(LISTING_ROOM * 0.95)
MAX_COMPACT = 160
WHEN_TO_USE_WITHIN = 20  # the "## When to use" heading must be within this many body lines
MAX_API_NAMES = 2
#: Portability limit of the Agent Skills format, applies regardless.
MAX_DESCRIPTION = 1024

META_RE = re.compile(r"guide ai agents|helps? (the )?ai", re.I)
RF_RE = re.compile(r"\bRobot Framework\b|\bRF\b")
#: Load cue: a sentence that starts with "Use" or "Load" ("Use when", "Use first
#: when", "Use for", "Load first when" ...).
LOAD_CUE_RE = re.compile(r"(?:^|[.!?;:]\s+)(?:Use|Load)\b")
WHEN_TO_USE_RE = re.compile(r"^##\s+When to use\s*$", re.I)
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
TITLE_RUN_RE = re.compile(r"\b[A-Z][A-Za-z0-9]*(?: [A-Z][A-Za-z0-9]*)+")
ROBOT_FENCE_RE = re.compile(r"^```(?:robotframework|robot)[ \t]*\n(.*?)^```", re.S | re.M)
_CONTROL = {"IF", "ELSE", "ELSE IF", "FOR", "END", "WHILE", "TRY", "EXCEPT", "FINALLY",
            "RETURN", "VAR", "BREAK", "CONTINUE", "GROUP"}
TAG_RE = re.compile(r"<[A-Za-z/!][^>]*>")
SKILL_TOKEN_RE = re.compile(r"`(rf-[a-z0-9-]+)`")

RETIRED = (
    "rf-keyword-builder",
    "rf-testcase-builder",
    "rf-resource-architect",
    "rf-libdoc-search",
    "rf-libdoc-explain",
)

# The library, tool or file each compact description must name (any one of them).
SUBJECT_TERMS: dict[str, tuple[str, ...]] = {
    "rf-browser": ("Browser Library", "Playwright"),
    "rf-selenium": ("SeleniumLibrary", "Selenium"),
    "rf-appium": ("AppiumLibrary", "Appium"),
    "rf-requests": ("RequestsLibrary",),
    "rf-restinstance": ("RESTinstance", "`REST`"),
    "rf-platynui": ("PlatynUI",),
    "rf-robotcode": ("robotcode",),
    "rf-setup": ("install", "pip", "uv", "venv", "environment"),
    "rf-libdoc": ("libdoc", "keyword doc", "keyword argument", "keyword name"),
    "rf-results": ("output.xml",),
    "rf-language": (".robot", ".resource", "test case", "suite", "keyword"),
    "rf-python-library": ("Python",),
}

# Trigger terms each skill's "## When to use" block must carry (they no longer
# fit in the description; the rf-robotcode / rf-setup / rf-libdoc words are
# also required by their own specs).
REQUIRED_TERMS: dict[str, tuple[str, ...]] = {
    "rf-browser": ("`Library    Browser`", "Playwright", "rfbrowser"),
    "rf-selenium": ("`Library    SeleniumLibrary`", "WebDriver", "Selenium Grid"),
    "rf-appium": ("`Library    AppiumLibrary`", "Appium", ".apk"),
    "rf-requests": ("`Library    RequestsLibrary`",),
    "rf-restinstance": ("`Library    REST`", "JSON Schema", "OpenAPI"),
    "rf-platynui": ("PlatynUI", "AT-SPI2"),
    "rf-robotcode": ("robotcode", "robot.toml", "robot-debug", "discover", "debug", "result"),
    "rf-setup": ("install", "uv", "venv", "Poetry", "ModuleNotFoundError", "No module named"),
    "rf-libdoc": ("libdoc", "keyword", "argument", "signature", "No keyword with name"),
    "rf-results": ("output.xml", "rebot"),
    "rf-language": (
        "Test Template",
        "Given/When/Then",
        "__init__.robot",
        "[Arguments]",
        "embedded",
        "Force Tags",
        "Multiple keywords with name",
    ),
    "rf-python-library": (
        "@keyword",
        "@library",
        "ROBOT_LIBRARY_SCOPE",
        "contains no keywords",
        "listener",
        "Literal",
    ),
}

# Boundary (spec "Sibling skills state their boundary"): texts the
# "## When to use" block must contain.
SIBLINGS: dict[str, tuple[str, ...]] = {
    "rf-browser": ("rf-selenium", "SeleniumLibrary", "rf-setup"),
    "rf-selenium": ("rf-browser", "Browser Library"),
    "rf-requests": ("rf-restinstance", "`REST`"),
    "rf-restinstance": ("rf-requests", "RequestsLibrary"),
    "rf-results": ("rf-robotcode", "robotcode CLI is installed"),
    "rf-libdoc": ("rf-robotcode", "robotcode CLI is installed"),
    "rf-robotcode": ("rf-results", "rf-libdoc"),
    "rf-setup": ("library skills",),
    "rf-appium": ("rf-platynui", "rf-browser", "rf-selenium"),
    "rf-platynui": ("rf-appium", "rf-browser", "rf-selenium"),
    "rf-language": ("Python keyword libraries", "rf-python-library", "rf-browser", "rf-requests"),
    "rf-python-library": ("rf-language", ".resource", "library skill"),
}

# Default wording when no library is named (user decision 2026-09-27), in the block.
DEFAULTS: dict[str, str] = {
    "rf-browser": "no library chosen",
    "rf-requests": "without naming a library",
}

# Companion Skills catalogue (design D4): key -> (Need, Skill cell), verbatim.
CATALOGUE: dict[str, tuple[str, str]] = {
    "setup": ("Install Robot Framework or a library, fix the environment", "`rf-setup`"),
    "libdoc": (
        "Look up keyword names, arguments and docs",
        "`rf-libdoc` (or `rf-robotcode`: `robotcode libdoc`)",
    ),
    "results": (
        "Analyze output.xml results",
        "`rf-results` (or `rf-robotcode`: `robotcode results`)",
    ),
    "robotcode": (
        "Discover, run, debug and statically check with the robotcode CLI",
        "`rf-robotcode`",
    ),
    "browser": ("Web UI tests with Browser Library (Playwright)", "`rf-browser`"),
    "selenium": ("Web UI tests with SeleniumLibrary (WebDriver)", "`rf-selenium`"),
    "requests": ("API tests with RequestsLibrary", "`rf-requests`"),
    "restinstance": ("API tests with RESTinstance / JSON Schema", "`rf-restinstance`"),
    "appium": ("Mobile app tests with AppiumLibrary", "`rf-appium`"),
    "platynui": ("Native desktop tests with PlatynUI", "`rf-platynui`"),
    "language": (
        "Write tests, suites, user keywords, resources and variables in Robot Framework syntax",
        "`rf-language`",
    ),
    "python-library": ("Write or fix a Python keyword library or listener", "`rf-python-library`"),
}

REQUIRED_ROWS: dict[str, tuple[str, ...]] = {
    "rf-browser": ("selenium", "setup", "libdoc", "results", "robotcode", "language"),
    "rf-selenium": ("browser", "setup", "libdoc", "results", "robotcode", "language"),
    "rf-appium": ("setup", "libdoc", "results", "robotcode", "language"),
    "rf-requests": ("restinstance", "setup", "libdoc", "results", "robotcode", "language"),
    "rf-restinstance": ("requests", "setup", "libdoc", "results", "robotcode", "language"),
    "rf-platynui": ("setup", "libdoc", "results", "robotcode", "language"),
    "rf-robotcode": ("setup", "libdoc", "results", "browser", "requests", "language"),
    "rf-setup": (
        "robotcode",
        "browser",
        "selenium",
        "appium",
        "requests",
        "restinstance",
        "platynui",
        "language",
    ),
    "rf-libdoc": ("robotcode", "setup", "results"),
    "rf-results": ("robotcode", "libdoc", "setup"),
    "rf-language": ("browser", "requests", "setup", "libdoc", "results", "robotcode", "python-library"),
    "rf-python-library": ("language", "setup", "libdoc", "results", "robotcode"),
}

# rf-robotcode keeps its "With robotcode / Without robotcode" form (design D4).
THREE_COLUMN_HEADERS: dict[str, tuple[str, ...]] = {
    "rf-robotcode": ("Need", "With robotcode", "Without robotcode"),
}


# ── helpers ─────────────────────────────────────────────────────────────────


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, f"{path}: no frontmatter"
    return yaml.safe_load(m.group(1))


def _skills() -> dict[str, Path]:
    out: dict[str, Path] = {}
    for md in sorted(SKILLS_ROOT.glob("*/SKILL.md")):
        out[str(_frontmatter(md)["name"])] = md
    return out


SKILLS = _skills()
SHIPPED = set(SKILLS)


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def _body_keywords(text: str) -> set[str]:
    """Keyword names called on indented lines of Robot Framework data."""
    out: set[str] = set()
    for line in text.splitlines():
        if not line.startswith(("    ", "\t")):
            continue
        cells = [c for c in re.split(r"\s{2,}|\t", line.strip()) if c]
        while cells and (re.match(r"^[$@&%]\{.*\}\s*=?$", cells[0]) or cells[0] == "="):
            cells = cells[1:]
        if not cells:
            continue
        first = cells[0]
        if first.startswith(("[", "#", "...")) or first in _CONTROL:
            continue
        out.add(first)
    return out


def _shipped_keyword_names() -> set[str]:
    """Multi-word keyword names used in the shipped skills' Robot examples.

    Collected from fenced ``robot``/``robotframework`` blocks in Markdown and
    from ``.robot``/``.resource`` files under ``skills/`` (e.g. ``New Browser``,
    ``Get Text``). Single-word names (``Click``, ``Integer``) are left out: they
    collide with ordinary words.
    """
    names: set[str] = set()
    for path in SKILLS_ROOT.rglob("*"):
        if path.suffix == ".md":
            for block in ROBOT_FENCE_RE.finditer(path.read_text(encoding="utf-8")):
                names |= _body_keywords(block.group(1))
        elif path.suffix in (".robot", ".resource"):
            names |= _body_keywords(path.read_text(encoding="utf-8"))
    return {_norm(n) for n in names if " " in n.strip()}


KEYWORD_NAMES = _shipped_keyword_names()


def catalog_names(desc: str, keyword_names: set[str] | None = None) -> list[str]:
    """Keyword/API names a description lists (design D8).

    Backtick spans that are not ``rf-*`` skill names, plus TitleCase phrases
    that are shipped keyword names (longest match, no overlaps).
    """
    known = KEYWORD_NAMES if keyword_names is None else keyword_names
    found = [t for t in BACKTICK_RE.findall(desc) if not re.fullmatch(r"rf-[a-z0-9-]+", t)]
    prose = BACKTICK_RE.sub(" ", desc)
    for run in TITLE_RUN_RE.finditer(prose):
        words = run.group(0).split()
        i = 0
        while i < len(words):
            for j in range(len(words), i + 1, -1):
                phrase = " ".join(words[i:j])
                if _norm(phrase) in known:
                    found.append(phrase)
                    i = j - 1
                    break
            i += 1
    return sorted(set(found))


def catalog_problems(name: str, desc: str, keyword_names: set[str] | None = None) -> list[str]:
    names = catalog_names(desc, keyword_names)
    if len(names) > MAX_API_NAMES:
        return [
            f"{name}: names {len(names)} keyword/API names (max {MAX_API_NAMES}): {names}"
        ]
    return []


def portability_problems(name: str, desc: str) -> list[str]:
    """Rules that hold for any description, compact or not."""
    probs: list[str] = []
    meta = META_RE.search(desc)
    if meta:
        probs.append(f"{name}: meta-phrasing {meta.group(0)!r}")
    if len(desc) > MAX_DESCRIPTION:
        probs.append(f"{name}: {len(desc)} characters (max {MAX_DESCRIPTION})")
    tag = TAG_RE.search(desc)
    if tag:
        probs.append(f"{name}: XML tag {tag.group(0)!r}")
    return probs + _skill_name_problems(name, desc)


def compact_problems(name: str, desc: str, keyword_names: set[str] | None = None) -> list[str]:
    """Compact-contract violations of one description (D11), prefixed by the skill name."""
    probs = portability_problems(name, desc)
    if len(desc) > MAX_COMPACT:
        probs.append(f"{name}: description is {len(desc)} characters (max {MAX_COMPACT})")
    if not RF_RE.search(desc):
        probs.append(f"{name}: names neither 'Robot Framework' nor 'RF'")
    subjects = SUBJECT_TERMS.get(name, ())
    if subjects and not any(t.lower() in desc.lower() for t in subjects):
        probs.append(f"{name}: names none of its library/tool/file terms {list(subjects)}")
    if not LOAD_CUE_RE.search(desc):
        probs.append(f"{name}: no load cue (a sentence starting with 'Use' or 'Load')")
    return probs + catalog_problems(name, desc, keyword_names)


def description_text_total(descriptions: dict[str, str]) -> int:
    """Characters Claude Code spends on the rf-* descriptions: ``": " + description`` each."""
    return sum(len(": " + d) for d in descriptions.values())


def listing_problems(descriptions: dict[str, str]) -> list[str]:
    """Description text over :data:`MAX_DESCRIPTION_TEXT`: total, limit, CC version, three longest."""
    total = description_text_total(descriptions)
    if total <= MAX_DESCRIPTION_TEXT:
        return []
    longest = sorted(descriptions.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:3]
    named = ", ".join(f"{n} ({len(d)})" for n, d in longest)
    return [
        f"description text is {total} characters (max {MAX_DESCRIPTION_TEXT} = 95% of the "
        f"{LISTING_ROOM}-character room measured with Claude Code {LISTING_ROOM_CLAUDE_CODE} "
        f"on {LISTING_ROOM_MEASURED}); longest descriptions: {named}"
    ]


#: Skills with a recorded near-miss load of a sibling's query carry a short cue
#: naming that sibling (skill-triggering spec; add-sibling-cues-to-descriptions).
SIBLING_CUES: dict[str, str] = {
    "rf-appium": "rf-setup",
    "rf-selenium": "rf-setup",
    "rf-libdoc": "rf-robotcode",
    "rf-results": "rf-robotcode",
}


def sibling_cue_problems(name: str, desc: str) -> list[str]:
    sibling = SIBLING_CUES.get(name)
    if sibling and sibling not in desc:
        return [f"{name}: description has no sibling cue naming {sibling}"]
    return []


def _skill_name_problems(name: str, desc: str) -> list[str]:
    probs: list[str] = []
    for token in re.findall(r"\brf-[a-z0-9-]+\b", desc):
        if token not in SHIPPED:
            probs.append(f"{name}: names {token!r}, which is not a shipped skill")
        if token == name:
            probs.append(f"{name}: names itself")
    return probs


def _body_lines(text: str) -> list[str]:
    """SKILL.md lines after the frontmatter."""
    m = re.match(r"---\n.*?\n---\n", text, re.S)
    return (text[m.end():] if m else text).splitlines()


def when_to_use_block(text: str) -> str | None:
    """The ``## When to use`` block when its heading is within the first body lines."""
    lines = _body_lines(text)
    for i, line in enumerate(lines[:WHEN_TO_USE_WITHIN]):
        if WHEN_TO_USE_RE.match(line):
            body: list[str] = []
            for rest in lines[i + 1:]:
                if rest.startswith("## ") or rest.startswith("# "):
                    break
                body.append(rest)
            return "\n".join(body)
    return None


def when_to_use_problems(name: str, text: str) -> list[str]:
    """D12: the block exists early, names the siblings and carries the trigger terms."""
    block = when_to_use_block(text)
    if block is None:
        return [
            f"{name}: no '## When to use' block within the first {WHEN_TO_USE_WITHIN} body lines"
        ]
    probs: list[str] = []
    for needle in SIBLINGS.get(name, ()):
        if needle not in block:
            probs.append(f"{name}: '## When to use' must name {needle!r} (sibling boundary)")
    if name in DEFAULTS and DEFAULTS[name] not in block:
        probs.append(f"{name}: default-when-no-library wording {DEFAULTS[name]!r} missing")
    for term in REQUIRED_TERMS.get(name, ()):
        if term.lower() not in block.lower():
            probs.append(f"{name}: '## When to use' should mention {term!r}")
    for token in re.findall(r"\brf-[a-z0-9-]+\b", block):
        if token not in SHIPPED:
            probs.append(f"{name}: '## When to use' names {token!r}, which is not a shipped skill")
    return probs


def _cells(row: str) -> list[str]:
    return [c.strip() for c in row.strip().strip("|").split("|")]


def companion_table(text: str) -> tuple[list[str], list[list[str]]] | None:
    """Header and rows of the first table under ``## Companion Skills`` (case-insensitive)."""
    m = re.search(r"^## Companion Skills[ \t]*\n(.*?)(?=^## |\Z)", text, re.S | re.M | re.I)
    if not m:
        return None
    rows = [ln for ln in m.group(1).splitlines() if ln.strip().startswith("|")]
    if len(rows) < 2:
        return None
    header = _cells(rows[0])
    body = [_cells(r) for r in rows[2:]]
    return header, body


def companion_problems(name: str, text: str) -> list[str]:
    parsed = companion_table(text)
    if parsed is None:
        return [f"{name}: no '## Companion Skills' section with a table"]
    header, body = parsed
    probs: list[str] = []
    expected_header = THREE_COLUMN_HEADERS.get(name, ("Need", "Skill"))
    if tuple(header) != expected_header:
        probs.append(f"{name}: Companion Skills header {header} != {list(expected_header)}")
    section = re.search(r"^## Companion Skills.*?(?=^## |\Z)", text, re.S | re.M | re.I)
    assert section
    for retired in RETIRED:
        if re.search(rf"(?<![\w-]){re.escape(retired)}(?![\w-])", section.group(0)):
            probs.append(f"{name}: Companion Skills names retired skill {retired!r}")
    present: set[str] = set()
    for row in body:
        probs += _row_problems(name, row, len(expected_header), present)
    for key in REQUIRED_ROWS.get(name, ()):
        if key not in present:
            probs.append(
                f"{name}: Companion Skills lacks the required {key!r} row ({CATALOGUE[key][0]!r})"
            )
    return probs


def _row_problems(name: str, row: list[str], width: int, present: set[str]) -> list[str]:
    """Check one Companion Skills row; record its catalogue key in *present*."""
    if len(row) != width:
        return [f"{name}: row {row} has {len(row)} cells, expected {width}"]
    need, last = row[0], row[-1]
    key = {n: k for k, (n, _s) in CATALOGUE.items()}.get(need)
    if key is None:
        return [f"{name}: row Need {need!r} is not in the companion catalogue"]
    present.add(key)
    probs: list[str] = []
    catalogue_skill = CATALOGUE[key][1]
    primary = SKILL_TOKEN_RE.search(catalogue_skill)
    assert primary
    if width == 2 and last != catalogue_skill:
        probs.append(f"{name}: row {need!r} skill cell {last!r} != catalogue {catalogue_skill!r}")
    if width != 2 and f"`{primary.group(1)}`" not in last:
        probs.append(f"{name}: row {need!r} last column must name `{primary.group(1)}`")
    for token in (tok for cell in row[1:] for tok in SKILL_TOKEN_RE.findall(cell)):
        if token not in SHIPPED:
            probs.append(f"{name}: Companion Skills names {token!r}, which is not a shipped skill")
        elif token == name and width == 2:
            probs.append(f"{name}: Companion Skills row names the skill itself")
    return probs


# ── real tree ───────────────────────────────────────────────────────────────


def test_every_shipped_skill_is_covered_by_the_contract() -> None:
    assert SHIPPED, "no skills found"
    missing = sorted(SHIPPED - set(REQUIRED_ROWS))
    assert not missing, f"add REQUIRED_ROWS / SIBLINGS entries for {missing}"
    stale = sorted(set(REQUIRED_ROWS) - SHIPPED)
    assert not stale, f"REQUIRED_ROWS names skills that are not shipped: {stale}"


# Skills whose shipped description / SKILL.md do not meet the compact contract
# yet. Task 6.1 shipped the compact descriptions and "## When to use" blocks for
# all 12 skills, so both sets are empty. A skill added here gets a strict xfail:
# an unexpected pass fails, so the set must be emptied once the skill complies.
_PENDING_REASON = "compact rewrite pending (tasks 4.4–6.1)"
COMPACT_PENDING: frozenset[str] = frozenset()
WHEN_TO_USE_PENDING: frozenset[str] = COMPACT_PENDING
#: Sibling cues not shipped yet (add-sibling-cues-to-descriptions task 4.2 empties it).
_CUES_REASON = "sibling cue pending (add-sibling-cues-to-descriptions 4.2)"
CUES_PENDING: frozenset[str] = frozenset()


def _params(pending: frozenset[str]) -> list[object]:
    return [
        pytest.param(name, marks=pytest.mark.xfail(strict=True, reason=_PENDING_REASON))
        if name in pending
        else name
        for name in sorted(SKILLS)
    ]


def _description(name: str) -> str:
    desc = _frontmatter(SKILLS[name])["description"]
    assert isinstance(desc, str)
    return desc


def test_pending_sets_name_shipped_skills() -> None:
    assert COMPACT_PENDING <= SHIPPED and WHEN_TO_USE_PENDING <= SHIPPED


@pytest.mark.parametrize("name", sorted(SKILLS))
def test_description_portability(name: str) -> None:
    problems = portability_problems(name, _description(name))
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("name", _params(COMPACT_PENDING))
def test_compact_description_rules(name: str) -> None:
    problems = compact_problems(name, _description(name))
    assert not problems, "\n".join(problems)


# The 2026-10-01 re-measurement (room 1600) shows the shipped texts at 1528 > 1520;
# add-sibling-cues-to-descriptions task 4.2 trims them and sets this to False.
LISTING_OVER_PENDING = False


@pytest.mark.xfail(
    bool(COMPACT_PENDING) or LISTING_OVER_PENDING,
    strict=True,
    reason="description text over the re-measured 95% limit until add-sibling-cues 4.2",
)
def test_combined_listing_fits_default_budget() -> None:
    problems = listing_problems({name: _description(name) for name in SKILLS})
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize(
    "name",
    [
        pytest.param(n, marks=pytest.mark.xfail(strict=True, reason=_CUES_REASON))
        if n in CUES_PENDING
        else n
        for n in sorted(SIBLING_CUES)
    ],
)
def test_sibling_cue_present(name: str) -> None:
    problems = sibling_cue_problems(name, _description(name))
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("name", _params(WHEN_TO_USE_PENDING))
def test_when_to_use_block(name: str) -> None:
    problems = when_to_use_problems(name, SKILLS[name].read_text(encoding="utf-8"))
    assert not problems, "\n".join(problems)


def test_frontmatter_keeps_name_and_description_first() -> None:
    for name, md in SKILLS.items():
        lines = md.read_text(encoding="utf-8").splitlines()
        assert lines[1] == f"name: {name}", md
        assert lines[2].startswith("description: "), md


@pytest.mark.parametrize("name", sorted(SKILLS))
def test_companion_skills_table(name: str) -> None:
    problems = companion_problems(name, SKILLS[name].read_text(encoding="utf-8"))
    assert not problems, "\n".join(problems)


def test_web_and_api_siblings_cross_linked() -> None:
    def skills_in_table(name: str) -> set[str]:
        parsed = companion_table(SKILLS[name].read_text(encoding="utf-8"))
        assert parsed
        return {t for row in parsed[1] for t in SKILL_TOKEN_RE.findall(row[-1])}

    assert "rf-selenium" in skills_in_table("rf-browser")
    assert "rf-browser" in skills_in_table("rf-selenium")
    assert "rf-restinstance" in skills_in_table("rf-requests")
    assert "rf-requests" in skills_in_table("rf-restinstance")


@pytest.mark.parametrize("name", sorted(SKILLS))
def test_trigger_set_exists_with_shape(name: str) -> None:
    path = TRIGGERS / f"{name}.yaml"
    assert path.is_file(), f"missing trigger set {path.relative_to(REPO)}"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["skill"] == name
    queries = data["queries"]
    for polarity in (True, False):
        # optional holdout splits (holdout, holdout<N>) are not counted
        items = [
            q
            for q in queries
            if q["should_trigger"] is polarity and q["split"] in ("train", "validation")
        ]
        assert len(items) >= 8, (name, polarity, len(items))
        assert {q["split"] for q in items} == {"train", "validation"}, (name, polarity)
    for q in queries:
        assert q["split"] in ("train", "validation") or re.fullmatch(
            r"holdout\d*", q["split"]
        ), (name, q["id"], q["split"])
    for q in queries:
        leaked = re.findall(r"\brf-[a-z0-9-]+\b", q["query"])
        assert not leaked, f"{name} {q['id']}: query names a skill id {leaked}"


def test_no_trigger_set_for_unshipped_or_retired_skill() -> None:
    names = {p.stem for p in TRIGGERS.glob("*.yaml")}
    assert names == SHIPPED, (sorted(names - SHIPPED), sorted(SHIPPED - names))


# ── the checks themselves (spec scenarios) ──────────────────────────────────


_GOOD = "Writes Robot Framework web tests with Browser Library. Use first when a suite imports it."


def test_contract_constants() -> None:
    assert (MAX_COMPACT, WHEN_TO_USE_WITHIN, MAX_API_NAMES) == (160, 20, 2)
    assert MAX_DESCRIPTION_TEXT == int(LISTING_ROOM * 0.95) == 1351
    assert MAX_DESCRIPTION == 1024


def test_compact_description_accepted() -> None:
    assert compact_problems("rf-browser", _GOOD, set()) == []
    rf = "Parses RF output.xml into JSON. Load first when a run's results are asked about."
    assert compact_problems("rf-results", rf, set()) == []


def test_compact_length_enforced() -> None:
    at_limit = _GOOD + " " + "x" * (MAX_COMPACT - len(_GOOD) - 1)
    assert len(at_limit) == 160
    assert compact_problems("rf-browser", at_limit, set()) == []
    over = at_limit + "x"
    assert compact_problems("rf-browser", over, set()) == [
        "rf-browser: description is 161 characters (max 160)"
    ]


def test_portability_length_rejected_regardless() -> None:
    long = _GOOD + " " + "x" * 1024
    assert any("max 1024" in p for p in portability_problems("rf-browser", long))
    assert any("max 1024" in p for p in compact_problems("rf-browser", long, set()))


def test_combined_listing_budget() -> None:
    # 10 x (": " + 120) = 1220 <= 1351
    descs = {f"rf-s{i:02d}": "d" * 120 for i in range(10)}
    assert description_text_total(descs) == 10 * 122 and listing_problems(descs) == []
    descs["rf-zz"] = "e" * 160  # +162 -> 1382 > 1351
    descs["rf-s03"] = "f" * 155
    probs = listing_problems(descs)
    assert len(probs) == 1
    total = description_text_total(descs)
    assert f"is {total} characters (max 1351 = 95% of the 1423-character room" in probs[0]
    assert "Claude Code 2.1.286" in probs[0]
    assert "rf-zz (160), rf-s03 (155), rf-s00 (120)" in probs[0]


def test_listing_counts_description_text_not_name_prefixes() -> None:
    # Name length must not matter: Claude Code lists names even when it drops descriptions.
    short = {"rf-a": "x" * 100}
    long = {"rf-a-very-long-skill-name": "x" * 100}
    assert description_text_total(short) == description_text_total(long) == 102


def test_sibling_cue_rule() -> None:
    assert sibling_cue_problems("rf-results", "Use first … rebot. With robotcode: rf-robotcode.") == []
    assert sibling_cue_problems("rf-results", "Use first … rebot.") == [
        "rf-results: description has no sibling cue naming rf-robotcode"]
    assert sibling_cue_problems("rf-browser", "anything") == []  # no recorded near-miss


def test_rf_and_subject_required() -> None:
    no_rf = "Writes web tests with Browser Library. Use first when a suite imports it."
    assert any("'Robot Framework' nor 'RF'" in p for p in compact_problems("rf-browser", no_rf, set()))
    no_subject = "Writes Robot Framework web tests. Use first when a web test is asked for."
    assert any("library/tool/file" in p for p in compact_problems("rf-browser", no_subject, set()))
    # "RF" as a word counts, "RFC" does not
    assert not RF_RE.search("See RFC 7231") and RF_RE.search("RF tests")


def test_load_cue_required() -> None:
    no_cue = "Writes Robot Framework web tests with Browser Library, when a suite imports it."
    assert any("load cue" in p for p in compact_problems("rf-browser", no_cue, set()))
    for cue in ("Use when", "Use first when", "Use for", "Load first when", "Load when"):
        assert LOAD_CUE_RE.search(f"Writes Robot Framework tests. {cue} x."), cue
    assert LOAD_CUE_RE.search("Use this for Robot Framework Browser Library tests.")
    assert not LOAD_CUE_RE.search("Writes Robot Framework tests. Useful for web.")


def test_meta_phrasing_is_rejected_and_named() -> None:
    probs = compact_problems(
        "rf-browser", "Guide AI agents in Robot Framework Browser Library tests. Use when asked.", set()
    )
    assert any(p.startswith("rf-browser:") and "meta-phrasing" in p for p in probs)
    probs = compact_problems(
        "rf-browser", "Browser Library for Robot Framework. Helps the AI. Use when asked.", set()
    )
    assert any("meta-phrasing 'Helps the AI'" in p for p in probs)


def test_keyword_catalog_rejected() -> None:
    known = {_norm(n) for n in ("New Browser", "New Page", "Fill Text", "Get Text")}
    three = ("Robot Framework Browser Library: New Browser, New Page, Get Text. "
             "Use when asked.")
    probs = catalog_problems("rf-demo", three, known)
    assert probs and probs[0].startswith("rf-demo: names 3 keyword/API names (max 2)")
    two = "Robot Framework Browser Library: New Browser, Get Text. Use when asked."
    assert catalog_problems("rf-demo", two, known) == []
    # an import line in backticks counts as one API name; rf-* names do not count
    ticks = "Use for `Library    Browser` and `New Page` with `rf-selenium` and `rf-setup`."
    assert catalog_problems("rf-demo", ticks, known) == []
    assert "3 keyword/API names" in catalog_problems("rf-demo", ticks + " `Get Url`", known)[0]


def test_shipped_keyword_names_are_collected() -> None:
    for kw in ("new browser", "get text", "open browser"):
        assert kw in KEYWORD_NAMES, kw
    assert "robot framework" not in KEYWORD_NAMES


def _skill_md(body: str) -> str:
    return "---\nname: rf-x\ndescription: \"d\"\n---\n" + body


_WEB_BLOCK = (
    "## When to use\n\n"
    "- A suite imports `Library    Browser`, the user mentions Playwright or rfbrowser, "
    "or wants a web test with no library chosen yet.\n"
    "- Not for SeleniumLibrary/WebDriver suites: use rf-selenium. Installing: rf-setup.\n"
)


def test_when_to_use_block_accepted() -> None:
    text = _skill_md("\n# Browser Library\n\nIntro.\n\n" + _WEB_BLOCK + "\n## Next\n")
    assert when_to_use_problems("rf-browser", text) == []
    assert "rf-selenium" in (when_to_use_block(text) or "")
    assert "## Next" not in (when_to_use_block(text) or "")


def test_when_to_use_block_must_be_early() -> None:
    late = _skill_md("# X\n" + "text\n" * 19 + _WEB_BLOCK)
    assert when_to_use_problems("rf-browser", late) == [
        "rf-browser: no '## When to use' block within the first 20 body lines"
    ]
    early = _skill_md("# X\n" + "text\n" * 18 + _WEB_BLOCK)  # heading on body line 20
    assert when_to_use_problems("rf-browser", early) == []
    # a similar heading does not count
    other = _skill_md("# X\n\n## When to read the references\n\n- rf-selenium\n")
    assert when_to_use_block(other) is None


def test_when_to_use_block_names_siblings_and_terms() -> None:
    no_sibling = _WEB_BLOCK.replace("use rf-selenium", "use the other skill")
    probs = when_to_use_problems("rf-browser", _skill_md(no_sibling))
    assert probs == ["rf-browser: '## When to use' must name 'rf-selenium' (sibling boundary)"]
    no_default = _WEB_BLOCK.replace("no library chosen yet", "nothing chosen")
    assert any("no library chosen" in p
               for p in when_to_use_problems("rf-browser", _skill_md(no_default)))
    no_term = _WEB_BLOCK.replace(" or rfbrowser", "")
    assert any("'rfbrowser'" in p for p in when_to_use_problems("rf-browser", _skill_md(no_term)))
    retired = _WEB_BLOCK + "- See rf-keyword-builder.\n"
    assert any("rf-keyword-builder" in p
               for p in when_to_use_problems("rf-browser", _skill_md(retired)))


def test_script_skills_defer_to_robotcode_in_block() -> None:
    block = ("## When to use\n\n- The user pastes output.xml or asks to merge runs with rebot.\n"
             "- Prefer rf-robotcode when the robotcode CLI is installed.\n")
    assert when_to_use_problems("rf-results", _skill_md(block)) == []
    assert any("robotcode CLI is installed" in p for p in when_to_use_problems(
        "rf-results", _skill_md(block.replace("when the robotcode CLI is installed", ""))))


def test_stale_companion_rows_rejected() -> None:
    text = (
        "# X\n\n## Companion Skills\n\n| Need | Skill |\n|---|---|\n"
        "| Look up keyword names, arguments and docs | `rf-libdoc-search` |\n"
        "| Build keywords | `rf-keyword-builder` |\n\n## Next\n"
    )
    probs = companion_problems("rf-selenium", text)
    assert any("retired skill 'rf-libdoc-search'" in p for p in probs)
    assert any("not in the companion catalogue" in p for p in probs)
    assert any("required 'browser' row" in p for p in probs)
    assert companion_problems("rf-selenium", "# X\n\nno table\n") == [
        "rf-selenium: no '## Companion Skills' section with a table"
    ]
