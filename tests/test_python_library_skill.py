"""Structure and runnable content of the rf-python-library skill (add-rf-python-library-skill D1, D9, D10).

* SKILL.md: frontmatter, size, section order, version gate, template, scope table,
  workflow, 13 Gotchas with checker finding ids, reference table, Companion Skills;
* references: table of contents for long files, one home per topic;
* code blocks: every ```python block that starts with ``# file: <Name>.py`` is saved
  and checked with the bundled checker (clean, or exactly the findings named on a
  ``# Wrong: <id>, <id>`` line; ``# check: skip`` for listener-only and pytest
  modules); every ```robotframework block with ``# file:`` runs with ``robot``
  next to the Python blocks of the same document (``# run: <args>`` adds options);
* examples: the suites in assets/examples pass and the example libraries check clean;
* distribution: channel copies, hook, README, rf-setup pointer.
"""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "rf-python-library"
SKILL_MD = SKILL / "SKILL.md"
SCRIPT = SKILL / "scripts" / "check_library.py"
EXAMPLES = SKILL / "assets" / "examples"
REFERENCES = SKILL / "references"
PLUGIN = ROOT / "plugins" / "rf-agentskills"

HAS_ROBOT = importlib.util.find_spec("robot") is not None
requires_robot = pytest.mark.skipif(not HAS_ROBOT, reason="robotframework not installed")

SECTIONS = [
    "When to use",  # trigger block (tune-skill-descriptions D12)
    "Quick reference and version gate",
    "Default library template",
    "Decisions",
    "Placement and import",
    "Agent workflow",
    "Gotchas",
    "When to read the references",
    "Companion Skills",
]
REFERENCE_FILES = {"conversion.md", "api-variants.md", "listeners.md", "communication.md",
                   "packaging-and-docs.md"}
TOC_THRESHOLD = 100
BLOCK = re.compile(r"^```(python|robotframework)\n(.*?)^```", re.S | re.M)


def _text(path: Path = SKILL_MD) -> str:
    return path.read_text(encoding="utf-8")


def _frontmatter() -> dict:
    m = re.match(r"---\n(.*?)\n---\n", _text(), re.S)
    assert m
    return yaml.safe_load(m.group(1))


