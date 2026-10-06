"""Structure, content and example checks for the rf-language skill (add-rf-language-skill, task 6.1).

Layers:

1. Structure (always): frontmatter, H2 order, size budget, references and their
   table, contents lists, no reference-to-reference links, no path into another
   skill, version-gate table, Step 0, gotchas, workflow, examples list and labels,
   house style, companion rows in the eight skills that point back.
2. Robot Framework (skipped without ``robot``): every ``robotframework`` code
   block in SKILL.md and the references dry-runs against a copy of
   ``assets/examples`` and passes a real run; the example tree dry-runs and runs;
   the selection recipes select the documented number of tests; no untemplated
   test body contains a control structure.
3. Robocop 9.x (skipped without it; an installed robocop 9 is used, else
   ``uvx --from "robotframework-robocop>=9.1,<10"``): every cited rule ID exists
   with the documented name, each legacy construct yields exactly its documented
   rule, and the examples and the keyword template are clean.

Code blocks whose first line starts with ``# Wrong`` or ``# Legacy`` are
counter-examples: they are excluded from dry runs and from the legacy-syntax check.
"""

from __future__ import annotations

import functools
import importlib.util
import os
import re
import shlex
import shutil
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "rf-language"
SKILL_MD = SKILL / "SKILL.md"
REFS = SKILL / "references"
EXAMPLES = SKILL / "assets" / "examples"
SCRIPT = SKILL / "scripts" / "rf_conventions.py"

HAS_ROBOT = importlib.util.find_spec("robot") is not None
needs_robot = pytest.mark.skipif(not HAS_ROBOT, reason="robotframework not installed")

REQUIRED_SECTIONS = [
    "When to use",  # trigger block (tune-skill-descriptions D12)
    "Version gate",
    "Step 0: Match the project",
    "Choose a style",
    "Test skeletons",
    "Keyword anatomy",
    "Setup, teardown and suite files",
    "Tags and selection",
    "Variables and resources",
    "Agent workflow",
    "Gotchas",
    "When to read the references",
    "Companion Skills",
]
REFERENCES = {
    "styles.md",
    "templates.md",
    "suites-and-init.md",
    "tags-and-selection.md",
    "arguments.md",
    "embedded-arguments.md",
    "variables-and-scopes.md",
    "control-structures.md",
    "resources-and-variable-files.md",
    "migration.md",
}
HARD_LIMIT, TARGET = 500, 300
TOC_WINDOW, TOC_THRESHOLD = 15, 100

# Version-gate rows: feature text that must appear in a row -> minimum RF version.
GATE = {
    "RETURN": "5.0",
    "Test Tags": "6.0",
    "Keyword Tags": "6.0",
    "robot:private": "6.0",
    "--parseinclude": "6.1",
    "Name": "6.1",
    "JSON variable files": "6.1",
    "embedded + normal arguments": "6.1",
    "VAR": "7.0",
    "-tag": "7.0",
    "--test": "7.0",
    "scope=SUITES": "7.1",
    "BDD prefix": "7.1",
    "GROUP": "7.2",
    "(?i)": "7.2",
    "some rows skip": "7.2",
    "Typed user keyword arguments": "7.3",
    "Secret": "7.4",
}

# Robocop 9.x rule id -> name, for every rule the skill cites (the cited meaning).
ROBOCOP_RULES = {
    "DEPR03": "deprecated-with-name",
    "DEPR04": "deprecated-singular-header",
    "DEPR05": "replace-set-variable-with-var",
    "DEPR06": "replace-create-with-var",
    "DEPR07": "deprecated-force-tags",
    "DEPR08": "deprecated-run-keyword-if",
    "DEPR09": "deprecated-loop-keyword",
    "DEPR10": "deprecated-return-keyword",
    "DEPR11": "deprecated-return-setting",
    "ANN02": "missing-argument-type",
    "ANN04": "set-keyword-with-type",
    "KW06": "ambiguous-keyword-name",
    "TAG03": "tag-with-reserved-word",
    "LEN04": "too-long-test-case",
    "LEN06": "too-many-calls-in-test-case",
    "LEN30": "empty-template",
    "ERR04": "variables-import-with-args",
    "ERR14": "return-in-test-case",
    "ERR17": "unsupported-setting-in-init-file",
    "NAME07": "not-capitalized-test-case-title",
    "NAME08": "section-variable-not-uppercase",
    "NAME18": "wrong-case-in-keyword-call",
    "ORD02": "keyword-section-out-of-order",
    "VAR05": "no-suite-variable",
    "VAR06": "no-test-variable",
    "VAR07": "non-local-variables-should-be-uppercase",
    "VAR10": "inconsistent-variable-name",
    "ARG03": "undefined-argument-default",
    "MISC08": "statement-outside-loop",
    "MISC11": "multiline-inline-if",
    "DOC01": "missing-doc-keyword",
    "DOC03": "missing-doc-suite",
}
RULE_ID_RE = re.compile(r"\b(?:DEPR|ANN|KW|TAG|LEN|ERR|NAME|ORD|VAR|ARG|MISC|DOC)\d{2}\b")

