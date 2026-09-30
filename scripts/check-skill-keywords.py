#!/usr/bin/env python3
"""Check that library skills only teach keywords that exist and are not deprecated.

Repository QA tooling (not shipped with the skills). For every library skill
under ``--skills-root`` it:

1. extracts keyword calls from fenced ```robotframework / ```robot blocks in
   Markdown files and from ``.robot`` / ``.resource`` files (via
   ``robot.api.get_model``),
2. resolves each call against libdoc of the skill's target library, then the
   Robot Framework standard libraries, then user keywords defined anywhere in
   the same skill (``*** Keywords ***`` sections, embedded arguments included),
3. reports ``UNKNOWN`` (not resolvable), ``DEPRECATED`` (libdoc marks it
   deprecated), ``LEGACY`` (``Run Keyword If`` / ``Run Keyword Unless``) and
   ``BAD-ARG`` (Browser ``Wait For Condition`` with an invalid condition name).

Intentional exceptions live in ``scripts/skill-keywords-allowlist.toml``::

    [[allow]]
    skill = "browser"                    # short skill key
    file = "references/locators.md"      # path relative to the skill dir
    keyword = "Create New Item"
    reason = "illustrative application keyword"

An allowlist entry that matches nothing fails the run (stale entry).

Exit status: 0 clean, 1 findings / stale entries / skipped skills with
``--require-all``, 2 usage error.
"""

from __future__ import annotations

import argparse
import contextlib
import difflib
import functools
import io
import re
import sys
import textwrap
import warnings
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover - Python < 3.11
    tomllib = None

try:
    from robot.api import get_model
    from robot.api.parsing import ModelVisitor
    from robot.libdocpkg import LibraryDocumentation
    from robot.running.arguments.embedded import EmbeddedArguments