def _section(name: str, text: str | None = None) -> str:
    text = _text() if text is None else text
    m = re.search(rf"^## {re.escape(name)}[ \t]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    assert m, name
    return m.group(1)


def _robot_version() -> tuple[int, int]:
    from robot.version import VERSION
    return tuple(int(p) for p in re.findall(r"\d+", VERSION)[:2])  # type: ignore[return-value]


def _checker_ids() -> set[str]:
    spec = importlib.util.spec_from_file_location("_check_library_for_skill_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return set(mod.FINDING_IDS)


# ---------------------------------------------------------------------------
# SKILL.md structure
# ---------------------------------------------------------------------------


def test_frontmatter_and_size() -> None:
    fm = _frontmatter()
    assert fm["name"] == "rf-python-library"
    assert fm["description"] and len(fm["description"]) <= 1024
    compat = fm["compatibility"]
    assert "Python 3.10+" in compat and "robotframework>=7" in compat
    assert fm["license"] == "Apache-2.0"
    assert len(_text().splitlines()) <= 300


def test_section_order() -> None:
    headings = re.findall(r"^## (.+?)\s*$", _text(), re.M)
    assert headings == SECTIONS


def test_version_gate_table() -> None:
    gate = _section("Quick reference and version gate")
    assert 'uv run python -c "import robot; print(robot.__version__)"' in gate
    assert "251" in gate
    rows = {}
    for line in gate.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 2 and re.fullmatch(r"\d\.\d", cells[1]):
            rows[cells[0]] = cells[1]
    joined = {v: " ".join(k for k, val in rows.items() if val == v) for v in set(rows.values())}
    expected = {
        "6.1": ("async def", "dry_run_active"),
        "7.0": ("Literal", "embedded plus normal arguments", "listener API v3"),
        "7.1": ("ROBOT_LISTENER_PRIORITY",),
        "7.2": ("@library",),
        "7.4": ("Secret", "object"),
        "7.5": ("Markdown",),
    }
    for version, terms in expected.items():
        for term in terms:
            assert term in joined.get(version, ""), (version, term, rows)


def _template() -> str:
    m = re.search(r"```python\n(# file: MyLibrary\.py\n.*?)```", _section("Default library template"), re.S)
    assert m, "template block missing"
    return m.group(1)


def test_template_sets_scope_explicitly_but_not_suite() -> None:
    template = _template()
    scope = re.search(r"@library\(scope=\"(\w+)\"", template)
    assert scope and scope.group(1) != "SUITE"
    assert 'scope="SUITE"' not in template
    assert "scope table" in template
    for part in ("@keyword", "from robot.api import logger", "AssertionError", '"""'):
        assert part in template
    # State only in __init__: no self.<attr> assignment in other methods.
    body = template.split("def __init__", 1)[1]
    rest = body.split("@keyword", 1)[1]
    assert not re.search(r"self\.\w+(\[.*\])?\s*[+\-*/]?=(?!=)", rest)


@requires_robot
def test_template_checks_clean(tmp_path: Path) -> None:
    (tmp_path / "libraries").mkdir()
    (tmp_path / "libraries" / "MyLibrary.py").write_text(_template(), encoding="utf-8")
    res = subprocess.run([sys.executable, str(SCRIPT), "libraries/MyLibrary.py"], cwd=tmp_path,
                         capture_output=True, text=True, timeout=120)
    assert res.returncode == 0, res.stderr
    bad = [f for f in json.loads(res.stdout)["libraries"][0]["findings"] if f["severity"] != "info"]
    assert not bad, bad


def test_scope_table_follows_user_guide() -> None:
    decisions = _section("Decisions")
    assert '"Library scope"' in decisions and "User Guide" in decisions
    rows = [ln for ln in decisions.splitlines() if ln.startswith("| ")]
    scope_rows = [r for r in rows if "State must live" in r or re.search(r"\| `(TEST|SUITE|GLOBAL)`", r)
                  or "`GLOBAL` avoids" in r]
    scopes = set(re.findall(r"`(TEST|SUITE|GLOBAL|SUITES|TASK)`", " ".join(scope_rows)))
    assert scopes == {"TEST", "SUITE", "GLOBAL"}
    table = " ".join(scope_rows)
    assert "new instance for every test" in table and "independent" in table
    assert table.count("cleanup keyword") >= 2
    assert "module libraries are always global" in table
    assert "different arguments creates a new instance regardless of scope" in decisions


def test_decision_tables_present() -> None:
    decisions = _section("Decisions")
    for term in ("Module library", "Class library", "Hybrid", "Dynamic", "PythonLibCore",
                 "ContinuableFailure", "SkipExecution", "FatalError", "logger.console", "html=True"):
        assert term in decisions, term


def test_placement_shows_import_by_name_and_python_path() -> None:
    placement = _section("Placement and import")
    assert "Library    MyLibrary" in placement
    assert 'python-path = ["resources", "libraries"]' in placement and "--pythonpath libraries" in placement
    assert "AS" in placement and "uv add" in placement and "rf-setup" in placement


def test_workflow_order_and_safety_line() -> None:
    workflow = _section("Agent workflow")
    steps = re.findall(r"^(\d+)\. ", workflow, re.M)
    assert steps == [str(i) for i in range(1, 9)]
    pos = {key: workflow.index(key) for key in (
        "robot.__version__", "scripts/check_library.py", "libdoc", "pytest", "--dryrun",
        "--loglevel DEBUG")}
    assert list(pos) == sorted(pos, key=pos.get)
    assert "uv run python scripts/check_library.py libraries/<Name>.py" in workflow
    assert "import and `__init__` code" in workflow and "own project libraries only" in workflow
    for blind in ("variables", "named-argument typos", "embedded-argument mismatches", "`str` in unions"):
        assert blind in workflow
    assert "rf-results" in workflow and "rf-robotcode" in workflow


GOTCHA_TRAPS = {
    1: ("`@library` disables automatic keyword discovery", "public_method_not_keyword"),
    2: ("Functions imported into a module library", "leaked_keyword"),
    3: ("default `TEST` scope", "state_in_test_scope"),
    4: ("inline type in a library embedded-argument name", "keyword_creation_failed"),
    5: ("union that contains `str`", "union_with_str"),
    6: ("Implicit typing from defaults is lenient", None),
    7: ("`bool` conversion passes unknown strings through", None),
    8: ("Positional-only arguments", "positional_only_argument"),
    9: ("broad `except Exception:`", "broad_except"),
    10: ("non-main thread", None),
    11: ("without `functools.wraps`", "signature_lost"),
    12: ("Listener methods", "listener_method_exposed"),
    13: ("same library twice with different arguments", None),
}


def _gotchas() -> list[str]:
    return [ln for ln in _section("Gotchas").splitlines() if ln.startswith("- ")]


def test_gotchas_cover_the_thirteen_traps() -> None:
    bullets = _gotchas()
    assert len(bullets) >= 13
    for number, (needle, fid) in GOTCHA_TRAPS.items():
        hits = [b for b in bullets if needle in b]
        assert len(hits) == 1, (number, needle, hits)
        if fid:
            assert f"`{fid}`" in hits[0], (number, fid)
        else:
            assert "not detected" in hits[0], number
    assert any("__init__` also runs during libdoc and `--dryrun`" in b for b in bullets)
    assert any("before RF 7.5" in b for b in bullets)


def test_gotcha_ids_exist_in_checker() -> None:
    ids = _checker_ids()
    cited = set(re.findall(r"→ `([a-z_]+)`", _section("Gotchas")))
    cited |= set(re.findall(r", `([a-z_]+)`\)", _section("Gotchas")))
    assert cited and cited <= ids, cited - ids


def test_reference_table_matches_files() -> None:
    table = _section("When to read the references")
    listed = set(re.findall(r"^\| `references/([\w.-]+)` \|", table, re.M))
    assert listed == REFERENCE_FILES
    assert {p.name for p in REFERENCES.iterdir()} == REFERENCE_FILES


@pytest.mark.parametrize("name", sorted(REFERENCE_FILES))
def test_long_references_have_a_toc(name: str) -> None:
    lines = _text(REFERENCES / name).splitlines()
    if len(lines) > TOC_THRESHOLD:
        assert any(re.match(r"- \[.+\]\(#.+\)", ln) for ln in lines[:15]), name


def test_companion_skills_resolve() -> None:
    names = set(re.findall(r"`(rf-[a-z-]+)`", _section("Companion Skills")))
    shipped = {p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file()}
    assert {"rf-language", "rf-setup", "rf-libdoc", "rf-results", "rf-robotcode"} <= names
    assert names <= shipped
    assert "rf-python-library" not in names


TOPICS = {
    "Enum": "conversion.md", "TypedDict": "conversion.md", "Secret": "conversion.md",
    "ROBOT_LIBRARY_CONVERTERS": "conversion.md", "types=": "conversion.md",
    "get_keyword_names": "api-variants.md", "PythonLibCore": "api-variants.md",
    "async def": "api-variants.md", "Remote": "api-variants.md",
    "end_test(data, result)": "listeners.md", "ROBOT_LISTENER_PRIORITY": "listeners.md",
    'listener="SELF"': "listeners.md",
    "ROBOT_SUPPRESS_NAME": "communication.md", "TimeoutExceeded": "communication.md",
    "dry_run_active": "communication.md", "also_console": "communication.md",
    "ROBOT_LIBRARY_VERSION": "packaging-and-docs.md", "MARKDOWN": "packaging-and-docs.md",
    "package-data": "packaging-and-docs.md",
}


@pytest.mark.parametrize("term", sorted(TOPICS))
def test_topic_has_a_home(term: str) -> None:
    assert term in _text(REFERENCES / TOPICS[term]), term


def test_custom_converter_end_to_end() -> None:
    text = _text(REFERENCES / "conversion.md")
    section = text.split("## Custom converters", 1)[1]
    assert "raise ValueError" in section
    assert "converters={Sku: parse_sku}" in section
    assert "sku: Sku" in section


def test_no_pip_install_and_no_agent_variables() -> None:
    for path in [SKILL_MD, *REFERENCES.iterdir()]:
        text = _text(path)
        assert "pip install" not in text, path.name
        assert not re.search(r"\$\{(CLAUDE|COPILOT|CURSOR)_", text), path.name


def test_documented_robocop_commands_use_no_cache() -> None:
    for path in [SKILL_MD, *REFERENCES.iterdir()]:
        for line in _text(path).splitlines():
            if "robocop check" in line:
                assert "--no-cache" in line, (path.name, line)


# ---------------------------------------------------------------------------
# Code blocks in SKILL.md and references
# ---------------------------------------------------------------------------


def _blocks(path: Path) -> list[tuple[str, str | None, str]]:
    out = []
    for lang, body in BLOCK.findall(_text(path)):
        m = re.match(r"# file: (\S+)\n", body)
        out.append((lang, m.group(1) if m else None, body))
    return out


DOCS = [SKILL_MD, *sorted(REFERENCES.glob("*.md"))]


def _min_version(body: str) -> tuple[int, int]:
    m = re.search(r"^# RF (\d+)\.(\d+)\+", body, re.M)
    return (int(m.group(1)), int(m.group(2))) if m else (7, 0)


@pytest.mark.parametrize("doc", DOCS, ids=[d.name for d in DOCS])
def test_python_blocks_are_complete_files(doc: Path) -> None:
    for lang, name, body in _blocks(doc):
        if lang == "python":
            assert name and name.endswith(".py"), (doc.name, body[:60])


def _stage(doc: Path, tmp_path: Path) -> list[tuple[str, str, str]]:
    staged = []
    for lang, name, body in _blocks(doc):
        if name:
            (tmp_path / name).write_text(body, encoding="utf-8")
            staged.append((lang, name, body))
    return staged


@requires_robot
@pytest.mark.parametrize("doc", DOCS, ids=[d.name for d in DOCS])
def test_python_blocks_check_as_documented(doc: Path, tmp_path: Path) -> None:
    for lang, name, body in _stage(doc, tmp_path):
        if lang != "python" or "# check: skip" in body or _robot_version() < _min_version(body):
            continue
        res = subprocess.run([sys.executable, str(SCRIPT), name], cwd=tmp_path, capture_output=True,
                             text=True, timeout=120)
        assert res.returncode == 0, (name, res.stderr)
        found = {f["id"] for f in json.loads(res.stdout)["libraries"][0]["findings"]
                 if f["severity"] != "info"}
        wrong = re.search(r"^# Wrong: (.+)$", body, re.M)
        expected = {w.strip() for w in wrong.group(1).split(",")} if wrong else set()
        assert found == expected, (doc.name, name, found)


@requires_robot
@pytest.mark.parametrize("doc", DOCS, ids=[d.name for d in DOCS])
def test_robot_blocks_run(doc: Path, tmp_path: Path) -> None:
    staged = _stage(doc, tmp_path)
    for lang, name, body in staged:
        if lang != "robotframework" or _robot_version() < _min_version(body):
            continue
        extra = re.findall(r"^# run: (.+)$", body, re.M)
        cmd = [sys.executable, "-m", "robot", "--pythonpath", str(tmp_path), "--outputdir",
               str(tmp_path / "out" / name), "--console", "none", *(extra[0].split() if extra else []), name]
        res = subprocess.run(cmd, cwd=tmp_path, capture_output=True, text=True, timeout=300,
                             env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"})
        assert res.returncode == 0, (doc.name, name, res.stdout[-800:], res.stderr[-800:])


# ---------------------------------------------------------------------------
# Examples (also run by CI)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def examples_run(tmp_path_factory) -> Path:
    if not HAS_ROBOT:
        pytest.skip("robotframework not installed")
    work = tmp_path_factory.mktemp("pylib-examples")
    shutil.copytree(EXAMPLES, work / "examples", ignore=shutil.ignore_patterns("__pycache__"))
    out = work / "out"
    res = subprocess.run(
        [sys.executable, "-m", "robot", "--pythonpath", str(work / "examples"), "--listener",
         "ResultListener", "--outputdir", str(out), "--console", "none", str(work / "examples")],
        capture_output=True, text=True, timeout=300)
    assert res.returncode == 0, res.stdout[-1500:] + res.stderr[-1500:]
    return out


def test_example_files_present() -> None:
    names = {p.name for p in EXAMPLES.iterdir() if p.is_file()}
    assert {"ExampleLibrary.py", "converters.py", "ResultListener.py", "example_library.robot",
            "converters.robot", "listener.robot"} <= names


def test_examples_pass(examples_run: Path) -> None:
    from robot.api import ExecutionResult

    result = ExecutionResult(str(examples_run / "output.xml"))
    stats = result.statistics.total
    assert stats.failed == 0 and stats.passed >= 10 and stats.skipped == 1
    summary = json.loads((examples_run / "result-summary.json").read_text())
    assert summary["total"] == stats.passed + stats.skipped and summary["skipped"] == 1


@requires_robot
def test_examples_clean() -> None:
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "ExampleLibrary.py", "converters.py", "ResultListener.py"],
        cwd=EXAMPLES, capture_output=True, text=True, timeout=120,
        env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"})
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["summary"]["error"] == 0 and data["summary"]["warning"] == 0, data
    scopes = {lib["library"]["name"]: lib["library"]["scope"] for lib in data["libraries"]}
    assert scopes["ExampleLibrary"] == "SUITE"
    example = _text(EXAMPLES / "ExampleLibrary.py")
    assert "def clear_inventory" in example and "Literal" in example and "logger" in example


# ---------------------------------------------------------------------------
# Distribution and cross-links
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("channel", [PLUGIN / "skills"])
def test_channel_copies_are_regular_files(channel: Path) -> None:
    copy = channel / "rf-python-library"
    script = copy / "scripts" / "check_library.py"
    assert script.is_file() and not script.is_symlink()
    assert (copy / "SKILL.md").is_file()
    for sub in ("references", "assets"):
        assert sorted(p.relative_to(copy / sub) for p in (copy / sub).rglob("*") if p.is_file()) == \
            sorted(p.relative_to(SKILL / sub) for p in (SKILL / sub).rglob("*")
                   if p.is_file() and "__pycache__" not in p.parts)


def test_plugin_copy_uses_skill_dir_command() -> None:
    text = _text(PLUGIN / "skills" / "rf-python-library" / "SKILL.md")
    assert 'uv run python "${CLAUDE_SKILL_DIR}/scripts/check_library.py" libraries/<Name>.py' in text


def test_hook_names_the_skill() -> None:
    res = subprocess.run(
        ["node", str(PLUGIN / "scripts" / "maybe_inject_rf_context.mjs")],
        input=json.dumps({"prompt": "my robot framework library says it contains no keywords"}),
        capture_output=True, text=True, timeout=30)
    if res.returncode != 0 and "not found" in res.stderr:
        pytest.skip("node not installed")
    assert "rf-python-library" in json.loads(res.stdout)["hookSpecificOutput"]["additionalContext"]


def test_rf_setup_layout_points_here() -> None:
    layout = _text(ROOT / "skills" / "rf-setup" / "references" / "project-layout.md")
    line = next(ln for ln in layout.splitlines() if "libraries/" in ln and "rf-python-library" in ln)
    assert line


def test_readme_lists_the_skill() -> None:
    readme = _text(ROOT / "README.md")
    assert "/rf-agentskills:rf-python-library" in readme
    assert "check_library.py" in readme