# One mini suite per migration-table construct -> the rule ids robocop 9 must report.
LEGACY_CASES = {
    "[Return]": ("*** Keywords ***\nKw\n    [Return]    x\n", {"DEPR11"}),
    "Return From Keyword": ("*** Keywords ***\nKw\n    Return From Keyword    x\n", {"DEPR10"}),
    "Run Keyword If": ("*** Keywords ***\nKw\n    Run Keyword If    True    Log    x\n", {"DEPR08"}),
    "Exit For Loop": (
        "*** Keywords ***\nKw\n    FOR    ${i}    IN    a\n        Exit For Loop\n    END\n",
        {"DEPR09"},
    ),
    "Set Suite Variable": ("*** Keywords ***\nKw\n    Set Suite Variable    ${X}    1\n", {"DEPR05"}),
    "Create List": ("*** Keywords ***\nKw\n    ${l}=    Create List    a\n    Log    ${l}\n", {"DEPR06"}),
    "Catenate": ("*** Keywords ***\nKw\n    ${s}=    Catenate    a    b\n    Log    ${s}\n", set()),
    "Set Variable If": (
        "*** Keywords ***\nKw\n    ${s}=    Set Variable If    True    a    b\n    Log    ${s}\n",
        set(),
    ),
    "Force Tags": ("*** Settings ***\nForce Tags    api\n", {"DEPR07"}),
    "Default Tags": ("*** Settings ***\nDefault Tags    api\n", set()),
    "WITH NAME": ("*** Settings ***\nLibrary    Collections    WITH NAME    Coll\n", {"DEPR03"}),
    "singular header": ("*** Keyword ***\nKw\n    No Operation\n", {"DEPR04"}),
    "typed Set Test Variable": (
        "*** Keywords ***\nKw\n    Set Test Variable    ${x: int}    1\n", {"ANN04", "DEPR05"},
    ),
}

LEGACY_CODE_RE = re.compile(
    r"\bForce Tags\b|\bDefault Tags\b|Run Keyword (?:If|Unless)\b|\[Return\]|\bExit For Loop\b"
    r"|\bContinue For Loop\b|\bReturn From Keyword\b|\bSet (?:Test|Suite|Global|Local) Variable\b"
    r"|\bWITH NAME\b|\bCreate (?:List|Dictionary)\b|^\*\*\* (?:Setting|Variable|Test Case|Keyword) \*\*\*\s*$",
    re.M,
)
SHOUT_WORDS = {
    "NEVER", "ALWAYS", "MUST", "CRITICAL", "IMPORTANT", "WARNING", "NOTE",
    "DO", "DON'T", "SHOULD", "REQUIRED",
}
DATED_RE = re.compile(
    r"\bas of\b|\brecently\b|\bnew in\b|\bcurrently\b|\b20\d\d-\d\d-\d\d\b|"
    r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
    re.I,
)
STANDARD_LIBRARIES = {
    "BuiltIn", "Collections", "String", "DateTime", "OperatingSystem", "Process", "XML",
    "Screenshot", "Telnet", "Dialogs",
}
EIGHT_SKILLS = (
    "rf-setup", "rf-robotcode", "rf-browser", "rf-selenium",
    "rf-appium", "rf-requests", "rf-restinstance", "rf-platynui",
)
LANGUAGE_NEED = "Write tests, suites, user keywords, resources and variables in Robot Framework syntax"


# --- helpers ---------------------------------------------------------------------


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _body(text: str) -> str:
    return text.split("\n---\n", 1)[1] if text.startswith("---") else text


def _frontmatter(text: str) -> dict:
    yaml = pytest.importorskip("yaml")
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, "no frontmatter"
    return yaml.safe_load(m.group(1))


def _h2(text: str) -> list[str]:
    out, fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
        elif not fence and line.startswith("## "):
            out.append(line[3:].strip())
    return out


def _section(text: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}[ \t]*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    assert m, f"section {heading!r} missing"
    return m.group(1)


def _prose(text: str) -> list[tuple[int, str]]:
    out, fence = [], False
    for no, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if not fence:
            out.append((no, re.sub(r"`[^`]*`", "", line)))
    return out


def _rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", s.strip("|"))]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            continue
        rows.append(cells)
    return rows


def _robot_blocks(text: str) -> list[str]:
    return re.findall(r"^```(?:robotframework|robot)\n(.*?)^```", text, re.M | re.S)


def _is_counter_example(block: str) -> bool:
    first = block.lstrip().splitlines()[0] if block.strip() else ""
    return first.startswith(("# Wrong", "# Legacy"))


def _min_version(block: str) -> tuple[int, int] | None:
    m = re.match(r"\s*# RF (\d+)\.(\d+)\+", block)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _all_docs() -> list[Path]:
    return [SKILL_MD, *sorted(REFS.glob("*.md"))]


def _code_blocks() -> list[tuple[str, int, str]]:
    return [
        (path.name, i, block)
        for path in _all_docs()
        for i, block in enumerate(_robot_blocks(_text(path)))
    ]


def _rf_version() -> tuple[int, int]:
    from robot.version import VERSION

    major, minor = VERSION.split(".")[:2]
    return int(major), int(re.match(r"\d+", minor).group(0))


def _robot(args: list[str], cwd: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "robot", *args], capture_output=True, text=True, timeout=300, cwd=cwd, env=env,
    )


def _count_tests(output_xml: Path) -> tuple[int, int, int]:
    from robot.api import ExecutionResult

    stats = ExecutionResult(str(output_xml)).statistics.total
    return stats.passed + stats.failed + stats.skipped, stats.passed, stats.skipped


