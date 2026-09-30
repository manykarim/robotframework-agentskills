"""scripts/validate-skills.py: agentskills.io frontmatter rules (skill-metadata-conformance spec)."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from _shell import BASH

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "validate-skills.py"

_spec = importlib.util.spec_from_file_location("validate_skills", SCRIPT)
vs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vs)

VERSION = "9.8.7"
VALID = {
    "name": "rf-demo",
    "description": "Demo skill. Use when testing the validator.",
    "license": "Apache-2.0",
    "compatibility": "Requires Python 3.10+ and robotframework>=7.",
    "metadata": {"author": "manykarim", "version": f'"{VERSION}"'},
}

# Both parsers must agree: PyYAML (when installed) and the stdlib fallback.
PARSERS = [pytest.param(True, id="yaml"), pytest.param(False, id="minimal")]


def render(fields: dict) -> str:
    out = ["---"]
    for key, value in fields.items():
        if isinstance(value, dict):
            out.append(f"{key}:")
            out.extend(f"  {k}: {v}" for k, v in value.items())
        else:
            out.append(f"{key}: {value}")
    out += ["---", "", "# Body", ""]
    return "\n".join(out)


def make_repo(tmp_path: Path, skills: dict[str, str], version: str = VERSION) -> Path:
    (tmp_path / "VERSION").write_text(version + "\n", encoding="utf-8")
    for dir_name, text in skills.items():
        d = tmp_path / "skills" / dir_name
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(text, encoding="utf-8")
    return tmp_path


def rules(tmp_path: Path, dir_name: str, text: str, use_yaml: bool) -> set[str]:
    repo = make_repo(tmp_path, {dir_name: text})
    lines = vs.validate(repo, ["root"], use_yaml=use_yaml)
    return {line.split(": ")[1] for line in lines}


@pytest.mark.parametrize("use_yaml", PARSERS)
def test_valid_skill_passes(tmp_path, use_yaml):
    assert rules(tmp_path, "rf-demo", render(VALID), use_yaml) == set()


@pytest.mark.parametrize("use_yaml", PARSERS)
def test_folded_and_quoted_description_pass(tmp_path, use_yaml):
    text = render({**VALID, "description": ">-\n  Folded demo\n  description."})
    assert rules(tmp_path, "rf-demo", text, use_yaml) == set()
    repo = tmp_path / "q"
    repo.mkdir()
    text = render({**VALID, "description": '"Quoted: demo — description."'})
    assert rules(repo, "rf-demo", text, use_yaml) == set()


@pytest.mark.parametrize("use_yaml", PARSERS)
@pytest.mark.parametrize(
    ("dir_name", "override", "rule"),
    [
        pytest.param("rf-Demo", {"name": "rf-Demo"}, "name-charset", id="uppercase"),
        pytest.param("rf_demo", {"name": "rf_demo"}, "name-charset", id="underscore"),
        pytest.param("rf--demo", {"name": "rf--demo"}, "name-charset", id="double-hyphen"),
        pytest.param("rf-demo-", {"name": "rf-demo-"}, "name-charset", id="trailing-hyphen"),
        pytest.param("-rf-demo", {"name": "-rf-demo"}, "name-charset", id="leading-hyphen"),
        pytest.param("rf-" + "a" * 62, {"name": "rf-" + "a" * 62}, "name-length", id="too-long"),
        pytest.param("demo", {"name": "demo"}, "name-prefix", id="no-rf-prefix"),
        pytest.param("rf-demo-copy", {}, "name-dir-mismatch", id="dir-mismatch"),
        pytest.param("rf-demo", {"description": "x" * 1025}, "description-length", id="long-description"),
        pytest.param("rf-demo", {"description": '""'}, "description-missing", id="empty-description"),
        pytest.param("rf-demo", {"compatibility": "y" * 501}, "compatibility-length", id="long-compatibility"),
        pytest.param("rf-demo", {"compatibility": None}, "compatibility-missing", id="no-compatibility"),
        pytest.param("rf-demo", {"description": "Use <b>this</b> skill."}, "xml-tag", id="tag-in-description"),
        pytest.param("rf-demo", {"version": "1.0"}, "unknown-key", id="unknown-key"),
        pytest.param("rf-demo", {"license": None}, "license", id="no-license"),
        pytest.param("rf-demo", {"metadata": {"author": "manykarim", "version": "2.0"}}, "metadata-type",
                     id="non-string-metadata"),
        pytest.param("rf-demo", {"metadata": {"author": "manykarim"}}, "metadata-missing", id="no-metadata-version"),
        pytest.param("rf-demo", {"metadata": {"author": "manykarim", "version": '"0.0.1"'}}, "version-mismatch",
                     id="version-mismatch"),
    ],
)
def test_each_rule_fails(tmp_path, use_yaml, dir_name, override, rule):
    fields = {**VALID, **override}
    fields = {k: v for k, v in fields.items() if v is not None}
    found = rules(tmp_path, dir_name, render(fields), use_yaml)
    assert rule in found, found


def test_missing_frontmatter(tmp_path):
    assert rules(tmp_path, "rf-demo", "# no frontmatter\n", True) == {"frontmatter"}


def test_channel_mismatch_is_reported(tmp_path):
    repo = make_repo(tmp_path, {"rf-demo": render(VALID)})
    plugin = repo / "plugins" / "rf-agentskills" / "skills" / "rf-other"
    plugin.mkdir(parents=True)
    (plugin / "SKILL.md").write_text(render({**VALID, "name": "rf-other"}), encoding="utf-8")
    (repo / "vscode-extension" / "skills").mkdir(parents=True)
    lines = vs.validate(repo, ["root", "plugin", "vscode"])
    assert any("skills/rf-other: channel-mismatch" in line for line in lines), lines
    assert any("plugins/rf-agentskills/skills/rf-demo: channel-mismatch" in line for line in lines), lines


def test_cli_reports_path_and_rule_and_exits_1(tmp_path):
    repo = make_repo(tmp_path, {"rf-foo": render({**VALID, "name": "rf-bar"})})
    res = subprocess.run([sys.executable, str(SCRIPT), "--channel", "root", "--repo-root", str(repo)],
                         capture_output=True, text=True)
    assert res.returncode == 1
    assert "skills/rf-foo/SKILL.md: name-dir-mismatch:" in res.stdout


@pytest.mark.parametrize("use_yaml", PARSERS)
def test_real_tree_all_channels_valid(use_yaml):
    lines = vs.validate(ROOT, ["root", "plugin", "vscode"], use_yaml=use_yaml)
    assert not lines, "\n".join(lines)


@pytest.mark.skipif(BASH is None, reason="bash not available")
def test_bump_version_keeps_skill_metadata_in_step(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(ROOT / "skills", repo / "skills")
    shutil.copy2(ROOT / "VERSION", repo / "VERSION")
    (repo / "scripts").mkdir()
    shutil.copy2(ROOT / "scripts" / "bump-version.sh", repo / "scripts" / "bump-version.sh")
    for rel in (".claude-plugin/marketplace.json", "plugins/rf-agentskills/.claude-plugin/plugin.json",
                "vscode-extension/package.json"):
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, repo / rel)
    res = subprocess.run([BASH, str(repo / "scripts" / "bump-version.sh"), "patch"], capture_output=True,
                         text=True, env={"REPO_ROOT": str(repo), "PATH": "/usr/bin:/bin"})
    assert res.returncode == 0, res.stdout + res.stderr
    new = (repo / "VERSION").read_text().strip()
    assert new != (ROOT / "VERSION").read_text().strip()
    assert vs.validate(repo, ["root"]) == []
    for rel in ("plugins/rf-agentskills/.claude-plugin/plugin.json", "vscode-extension/package.json"):
        assert f'"version": "{new}"' in (repo / rel).read_text()
