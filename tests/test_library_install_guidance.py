"""Library skills defer installation to rf-setup and never show bare pip recipes.

Spec: openspec capability ``library-skill-install-guidance``.

The six library skills (browser, selenium, appium, requests, restinstance,
platynui) must:

* carry the same ``uv add ...`` command(s) that rf-setup's Step 4 table lists,
* point to ``rf-setup`` from their ``## Installation`` block and Companion Skills,
* contain no ``pip install`` / ``pip3 install`` outside a line labelled as a pip
  alternative (``pip alternative`` or ``# pip:``),
* never mention ``webdriver-manager`` / ``webdriver_manager``; rf-selenium never
  shows ``executable_path=``,
* (rf-browser) default to ``[bb]`` + ``rfbrowser install``; ``rfbrowser init``
  only in the labelled Node.js escape hatch,
* (rf-platynui) keep the pre-release opt-in / pin in uv form and the 0.9.2 warning.

Checks run over root ``skills/`` and the synced plugin copies.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SETUP_SKILL_MD = ROOT / "skills" / "rf-setup" / "SKILL.md"
FIXTURES = ROOT / "tests" / "fixtures" / "install_guidance"

LIBRARY_KEYS = ["browser", "selenium", "appium", "requests", "restinstance", "platynui"]

SKILL_DIRS = {
    **{("root", k): ROOT / "skills" / f"rf-{k}" for k in LIBRARY_KEYS},
    **{("plugin", k): ROOT / "plugins" / "rf-agentskills" / "skills" / f"rf-{k}" for k in LIBRARY_KEYS},
}
PARAMS = [pytest.param(chan, key, id=f"{chan}-{key}") for chan, key in SKILL_DIRS]

TEXT_SUFFIXES = {".md", ".robot", ".resource", ".py", ".txt", ".yaml", ".yml", ".json", ".toml"}

PIP_RE = re.compile(r"\bpip3? install\b")
PIP_LABEL_RE = re.compile(r"pip alternative|#\s*pip:", re.IGNORECASE)
WDM_RE = re.compile(r"webdriver[-_]manager")
EXEC_PATH_RE = re.compile(r"executable_path\s*=")
RFBROWSER_INIT_RE = re.compile(r"rfbrowser init")


# --- helpers ---------------------------------------------------------------


def skill_text_files(skill_dir: Path) -> list[Path]:
    files = [skill_dir / "SKILL.md"]
    for sub in ("references", "assets"):
        base = skill_dir / sub
        if base.is_dir():
            files += sorted(
                p for p in base.rglob("*") if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES
            )
    return [f for f in files if f.is_file()]


def scan(skill_dir: Path, pattern: re.Pattern, label: re.Pattern | None = None) -> list[str]:
    """Return ``file:line: text`` for each line matching ``pattern`` (unless labelled)."""
    hits = []
    for path in skill_text_files(skill_dir):
        for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line) and not (label and label.search(line)):
                hits.append(f"{path.relative_to(skill_dir)}:{no}: {line.strip()}")
    return hits


def scan_bare_pip(skill_dir: Path) -> list[str]:
    return scan(skill_dir, PIP_RE, PIP_LABEL_RE)


def section(text: str, heading_re: str) -> str:
    """Body of the first ``## `` section whose heading matches ``heading_re``."""
    m = re.search(rf"^##\s+{heading_re}[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.M | re.S | re.I)
    return m.group(1) if m else ""


def setup_install_commands() -> dict[str, list[str]]:
    """rf-setup Step 4 table: usage skill (e.g. ``rf-browser``) -> install commands."""
    body = section(SETUP_SKILL_MD.read_text(encoding="utf-8"), r"Step 4")
    table: dict[str, list[str]] = {}
    for line in body.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or not cells[1].startswith("`uv add"):
            continue
        cmd = cells[1].strip("`")
        skill = cells[3].strip("`")
        table.setdefault(skill, []).append(cmd)
    return table


def fenced_blocks(text: str) -> list[tuple[str, list[str]]]:
    """Return (context_before_fence, block_lines) for each fenced code block."""
    lines = text.splitlines()
    out, i = [], 0
    while i < len(lines):
        if lines[i].lstrip().startswith("```"):
            ctx = " ".join(lines[max(0, i - 3):i])
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("```"):
                j += 1
            out.append((ctx, lines[i + 1:j]))
            i = j + 1
        else:
            i += 1
    return out


def rfbrowser_init_outside_node(text: str) -> list[str]:
    """Lines with ``rfbrowser init`` not labelled as the Node.js path."""
    bad = []
    in_block_ok: set[int] = set()
    lines = text.splitlines()
    # Index lines inside fenced blocks whose preceding context mentions Node.
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("```"):
            ctx = " ".join(lines[max(0, i - 3):i])
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("```"):
                j += 1
            if "Node" in ctx:
                in_block_ok.update(range(i + 1, j))
            i = j + 1
        else:
            i += 1
    for idx, line in enumerate(lines):
        if RFBROWSER_INIT_RE.search(line) and "Node" not in line and idx not in in_block_ok:
            bad.append(f"{idx + 1}: {line.strip()}")
    return bad


# --- (a)-(c): pointer, uv line, companion ----------------------------------


def test_setup_table_parsed():
    table = setup_install_commands()
    for key in LIBRARY_KEYS:
        assert table.get(f"rf-{key}"), f"rf-setup Step 4 has no row for rf-{key}"


@pytest.mark.parametrize("chan,key", PARAMS)
def test_uv_add_matches_setup_table(chan, key):
    text = (SKILL_DIRS[chan, key] / "SKILL.md").read_text(encoding="utf-8")
    missing = [c for c in setup_install_commands()[f"rf-{key}"] if c not in text]
    assert not missing, f"rf-{key} SKILL.md lacks rf-setup install command(s): {missing}"


@pytest.mark.parametrize("chan,key", PARAMS)
def test_installation_block_points_to_setup(chan, key):
    text = (SKILL_DIRS[chan, key] / "SKILL.md").read_text(encoding="utf-8")
    body = section(text, r"Installation")
    assert body, f"rf-{key} SKILL.md has no '## Installation' section"
    assert "rf-setup" in body, f"rf-{key} Installation block does not point to rf-setup"


@pytest.mark.parametrize("chan,key", PARAMS)
def test_companion_skills_list_setup(chan, key):
    text = (SKILL_DIRS[chan, key] / "SKILL.md").read_text(encoding="utf-8")
    body = section(text, r"Companion Skills")
    assert body, f"rf-{key} SKILL.md has no '## Companion Skills' section"
    # One identifier per skill: the plugin copy names `rf-setup` too.
    token = "`rf-setup`"
    assert token in body, f"rf-{key} Companion Skills does not list {token}"


# --- (d)-(e): forbidden recipes --------------------------------------------


@pytest.mark.parametrize("chan,key", PARAMS)
def test_no_bare_pip_install(chan, key):
    hits = scan_bare_pip(SKILL_DIRS[chan, key])
    assert not hits, "bare pip install (label the line 'pip alternative' or '# pip:'):\n" + "\n".join(hits)


@pytest.mark.parametrize("chan,key", PARAMS)
def test_no_webdriver_manager(chan, key):
    hits = scan(SKILL_DIRS[chan, key], WDM_RE)
    assert not hits, "webdriver-manager mentioned:\n" + "\n".join(hits)


@pytest.mark.parametrize("chan", ["root", "plugin"])
def test_selenium_no_executable_path(chan):
    hits = scan(SKILL_DIRS[chan, "selenium"], EXEC_PATH_RE)
    assert not hits, "executable_path= in rf-selenium:\n" + "\n".join(hits)


@pytest.mark.parametrize("chan", ["root", "plugin"])
def test_selenium_states_selenium_manager(chan):
    body = section((SKILL_DIRS[chan, "selenium"] / "SKILL.md").read_text(encoding="utf-8"), r"Installation")
    assert "Selenium Manager" in body
    assert "browser" in body.lower()


# --- (f): rf-browser -------------------------------------------------------


@pytest.mark.parametrize("chan", ["root", "plugin"])
def test_browser_default_is_bb(chan):
    body = section((SKILL_DIRS[chan, "browser"] / "SKILL.md").read_text(encoding="utf-8"), r"Installation")
    blocks = fenced_blocks(body)
    assert blocks, "rf-browser Installation block has no code block"
    commands = [ln.split("#")[0].strip() for ln in blocks[0][1]]
    commands = [c for c in commands if c]
    assert commands[:2] == ['uv add "robotframework-browser[bb]"', "uv run rfbrowser install chromium"], commands
    assert not any("rfbrowser init" in c for c in commands)


@pytest.mark.parametrize("chan", ["root", "plugin"])
def test_browser_rfbrowser_init_only_in_node_escape_hatch(chan):
    skill_dir = SKILL_DIRS[chan, "browser"]
    bad = []
    for path in skill_text_files(skill_dir):
        for hit in rfbrowser_init_outside_node(path.read_text(encoding="utf-8")):
            bad.append(f"{path.relative_to(skill_dir)}:{hit}")
    assert not bad, "rfbrowser init outside the Node.js escape hatch:\n" + "\n".join(bad)


@pytest.mark.parametrize("chan", ["root", "plugin"])
def test_browser_troubleshooting_has_no_pip_reinstall(chan):
    text = (SKILL_DIRS[chan, "browser"] / "references" / "troubleshooting.md").read_text(encoding="utf-8")
    assert not re.search(r"\bpip3? (un)?install\b", text)
    assert "rf-setup" in text


# --- (g): rf-platynui ------------------------------------------------------


@pytest.mark.parametrize("chan", ["root", "plugin"])
def test_platynui_prerelease_uv_form(chan):
    text = (SKILL_DIRS[chan, "platynui"] / "SKILL.md").read_text(encoding="utf-8")
    body = section(text, r"Installation")
    assert re.search(r"uv add (--prerelease allow robotframework-PlatynUI|robotframework-PlatynUI==0\.12\.0\.dev)", body)
    assert "0.9.2" in body and "BareMetal" in body


# --- (h): negative fixture -------------------------------------------------


def test_scanner_flags_bare_pip_in_fixture():
    hits = scan_bare_pip(FIXTURES / "bad-skill")
    assert hits == ["SKILL.md:6: pip install robotframework-browser"], hits


def test_scanner_accepts_labelled_pip_alternative():
    text = (FIXTURES / "bad-skill" / "SKILL.md").read_text(encoding="utf-8")
    assert "# pip:" in text and "pip alternative" in text  # labelled lines exist and are not flagged