# --- 1. structure ----------------------------------------------------------------


def test_frontmatter_and_layout() -> None:
    text = _text(SKILL_MD)
    fm = _frontmatter(text)
    assert fm["name"] == "rf-language" == SKILL.name
    assert fm["license"] == "Apache-2.0"
    compat = fm["compatibility"]
    assert len(compat) <= 500
    for word in ("Python", "robotframework>=7", "version-gated", "robocop", "optional"):
        assert word in compat, word
    assert fm["metadata"]["author"] and fm["metadata"]["version"] == _text(ROOT / "VERSION").strip()
    assert SCRIPT.is_file() and (SKILL / "references").is_dir() and EXAMPLES.is_dir()
    links = [p for p in SKILL.rglob("*") if p.is_symlink()]
    assert not links, links


def test_description_boundary() -> None:
    desc = _frontmatter(_text(SKILL_MD))["description"]
    assert len(desc) <= 1024
    if len(desc) > 600:
        warnings.warn(f"rf-language description is {len(desc)} characters (target about 600)", stacklevel=1)
    # Compact description (tune-skill-descriptions D11); the trigger terms and the
    # boundary moved into the "## When to use" body block (D12).
    assert len(desc) <= 160 and "Robot Framework" in desc
    m = re.search(r"^## When to use[ \t]*\n(.*?)(?=^## )", _text(SKILL_MD), re.M | re.S)
    assert m, "no '## When to use' block"
    use_when = m.group(1)
    for term in (".robot", ".resource", "__init__.robot", "[Arguments]", "Force Tags", "Multiple keywords with name"):
        assert term in use_when, term
    boundary = use_when.split("Multiple keywords with name", 1)[1]
    assert "Python keyword libraries" in boundary and "rf-browser" in boundary and "rf-requests" in boundary
    assert "rf-python-library" in boundary
    shipped = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
    named = set(re.findall(r"\brf-[a-z-]+\b", desc))
    assert named <= shipped, named - shipped


def test_required_sections_in_order() -> None:
    assert _h2(_body(_text(SKILL_MD))) == REQUIRED_SECTIONS


def test_size_budget() -> None:
    lines = len(_text(SKILL_MD).splitlines())
    assert lines <= HARD_LIMIT, f"SKILL.md has {lines} lines (hard limit {HARD_LIMIT})"
    if lines > TARGET:
        warnings.warn(f"rf-language SKILL.md has {lines} lines (target <= {TARGET})", stacklevel=1)


def test_orientation_and_verified_line() -> None:
    body = _body(_text(SKILL_MD))
    head = body.split("\n## ", 1)[0]
    lines = [ln for ln in head.splitlines() if ln.strip() and not ln.startswith("# ")]
    assert len(lines) <= 6, lines
    assert re.fullmatch(r"Verified against Robot Framework \d+\.\d+(\.\d+)?\.", lines[-1]), lines[-1]
    hits = [(p.name, ln) for p in _all_docs() for ln in _text(p).splitlines() if "Verified against" in ln]
    assert len(hits) == 1 and hits[0][0] == "SKILL.md", hits


def test_reference_set_matches_table() -> None:
    present = {p.name for p in REFS.iterdir()}
    assert present == REFERENCES
    table = _section(_text(SKILL_MD), "When to read the references")
    rows = _rows(table)
    assert rows[0][:2] == ["Read", "When"]
    listed = {re.search(r"references/([\w.-]+\.md)", r[0]).group(1) for r in rows[1:] if "references/" in r[0]}
    assert listed == REFERENCES
    assert all(r[1] for r in rows[1:]), "every reference needs a read-when condition"


def test_long_references_have_toc() -> None:
    problems = []
    for path in sorted(REFS.glob("*.md")):
        lines = _text(path).splitlines()
        if len(lines) <= TOC_THRESHOLD:
            continue
        start = next((i for i, ln in enumerate(lines[:TOC_WINDOW]) if re.match(r"\s*[-*]\s+", ln)), None)
        if start is None:
            problems.append(f"{path.name}: no contents list in the first {TOC_WINDOW} lines")
            continue
        end = start
        while end < len(lines) and re.match(r"\s*[-*]\s+", lines[end]):
            end += 1
        toc = "\n".join(lines[start:end])
        problems += [f"{path.name}: TOC misses {h!r}" for h in _h2("\n".join(lines)) if h not in toc]
    assert not problems, problems


def test_references_do_not_link_to_each_other() -> None:
    bad = []
    for path in sorted(REFS.glob("*.md")):
        text = _text(path)
        for name in REFERENCES - {path.name}:
            if name in text:
                bad.append(f"{path.name} -> {name}")
        bad += [f"{path.name}: {m}" for m in re.findall(r"\]\((?!#|https?:)[^)]+\)", text)]
    assert not bad, bad


def test_no_path_into_another_skill() -> None:
    pattern = re.compile(r"(?:skills/|\.\./)rf-[a-z-]+/|\brf-(?!language)[a-z-]+/(?:references|scripts|assets)/")
    bad = [f"{p.name}: {m.group(0)}" for p in _all_docs() for m in pattern.finditer(_text(p))]
    assert not bad, bad