except ImportError:  # pragma: no cover
    print("ERROR: robotframework is required (pip install robotframework)", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ALLOWLIST = REPO_ROOT / "scripts" / "skill-keywords-allowlist.toml"

# Skill key (dir name without the "rf-" prefix) -> libdoc import name.
SKILL_LIBRARIES = {
    "browser": "Browser",
    "selenium": "SeleniumLibrary",
    "appium": "AppiumLibrary",
    "requests": "RequestsLibrary",
    "restinstance": "REST",
    "platynui": "PlatynUI.BareMetal",
}
STANDARD_LIBRARIES = [
    "BuiltIn",
    "Collections",
    "String",
    "OperatingSystem",
    "DateTime",
    "Process",
    "XML",
    "Screenshot",
]
# Prefixes that may qualify a keyword call (``Browser.Click``).
LIBRARY_PREFIXES = {
    "browser", "seleniumlibrary", "appiumlibrary", "requestslibrary", "rest",
    "platynui.baremetal", "baremetal", *(lib.lower() for lib in STANDARD_LIBRARIES),
}

CONTROL = {
    "IF", "ELSE", "ELSE IF", "END", "FOR", "WHILE", "TRY", "EXCEPT", "FINALLY",
    "RETURN", "BREAK", "CONTINUE", "VAR", "GROUP",
}
SETUP_SETTINGS = {
    "suite setup", "suite teardown", "test setup", "test teardown",
    "task setup", "task teardown", "test template", "task template",
}
OTHER_SETTINGS = {
    "library", "resource", "variables", "documentation", "metadata", "name",
    "force tags", "default tags", "test tags", "task tags", "keyword tags",
    "test timeout", "task timeout",
}
LEGACY = {"runkeywordif", "runkeywordunless"}

# Wrapper keyword (normalized) -> index of the wrapped keyword-name argument.
WRAPPERS = {
    "runkeyword": 0,
    "runkeywordandreturnstatus": 0,
    "runkeywordandignoreerror": 0,
    "runkeywordandcontinueonfailure": 0,
    "runkeywordandwarnonfailure": 0,
    "runkeywordandreturn": 0,
    "runkeywordandexpecterror": 1,
    "runkeywordandreturnif": 1,
    "runkeywordif": 1,
    "runkeywordunless": 1,
    "runkeywordiftestfailed": 0,
    "runkeywordiftestpassed": 0,
    "runkeywordiftimeoutoccurred": 0,
    "runkeywordifalltestspassed": 0,
    "runkeywordifanytestsfailed": 0,
    "waituntilkeywordsucceeds": 2,
    "repeatkeyword": 1,
    "promiseto": 0,
}

FENCE_OPEN = re.compile(r"^(?P<indent>[ \t]*)```\s*(?:robotframework|robot)\s*$", re.I)
FENCE_CLOSE = re.compile(r"^[ \t]*```\s*$")
SECTION = re.compile(r"^\*{3}\s*(.*?)\s*\*{3}")
ASSIGN = re.compile(r"^[$@&%]\{[^}]*\}(\[[^\]]*\])*\s*=?$")
CELL_SPLIT = re.compile(r"\s{2,}|\t|\s\|\s")


def normalize(name: str) -> str:
    return re.sub(r"[\s_]+", "", name).lower()


def is_variable(cell: str) -> bool:
    return bool(re.match(r"^[$@&%]\{", cell))


def looks_like_keyword(name: str) -> bool:
    return bool(re.match(r"^[A-Za-z]", name)) and not re.search(r"[/<>\"'()]|\.\.\.|…", name)


@dataclass
class Call:
    file: str
    line: int
    keyword: str
    args: list[str]


@dataclass
class Finding:
    skill: str
    file: str
    line: int
    kind: str
    keyword: str
    detail: str = ""

    def format(self) -> str:
        text = f"{self.skill} {self.file}:{self.line} {self.kind} {self.keyword}"
        return f"{text} ~ {self.detail}" if self.detail else text


@dataclass
class SkillData:
    calls: list[Call] = field(default_factory=list)
    defined: set[str] = field(default_factory=set)
    embedded: list[EmbeddedArguments] = field(default_factory=list)

    def define(self, name: str) -> None:
        emb = EmbeddedArguments.from_name(name)
        if emb:
            self.embedded.append(emb)
        else:
            self.defined.add(normalize(name))

    def is_defined(self, name: str) -> bool:
        return normalize(name) in self.defined or any(e.name.fullmatch(name) for e in self.embedded)


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------


def split_cells(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("| "):
        s = s.strip("|").strip()
    cells = []
    for cell in CELL_SPLIT.split(s):
        cell = cell.strip()
        if not cell:
            continue
        if cell.startswith("#"):
            break
        cells.append(re.sub(r"\s+#.*$", "", cell))
    return cells


def calls_from_cells(cells: list[str]) -> list[tuple[str, list[str]]]:
    """Return (keyword, args) pairs found in one body row (after assignments)."""
    i = 0
    while i < len(cells) and ASSIGN.match(cells[i]):
        i += 1
    cells = cells[i:]
    if not cells:
        return []
    head = cells[0].upper()
    if head == "IF" and len(cells) > 2:
        # Inline IF: IF cond Kw args [ELSE IF cond Kw args] [ELSE Kw args]
        out: list[tuple[str, list[str]]] = []
        idx, expect_cond = 1, True
        while idx < len(cells):
            if expect_cond:
                idx += 1
                expect_cond = False
                continue
            end = idx
            while end < len(cells) and cells[end].upper() not in ("ELSE", "ELSE IF"):
                end += 1
            seg = cells[idx:end]
            j = 0
            while j < len(seg) and ASSIGN.match(seg[j]):
                j += 1
            seg = seg[j:]
            if seg and seg[0].upper() not in CONTROL:
                out.append((seg[0], seg[1:]))
            if end < len(cells):
                expect_cond = cells[end].upper() == "ELSE IF"
            idx = end + 1
        return out
    if head in CONTROL:
        return []
    return [(cells[0], cells[1:])]


def extract_lines(lines: list[str], start_line: int, rel: str, data: SkillData) -> None:
    """Line-based extractor for a (dedented) fenced block."""
    has_sections = any(SECTION.match(ln) for ln in lines)
    section = None if not has_sections else "unknown"
    suite_template = False
    in_template_test = False
    for idx, raw in enumerate(lines):
        lineno = start_line + idx
        m = SECTION.match(raw)
        if m:
            section = m.group(1).lower().rstrip("s")  # "test case", "keyword", "task", ...
            in_template_test = False
            continue
        s = raw.strip()
        if not s or s.startswith("#") or s.startswith("..."):
            continue
        indented = raw[:1].isspace()
        if section in ("variable", "comment"):
            continue
        cells = split_cells(raw)
        # Join "..." continuation rows into this logical row.
        for nxt_line in lines[idx + 1:]:
            if not nxt_line.strip().startswith("..."):
                break
            cells += split_cells(nxt_line)[1:]
        if not cells:
            continue
        first = cells[0].lower()
        # Settings (either in a Settings section or bare lines in fragments).
        if section == "setting" or (not indented and first in SETUP_SETTINGS | OTHER_SETTINGS):
            if first in ("test template", "task template") and len(cells) > 1:
                suite_template = cells[1].upper() != "NONE"
            if first in SETUP_SETTINGS and len(cells) > 1 and cells[1].upper() != "NONE":
                data.calls.append(Call(rel, lineno, cells[1], cells[2:]))
            continue
        if not indented:
            if section in ("test case", "task", "keyword"):
                in_template_test = False
                if section == "keyword":
                    data.define(s)
                continue
            if section is None:
                # Header-less fragment: a single-cell line followed by an
                # indented line is a test/keyword name, not a call.
                nxt = next((ln for ln in lines[idx + 1:] if ln.strip() and not ln.strip().startswith("#")), "")
                if len(cells) == 1 and nxt[:1].isspace() and cells[0].upper() not in CONTROL:
                    in_template_test = False
                    continue
        if cells[0].startswith("["):
            setting = cells[0].lower()
            if setting in ("[setup]", "[teardown]", "[template]") and len(cells) > 1:
                if cells[1].upper() == "NONE":
                    continue
                data.calls.append(Call(rel, lineno, cells[1], cells[2:]))
                if setting == "[template]":
                    in_template_test = True
            continue
        if (suite_template and section in ("test case", "task")) or in_template_test:
            continue
        for kw, args in calls_from_cells(cells):
            data.calls.append(Call(rel, lineno, kw, args))


def extract_markdown(path: Path, rel: str, data: SkillData) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        if FENCE_OPEN.match(lines[i]):
            start = i + 1
            j = start
            while j < len(lines) and not FENCE_CLOSE.match(lines[j]):
                j += 1
            block = textwrap.dedent("\n".join(lines[start:j])).splitlines()
            extract_lines(block, start + 1, rel, data)
            i = j + 1
        else:
            i += 1


class _RobotVisitor(ModelVisitor):
    def __init__(self, rel: str, data: SkillData) -> None:
        self.rel = rel
        self.data = data
        self.suite_template = False
        self.skip_body = False

    def add(self, node, name, args) -> None:
        if name and name.upper() != "NONE":
            self.data.calls.append(Call(self.rel, node.lineno, name, list(args)))

    def visit_File(self, node) -> None:  # noqa: N802
        for section in node.sections:
            for item in getattr(section, "body", []):
                if type(item).__name__ == "TestTemplate" and item.value and item.value.upper() != "NONE":
                    self.suite_template = True
        self.generic_visit(node)

    def visit_Keyword(self, node) -> None:  # noqa: N802
        self.data.define(node.name)
        self.skip_body = False
        self.generic_visit(node)

    def visit_TestCase(self, node) -> None:  # noqa: N802
        has_template = any(type(item).__name__ == "Template" for item in node.body)
        self.skip_body = self.suite_template or has_template
        self.generic_visit(node)
        self.skip_body = False

    def visit_KeywordCall(self, node) -> None:  # noqa: N802
        if not self.skip_body:
            self.add(node, node.keyword, node.args)

    def visit_Setup(self, node) -> None:  # noqa: N802
        self.add(node, node.name, node.args)

    visit_Teardown = visit_Setup  # noqa: N815
    visit_SuiteSetup = visit_Setup  # noqa: N815
    visit_SuiteTeardown = visit_Setup  # noqa: N815
    visit_TestSetup = visit_Setup  # noqa: N815
    visit_TestTeardown = visit_Setup  # noqa: N815

    def visit_TestTemplate(self, node) -> None:  # noqa: N802
        self.add(node, node.value, [])

    def visit_Template(self, node) -> None:  # noqa: N802
        self.add(node, node.value, [])


def extract_robot(path: Path, rel: str, data: SkillData) -> None:
    model = get_model(str(path))
    _RobotVisitor(rel, data).visit(model)


def collect_skill(skill_dir: Path) -> tuple[SkillData, int]:
    data = SkillData()
    files = sorted(
        p for p in skill_dir.rglob("*")
        if p.is_file() and p.suffix in (".md", ".robot", ".resource")
    )
    for path in files:
        rel = path.relative_to(skill_dir).as_posix()
        if path.suffix == ".md":
            extract_markdown(path, rel, data)
        else:
            extract_robot(path, rel, data)
    return data, len(files)


# --------------------------------------------------------------------------
# Resolution
# --------------------------------------------------------------------------


@dataclass
class LibraryInfo:
    keywords: dict[str, object]  # normalized name -> libdoc KeywordDoc
    condition_inputs: dict[str, str] | None = None  # normalized -> display name


@functools.lru_cache(maxsize=None)
def load_library(name: str) -> LibraryInfo | None:
    with warnings.catch_warnings(), contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        warnings.simplefilter("ignore")
        try:
            doc = LibraryDocumentation(name)
        except Exception:
            return None
    info = LibraryInfo({normalize(k.name): k for k in doc.keywords})
    for td in getattr(doc, "type_docs", []):
        if td.name == "ConditionInputs":
            info.condition_inputs = {
                normalize(m.name): m.name.replace("_", " ").title() for m in td.members
            }
    return info


def strip_prefix(name: str) -> str:
    if "." in name:
        prefix, _, rest = name.rpartition(".")
        if prefix.lower() in LIBRARY_PREFIXES and rest:
            return rest
    return name


def check_skill(skill: str, lib: LibraryInfo, std: dict[str, object], data: SkillData) -> list[Finding]:
    names = sorted({k.name for k in lib.keywords.values()} | {k.name for k in std.values()})
    by_norm = {normalize(n): n for n in names}
    findings: list[Finding] = []

    cache: dict[str, str] = {}

    def suggest(name: str) -> str:
        key = normalize(name)
        if key not in cache:
            close = difflib.get_close_matches(key, list(by_norm), n=3, cutoff=0.6)
            cache[key] = ", ".join(by_norm[c] for c in close)
        return cache[key]

    def resolve(call: Call, name: str, args: list[str]) -> None:
        if is_variable(name) or not name:
            return
        bare = strip_prefix(name)
        norm = normalize(bare)
        kw = lib.keywords.get(norm)
        from_lib = kw is not None
        if kw is None:
            kw = std.get(norm)
        if kw is not None:
            if norm in LEGACY:
                findings.append(Finding(skill, call.file, call.line, "LEGACY", name,
                                        "use native IF / ELSE"))
            elif kw.deprecated:
                findings.append(Finding(skill, call.file, call.line, "DEPRECATED", name,
                                        kw.short_doc.replace("\n", " ")))
            if from_lib and norm == "waitforcondition" and lib.condition_inputs and args:
                cond = args[0]
                if cond.lower().startswith("condition="):
                    cond = cond.split("=", 1)[1]
                if not is_variable(cond) and normalize(cond) not in lib.condition_inputs:
                    findings.append(Finding(
                        skill, call.file, call.line, "BAD-ARG", f"{name}    {args[0]}",
                        "condition must be one of: " + ", ".join(sorted(lib.condition_inputs.values()))))
            wrap = WRAPPERS.get(norm)
            if wrap is not None:
                resolve_wrapped(call, norm, args, wrap)
            return
        if data.is_defined(bare) or data.is_defined(name):
            return
        if looks_like_keyword(bare):
            findings.append(Finding(skill, call.file, call.line, "UNKNOWN", name, suggest(bare)))

    def resolve_wrapped(call: Call, norm: str, args: list[str], index: int) -> None:
        if len(args) <= index:
            return
        rest = args[index:]
        if norm == "runkeywords":
            return
        resolve(call, rest[0], rest[1:])

    for call in data.calls:
        norm = normalize(strip_prefix(call.keyword))
        if norm == "runkeywords" and (lib.keywords.get(norm) or std.get(norm)):
            args = call.args
            if any(a == "AND" for a in args):
                groups, cur = [], []
                for a in args:
                    if a == "AND":
                        groups.append(cur)
                        cur = []
                    else:
                        cur.append(a)
                groups.append(cur)
                for g in groups:
                    if g:
                        resolve(call, g[0], g[1:])
            else:
                for a in args:
                    resolve(call, a, [])
            continue
        resolve(call, call.keyword, call.args)
    return findings


# --------------------------------------------------------------------------
# Allowlist
# --------------------------------------------------------------------------


@dataclass
class AllowEntry:
    skill: str
    file: str
    keyword: str
    reason: str
    used: bool = False

    def matches(self, f: Finding) -> bool:
        return (
            self.skill == f.skill
            and self.file == f.file
            and normalize(self.keyword) == normalize(f.keyword)
        )


def load_allowlist(path: Path | None) -> list[AllowEntry]:
    if path is None or not path.exists():
        return []
    if tomllib is None:
        print("ERROR: reading the allowlist needs Python 3.11+ (tomllib)", file=sys.stderr)
        sys.exit(2)
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    entries = []
    for i, item in enumerate(raw.get("allow", [])):
        missing = [k for k in ("skill", "file", "keyword", "reason") if not str(item.get(k, "")).strip()]
        if missing:
            print(f"ERROR: allowlist entry #{i + 1} is missing {', '.join(missing)}", file=sys.stderr)
            sys.exit(2)
        entries.append(AllowEntry(skill_key(item["skill"]), item["file"], item["keyword"], item["reason"]))
    return entries


def skill_key(dir_name: str) -> str:
    """``rf-browser`` -> ``browser`` (skill dirs are named by their rf-<topic> id)."""
    return dir_name.removeprefix("rf-")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify that library skills only use existing, non-deprecated keywords.")
    parser.add_argument("--skills-root", default=str(REPO_ROOT / "skills"),
                        help="directory containing the skill dirs (default: <repo>/skills)")
    parser.add_argument("--allowlist", default=str(DEFAULT_ALLOWLIST),
                        help="TOML allowlist ([[allow]] skill/file/keyword/reason); '' disables it")
    parser.add_argument("--require-all", action="store_true",
                        help="fail when a skill is skipped because its library is not installed")
    args = parser.parse_args(argv)

    root = Path(args.skills_root)
    if not root.is_dir():
        print(f"ERROR: skills root not found: {root}", file=sys.stderr)
        return 2
    allow = load_allowlist(Path(args.allowlist) if args.allowlist else None)

    std: dict[str, object] = {}
    for name in STANDARD_LIBRARIES:
        info = load_library(name)
        if info:
            std.update(info.keywords)

    failed = False
    summaries: list[str] = []
    checked_skills: set[str] = set()
    for skill_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        key = skill_key(skill_dir.name)
        if key not in SKILL_LIBRARIES:
            continue
        lib = load_library(SKILL_LIBRARIES[key])
        if lib is None:
            summaries.append(f"{key}: skipped (library not installed: {SKILL_LIBRARIES[key]})")
            failed = failed or args.require_all
            continue
        checked_skills.add(key)
        data, nfiles = collect_skill(skill_dir)
        findings = check_skill(key, lib, std, data)
        reported = 0
        for f in sorted(findings, key=lambda f: (f.file, f.line, f.kind, f.keyword)):
            entry = next((e for e in allow if e.matches(f)), None)
            if entry:
                entry.used = True
                continue
            print(f.format())
            reported += 1
        failed = failed or reported > 0
        summaries.append(f"{key}: checked {nfiles} files, {reported} findings")

    for entry in allow:
        if not entry.used and (entry.skill in checked_skills or entry.skill not in SKILL_LIBRARIES):
            print(f"STALE allowlist entry: skill={entry.skill} file={entry.file} "
                  f"keyword={entry.keyword!r} matches no call")
            failed = True

    print("--")
    for line in summaries:
        print(line)
    print("RESULT: FAIL" if failed else "RESULT: OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