def test_version_gate_single_block_with_features() -> None:
    text = _text(SKILL_MD)
    assert text.count("| Feature | Min RF |") == 1
    for path in sorted(REFS.glob("*.md")):
        assert "| Feature | Min RF |" not in _text(path), path.name
    gate = _section(text, "Version gate")
    assert 'uv run python -c "import robot; print(robot.__version__)"' in gate
    assert "robot --version" in gate and "251" in gate
    rows = _rows(gate)[1:]
    for feature, version in GATE.items():
        hit = [r for r in rows if feature in r[0]]
        assert hit, f"version gate lacks {feature!r}"
        assert hit[0][1] == version, (feature, hit[0][1], version)
    assert "`${count}: int` is invalid on every version" in gate
    assert "passes `robot --dryrun` and fails at run time" in gate


def test_version_gate_matches_rf_conventions_features() -> None:
    """Every feature the script reports has the same minimum in the gate table."""
    src = _text(SCRIPT)
    mins = set(re.findall(r'\(\s*"[a-z_]+",\s*\((\d+),\s*(\d+)\)', src))
    assert mins, "feature table not found in rf_conventions.py"
    gate_versions = {r[1] for r in _rows(_section(_text(SKILL_MD), "Version gate"))[1:]}
    assert {f"{a}.{b}" for a, b in mins} == gate_versions


@needs_robot
def test_version_command_exits_zero() -> None:
    res = subprocess.run([sys.executable, "-c", "import robot; print(robot.__version__)"], capture_output=True)
    assert res.returncode == 0
    res = subprocess.run([sys.executable, "-m", "robot", "--version"], capture_output=True)
    assert res.returncode == 251


def test_step0_means_in_order() -> None:
    step0 = _section(_text(SKILL_MD), "Step 0: Match the project")
    script, grep = (step0.index(s) for s in ("scripts/rf_conventions.py", "grep -r"))
    assert script < grep
    assert "MCP" not in step0
    greps = [ln for ln in step0.splitlines() if ln.startswith("grep -r")]
    assert len(greps) == 3
    assert all("--include='*.robot'" in g and "--include='*.resource'" in g and "grep -rh" in g for g in greps)
    assert "Library|Resource|Variables" in greps[0]
    assert "Given|When|Then" in greps[1] and "Template" in greps[1]
    assert "Test Tags|Force Tags|Default Tags" in greps[2]
    for field in ("rf.features.typed_arguments.available", "style.separator.dominant", "follow-embedded-style",
                  "layout.resource_dir", "libraries.web_library"):
        assert field in step0, field
    assert "existing keyword" in step0


def test_step0_fields_exist_in_script_output(tmp_path: Path) -> None:
    pytest.importorskip("robot")
    import json

    res = subprocess.run([sys.executable, str(SCRIPT), str(EXAMPLES)], capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    step0 = _section(_text(SKILL_MD), "Step 0: Match the project")
    for dotted in set(re.findall(r"`((?:rf|style|keywords|layout|libraries|calls|tests)\.[a-z_.]+)`", step0)):
        node = data
        for part in dotted.split("."):
            assert isinstance(node, dict) and part in node, f"{dotted}: {part} missing"
            node = node[part]


def test_style_table_rows() -> None:
    table = _rows(_section(_text(SKILL_MD), "Choose a style"))
    text = " ".join(" ".join(r) for r in table).lower()
    for needle in ("keyword-driven", "template", "bdd", "datadriver", "user keyword", "python keyword library"):
        assert needle in text, needle
    assert len(table) - 1 >= 6


def test_keyword_anatomy() -> None:
    anatomy = _section(_text(SKILL_MD), "Keyword anatomy")
    block = _robot_blocks(anatomy)[0]
    order = [s for s in ("[Documentation]", "[Tags]", "[Arguments]", "[Timeout]", "[Setup]", "RETURN", "[Teardown]")
             if s in block]
    assert order == sorted(order, key=block.index) and len(order) == 7
    assert re.search(r"\$\{\w+: int\}", block), "the default template is typed (RF 7.3+)"
    assert "RF < 7.3" in anatomy and "Convert To Integer" in anatomy
    rows = " ".join(" ".join(r) for r in _rows(anatomy))
    for form in ("${quantity}=1", "${EMPTY}", "${to}=${from}", "@{items}", "&{options}", "Select Team", ": int"):
        assert form in rows, form
    assert "A variable that contains `timeout=5s` is passed as a positional value" in anatomy
    assert "@{args}    &{kwargs}" in anatomy


def test_setup_teardown_section_rules() -> None:
    sec = _section(_text(SKILL_MD), "Setup, teardown and suite files")
    for needle in ("exactly one keyword call", "replaces", "`NONE`", "continues", "fails every test",
                   "not visible to child suites", "imports the resource", "`Test Template` is not allowed",
                   "skips the parent `__init__.robot`", "`--suite`", "prefixes order suites"):
        assert needle in sec, needle
    init = _robot_blocks(sec)[0]
    assert "*** Keywords ***" not in init and "Suite Setup" in init


def test_tags_section() -> None:
    sec = _section(_text(SKILL_MD), "Tags and selection")
    for tag in ("robot:skip", "robot:exclude", "robot:skip-on-failure", "robot:continue-on-failure",
                "robot:stop-on-failure", "robot:no-dry-run", "robot:private", "robot:flatten"):
        assert tag in sec, tag
    assert "Force Tags" in sec and "legacy" in sec and "DEPR07" in sec
    assert '"smoke NOT slow"' in sec and "insensitive" in sec
    assert "Tests.Api.Users.Create User" in sec and "*.Users.Create User" in sec


def test_variables_section() -> None:
    sec = _section(_text(SKILL_MD), "Variables and resources")
    for needle in ("scope=SUITE", "SUITES", "GLOBAL", "Upper case", "Priority", "resources/", "Never overwrite",
                   "uv add pyyaml"):
        assert needle in sec, needle
    assert len(_rows(sec)) - 1 == 5


def test_agent_workflow_order_and_blind_spots() -> None:
    wf = _section(_text(SKILL_MD), "Agent workflow")
    steps = re.findall(r"^(\d+)\. (.*?)(?=^\d+\. |\Z)", wf, re.M | re.S)
    assert [int(n) for n, _ in steps] == list(range(1, 10))
    joined = [s for _, s in steps]
    idx = {k: next(i for i, s in enumerate(joined) if k in s) for k in
           ("--dryrun", "robocop check", "for real", "robotcode results")}
    assert idx["--dryrun"] < idx["robocop check"] < idx["for real"] < idx["robotcode results"]
    assert "step 4" in joined[-1]
    dry = joined[idx["--dryrun"]]
    for blind in ("undefined or misspelled variables", "space before `=`", "embedded-argument binding",
                  "union-with-`str`", "RF < 7.3", "real run"):
        assert blind in dry, blind
    lint = joined[idx["robocop check"]]
    assert "skipped" in lint and "rf-setup" in lint and "--target-version" in lint
    assert "--no-cache" in lint, "robocop leaves .robocop_cache/ in the project without --no-cache"
    assert lint.count(" -s ") >= 4 and "DEPR" in lint and "ORD02" in lint and "NAME" in lint
    assert not re.search(r"-s\s+\S*,\S*", lint), "comma-separated robocop selection is rejected by robocop 9"
    assert "robotcode analyze code" in wf and "rf-libdoc" in wf and "rf-results" in wf


def test_gotchas() -> None:
    items = re.findall(r"^- (.+)$", _section(_text(SKILL_MD), "Gotchas"), re.M)
    assert len(items) >= 19, len(items)
    text = "\n".join(items)
    for needle in ("__init__.robot", "Force Tags", "robot:", "[Template]", "Test Template", "timeout =5s",
                   "${count}: int", "embedded", "Multiple keywords with name", "dry run", "PyYAML", "BREAK",
                   "None", "Catenate", "Set Variable If", "section header", "`*`", "NOT slow", "Given"):
        assert needle in text, needle
    assert all("`" in item for item in items), "each gotcha names the construct in inline code"


def test_examples_listed_and_labelled() -> None:
    text = _text(SKILL_MD)
    files = sorted(p for p in EXAMPLES.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    for path in files:
        assert path.name in text, f"SKILL.md does not list {path.name}"
        head = "\n".join(_text(path).splitlines()[:3])
        want = "RF 7.3+" if path.name == "keywords.resource" else "RF 7.0+"
        assert want in head, f"{path.name}: missing {want!r} label"
    listing = _section(text, "When to read the references").split("Examples in", 1)[1]
    assert "(RF 7.3+)" in listing and listing.count("(RF 7.0+)") >= 3
    assert not any("6.1" in p.name or "rf61" in p.name or "rf70" in p.name for p in files)
    assert not re.search(r"RF 6\.1", "\n".join(_text(p) for p in files))


def test_no_legacy_constructs_in_code_or_examples() -> None:
    bad = []
    for name, i, block in _code_blocks():
        if not _is_counter_example(block):
            bad += [f"{name}#{i}: {m.group(0)}" for m in LEGACY_CODE_RE.finditer(block)]
    for path in EXAMPLES.rglob("*.*"):
        if path.suffix in (".robot", ".resource"):
            code = "\n".join(ln for ln in _text(path).splitlines() if not ln.lstrip().startswith("#"))
            bad += [f"{path.name}: {m.group(0)}" for m in LEGACY_CODE_RE.finditer(code)]
    assert not bad, bad


def test_legacy_tag_settings_only_named_as_legacy() -> None:
    for path in _all_docs():
        for no, line in enumerate(_text(path).splitlines(), 1):
            if re.search(r"\b(Force|Default) Tags\b", line) and not line.lstrip().startswith("```"):
                ok = any(w in line.lower() for w in ("legacy", "deprecated", "instead", "depr07", "replacement",
                                                     "not reported", "no direct", "|", "not allowed", "grep",
                                                     "replacing"))
                assert ok, f"{path.name}:{no}: {line.strip()}"


def test_code_blocks_use_standard_libraries_only() -> None:
    for name, i, block in _code_blocks():
        for lib in re.findall(r"^Library\s{2,}(\S+)", block, re.M):
            assert lib in STANDARD_LIBRARIES, f"{name}#{i}: {lib}"
    for path in EXAMPLES.rglob("*.*"):
        if path.suffix in (".robot", ".resource"):
            for lib in re.findall(r"^Library\s{2,}(\S+)", _text(path), re.M):
                assert lib in STANDARD_LIBRARIES, f"{path.name}: {lib}"


def test_house_style() -> None:
    loud, dated = [], []
    for path in _all_docs():
        text = _body(_text(path)) if path == SKILL_MD else _text(path)
        for no, line in _prose(text):
            words = set(re.findall(r"\b[A-Z][A-Z']+\b", line)) & SHOUT_WORDS
            if words:
                loud.append(f"{path.name}:{no}: {sorted(words)}")
            if DATED_RE.search(line) and not (path.name == "migration.md" and "Robocop 9.1.0" in line):
                dated.append(f"{path.name}:{no}: {line.strip()[:80]}")
    assert not loud, loud
    assert not dated, dated
    stamp = [ln for ln in _text(REFS / "migration.md").splitlines() if "Robocop 9.1.0" in ln]
    assert stamp, "migration.md is stamped with the robocop version"


def test_companion_rows() -> None:
    sec = _section(_text(SKILL_MD), "Companion Skills")
    for skill in ("rf-setup", "rf-libdoc", "rf-results", "rf-robotcode", "rf-browser", "rf-requests"):
        assert f"`{skill}`" in sec, skill
    for skill in EIGHT_SKILLS:
        other = _section(_text(ROOT / "skills" / skill / "SKILL.md"), "Companion Skills")
        row = [r for r in _rows(other) if r[0] == LANGUAGE_NEED]
        assert len(row) == 1 and "`rf-language`" in row[0][-1], skill
        for retired in ("rf-test-design", "rf-keyword-design", "rf-resource-architect"):
            assert retired not in other


def test_migration_table_rows() -> None:
    rows = _rows(_section(_text(REFS / "migration.md"), "Legacy to modern table"))
    assert rows[0] == ["Legacy construct", "Modern replacement", "Min RF", "Robocop rule"]
    by_construct = {r[0]: r for r in rows[1:]}
    expected = {
        "[Return]": "DEPR11", "Return From Keyword": "DEPR10", "Run Keyword If": "DEPR08",
        "Exit For Loop": "DEPR09", "Set Suite Variable": "DEPR05", "Create List": "DEPR06",
        "Catenate": "none", "Set Variable If": "none", "Force Tags": "DEPR07", "WITH NAME": "DEPR03",
        "Singular section headers": "DEPR04",
    }
    for construct, rule in expected.items():
        hit = [r for c, r in by_construct.items() if construct in c]
        assert hit, construct
        assert hit[0][3].startswith(rule), (construct, hit[0][3])
        assert re.fullmatch(r"\d\.\d", hit[0][2]), hit[0][2]
    text = _text(REFS / "migration.md")
    assert "--target-version" in text and '-s "DEPR*"' in text


def test_cited_rule_ids_are_documented_here() -> None:
    cited = {m for p in _all_docs() for m in RULE_ID_RE.findall(_text(p))}
    unknown = cited - set(ROBOCOP_RULES)
    assert not unknown, f"add the cited robocop rules to ROBOCOP_RULES: {sorted(unknown)}"


def test_references_state_required_facts() -> None:
    args = _text(REFS / "arguments.md")
    assert "`${count}: int`" in args and "invalid" in args and "`${count: int}`" in args
    emb = _text(REFS / "embedded-arguments.md")
    assert "Los Angeles" in emb and '"${city}" "${team}"' in emb and "${team:\\S+}" in emb
    assert "defaults" in emb and "not checked against the pattern" in emb and "escaped" in emb
    res = _text(REFS / "resources-and-variable-files.md")
    assert "uv add pyyaml" in res and "rf-setup" in res and "KW06" in res and "admin.Open App" in res
    assert "robot:private" in res and "`AS`" in res and "${CURDIR}" in res and "get_variables" in res
    var = _text(REFS / "variables-and-scopes.md")
    assert "VAR    ${X}    a    scope=SUITE" in var and "$status == 'ready'" in var
    assert "Set Suite Variable" in var and "SUITES" in var and "Secret" in var
    ctl = _text(REFS / "control-structures.md")
    assert "Wait Until Keyword Succeeds" in ctl and "do not wait" in ctl and "four levels" in ctl
    assert "`None`" in ctl and "mode=STRICT" in ctl and "limit=" in ctl


def test_bdd_steps_defined_without_prefix() -> None:
    bdd_def = re.compile(r"^(Given|When|Then|And|But)\s", re.M)
    for path in list(EXAMPLES.rglob("*.resource")):
        kws = _text(path).split("*** Keywords ***", 1)[-1]
        assert not bdd_def.search(kws), path.name
    for name, i, block in _code_blocks():
        if "*** Keywords ***" in block and not _is_counter_example(block):
            assert not bdd_def.search(block.split("*** Keywords ***", 1)[1]), f"{name}#{i}"


# --- 2. Robot Framework layer ---------------------------------------------------


@pytest.fixture()
def example_copy(tmp_path: Path) -> Path:
    dest = tmp_path / "examples"
    shutil.copytree(EXAMPLES, dest, ignore=shutil.ignore_patterns("__pycache__", ".robocop_cache"))
    return dest


def _place(block: str, root: Path, idx: int) -> tuple[Path, str | None]:
    """Write a code block into the example copy; return (file to dry-run, suite to run for real)."""
    folder = root / "tests" / "api" if "../../resources/" in block else root / "tests"
    if "*** Test Cases ***" in block:
        path = folder / f"snippet_{idx}.robot"
        path.write_text(block, encoding="utf-8")
        return path, f"Snippet {idx}"
    if "*** Keywords ***" in block or "*** Variables ***" in block:
        res = root / "resources" / f"snippet_{idx}.resource"
        res.write_text(block, encoding="utf-8")
        wrapper = root / "tests" / f"wrapper_{idx}.robot"
        wrapper.write_text(
            f"*** Settings ***\nResource    ../resources/snippet_{idx}.resource\n\n"
            "*** Test Cases ***\nImport Only\n    No Operation\n",
            encoding="utf-8",
        )
        return wrapper, None
    init = folder / "__init__.robot"
    init.write_text(block, encoding="utf-8")
    return folder, None


BLOCK_PARAMS = [
    pytest.param(name, i, block, id=f"{name}-{i}") for name, i, block in _code_blocks()
    if not _is_counter_example(block)
]


@needs_robot
@pytest.mark.parametrize(("name", "idx", "block"), BLOCK_PARAMS)
def test_code_block_dry_runs_and_runs(name: str, idx: int, block: str, example_copy: Path) -> None:
    need = _min_version(block)
    if need and _rf_version() < need:
        pytest.skip(f"block needs RF {need}")
    target, suite = _place(block, example_copy, idx)
    out = example_copy / "out"
    res = _robot(["--dryrun", "--outputdir", str(out), str(target)], example_copy)
    log = res.stdout + res.stderr
    assert res.returncode == 0 and "[ ERROR ]" not in log and "[ WARN ]" not in log, log
    if suite:
        env = {**os.environ, "APP_PASSWORD": "s3cret"}
        res = _robot(["--outputdir", str(out), "--suite", suite, "tests"], example_copy, env=env)
        assert res.returncode == 0, res.stdout + res.stderr


@needs_robot
def test_examples_dry_run_and_run(example_copy: Path) -> None:
    out = example_copy / "out"
    for extra in (["--dryrun"], []):
        res = _robot([*extra, "--outputdir", str(out), "tests"], example_copy)
        log = res.stdout + res.stderr
        assert res.returncode == 0 and "[ ERROR ]" not in log and "[ WARN ]" not in log, log
        total, passed, _skipped = _count_tests(out / "output.xml")
        assert total == passed == 14


@needs_robot
def test_yaml_variable_files(example_copy: Path) -> None:
    pytest.importorskip("yaml", reason="PyYAML not installed; YAML example skipped")
    out = example_copy / "out"
    for env_file, url in (("staging.yaml", "https://staging.example.com"), ("dev.yaml", "http://localhost:8080")):
        check = example_copy / "tests" / "env_check.robot"
        check.write_text(
            "*** Test Cases ***\nValues\n"
            f"    Should Be Equal    ${{BASE_URL}}    {url}\n"
            f"    Should Be Equal    ${{ENVIRONMENT}}    {env_file.split('.')[0]}\n",
            encoding="utf-8",
        )
        res = _robot(["--outputdir", str(out), "--variablefile", f"variables/{env_file}",
                      "tests/env.robot", "tests/env_check.robot"], example_copy)
        assert res.returncode == 0, res.stdout + res.stderr


@needs_robot
def test_typed_keyword_template_runs(example_copy: Path) -> None:
    if _rf_version() < (7, 3):
        pytest.skip("typed arguments need RF 7.3")
    suite = example_copy / "tests" / "typed.robot"
    suite.write_text(
        "*** Settings ***\nResource    ../resources/keywords.resource\n\n*** Test Cases ***\nTyped\n"
        "    VAR    @{cart}    @{EMPTY}\n    ${n}=    Add Items To Cart    ${cart}    apple    2    gift=yes\n"
        "    Should Be Equal    ${n}    ${3}\n    Cart Should Contain    ${cart}    apple    2\n",
        encoding="utf-8",
    )
    res = _robot(["--outputdir", str(example_copy / "out"), str(suite)], example_copy)
    assert res.returncode == 0, res.stdout + res.stderr


def _recipes() -> list[tuple[str, str, int]]:
    out = []
    for path, heading in ((SKILL_MD, "Tags and selection"), (REFS / "tags-and-selection.md", "Recipes")):
        for row in _rows(_section(_text(path), heading))[1:]:
            m = re.fullmatch(r"`(robot [^`]+)`", row[1])
            if m and row[2].isdigit():
                out.append((path.name, m.group(1), int(row[2])))
    return out


RECIPES = _recipes()


def test_recipes_found() -> None:
    assert len([r for r in RECIPES if r[0] == "SKILL.md"]) >= 5
    assert len(RECIPES) >= 12


@needs_robot
@pytest.mark.parametrize(("doc", "command", "count"), RECIPES, ids=[f"{d}:{c}" for d, c, _ in RECIPES])
def test_selection_recipe_counts(doc: str, command: str, count: int, example_copy: Path) -> None:
    args = shlex.split(command)[1:]
    out = example_copy / "out"
    res = _robot(["--dryrun", "--outputdir", str(out), *args], example_copy)
    assert res.returncode == 0, res.stdout + res.stderr
    total, _passed, _skipped = _count_tests(out / "output.xml")
    assert total == count, f"{command}: selected {total}, documented {count}"


def _untemplated_control(path: Path, source: str | None = None) -> list[str]:
    from robot.api import get_model
    from robot.api.parsing import ModelVisitor

    model = get_model(source if source is not None else str(path))
    suite_template = any(
        type(s).__name__ == "TestTemplate" and s.value and s.value.upper() != "NONE"
        for sec in model.sections for s in getattr(sec, "body", []) if type(sec).__name__ == "SettingSection"
    )
    bad: list[str] = []

    class Visitor(ModelVisitor):
        def visit_TestCase(self, node):  # robot API naming
            templated = suite_template
            for item in node.body:
                if type(item).__name__ == "Template":
                    templated = bool(item.value) and item.value.upper() != "NONE"
            if not templated:
                kinds = {type(i).__name__ for i in node.body}
                hit = kinds & {"For", "While", "If", "Try"}
                if hit:
                    bad.append(f"{path.name}: {node.name}: {sorted(hit)}")

    Visitor().visit(model)
    return bad


@needs_robot
def test_no_control_structures_in_untemplated_tests() -> None:
    bad = []
    for path in sorted(EXAMPLES.rglob("*.robot")):
        bad += _untemplated_control(path)
    for name, i, block in _code_blocks():
        if "*** Test Cases ***" in block and not _is_counter_example(block):
            bad += _untemplated_control(Path(f"{name}#{i}"), block)
    assert not bad, bad


@needs_robot
def test_rf_conventions_on_examples() -> None:
    import json

    res = subprocess.run([sys.executable, str(SCRIPT), str(EXAMPLES)], capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["tests"]["template_suites"] >= 1
    assert data["tests"]["tag_settings"]["test_tags"] >= 1 and data["tests"]["tag_settings"]["force_tags"] == 0
    assert data["layout"]["init_files"] >= 1
    assert data["legacy"] == [] and data["tests"]["control_in_untemplated"] == 0


# --- 3. Robocop 9.x layer --------------------------------------------------------


@functools.lru_cache(maxsize=1)
def _robocop_cmd() -> tuple[str, ...] | None:
    local = shutil.which("robocop", path=str(Path(sys.executable).parent)) or shutil.which("robocop")
    candidates: list[tuple[str, ...]] = []
    if local:
        candidates.append((local,))
    uvx = shutil.which("uvx")
    if uvx:
        candidates.append((uvx, "--from", "robotframework-robocop>=9.1,<10", "robocop"))
    for cmd in candidates:
        try:
            res = subprocess.run([*cmd, "--version"], capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired):
            continue
        m = re.search(r"(\d+)\.\d+", res.stdout + res.stderr)
        if res.returncode == 0 and m and m.group(1) == "9":
            return cmd
    return None


def _robocop() -> tuple[str, ...]:
    cmd = _robocop_cmd()
    if cmd is None:
        pytest.skip("robocop 9.x not installed and not available via uvx")
    return cmd


def _robocop_check(paths: list[Path], selects: list[str], cwd: Path) -> list[tuple[str, str]]:
    args = [a for s in selects for a in ("-s", s)]
    res = subprocess.run(
        [*_robocop(), "check", "--no-cache", "--ignore-file-config", *args, *map(str, paths)],
        capture_output=True, text=True, timeout=300, cwd=cwd,
    )
    return re.findall(r"^(\S+):\d+:\d+ ([A-Z]+\d{2}) ", res.stdout, re.M)


def test_robocop_rule_ids_exist_with_documented_names() -> None:
    res = subprocess.run([*_robocop(), "list", "rules"], capture_output=True, text=True, timeout=300)
    rules = dict(re.findall(r"^([A-Z]+\d{2}) \[[A-Z]\]: ([a-z0-9-]+):", res.stdout, re.M))
    assert rules, res.stdout[:500]
    wrong = {rid: (name, rules.get(rid)) for rid, name in ROBOCOP_RULES.items() if rules.get(rid) != name}
    assert not wrong, wrong


@pytest.mark.parametrize("construct", list(LEGACY_CASES))
def test_robocop_reports_documented_rule_per_construct(construct: str, tmp_path: Path) -> None:
    source, expected = LEGACY_CASES[construct]
    path = tmp_path / "legacy.robot"
    path.write_text(source, encoding="utf-8")
    found = {rid for _src, rid in _robocop_check([path], ["DEPR*", "ANN04"], tmp_path)}
    assert found == expected, (construct, found)


def test_examples_and_template_are_robocop_clean(tmp_path: Path) -> None:
    ex = tmp_path / "examples"
    shutil.copytree(EXAMPLES, ex, ignore=shutil.ignore_patterns("__pycache__", ".robocop_cache"))
    template = tmp_path / "template.resource"
    template.write_text(_robot_blocks(_section(_text(SKILL_MD), "Keyword anatomy"))[0], encoding="utf-8")
    selects = ["DEPR*", "ERR*", "ORD02", "NAME*", "VAR07", "ARG03", "KW06"]
    issues = _robocop_check([ex, template], selects, tmp_path)
    assert not issues, issues


def test_documented_robocop_commands_disable_the_cache() -> None:
    """Every documented `robocop check`/`format` run passes --no-cache, so following the
    skill never leaves .robocop_cache/ in the user's project (modernize-plugin-agents-and-hooks)."""
    skill_dir = SKILL_MD.parent
    for path in [SKILL_MD, *sorted((skill_dir / "references").glob("*.md"))]:
        for line in path.read_text(encoding="utf-8").splitlines():
            for cmd in re.findall(r"robocop (?:check|format)\b[^`\n]*", line):
                assert "--no-cache" in cmd, f"{path.name}: {cmd}"
