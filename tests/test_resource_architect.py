"""Tests for the resource architect script."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "robotframework-resource-architect"
    / "scripts"
    / "resource_architect.py"
)


def run_architect(data, extra_args=None):
    """Run the resource architect script and return the CompletedProcess."""
    args = [sys.executable, str(SCRIPT)]
    if extra_args:
        args.extend(extra_args)
    return subprocess.run(
        args,
        input=json.dumps(data),
        capture_output=True,
        text=True,
        timeout=30,
    )


def run_architect_ok(data, extra_args=None):
    """Run the resource architect script and return parsed JSON on success."""
    result = run_architect(data, extra_args)
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    return json.loads(result.stdout)


def test_basic_domain_layout():
    """Simple domains list generates proper resource files."""
    data = {
        "domains": ["login", "checkout"],
        "libraries": ["Browser"],
    }
    output = run_architect_ok(data)
    assert "files" in output
    assert "directories" in output
    file_paths = [f["path"] for f in output["files"]]
    # Should have common.resource plus one per domain
    assert any("common.resource" in p for p in file_paths)
    assert any("login.resource" in p for p in file_paths)
    assert any("checkout.resource" in p for p in file_paths)


def test_environment_variables_resource():
    """Variables format=resource produces .resource files with RF variable syntax."""
    data = {
        "domains": [],
        "environments": ["dev", "prod"],
        "variables_format": "resource",
    }
    output = run_architect_ok(data)
    file_paths = [f["path"] for f in output["files"]]
    assert any("dev.resource" in p for p in file_paths)
    assert any("prod.resource" in p for p in file_paths)
    # Check content uses *** Variables *** format
    env_files = [f for f in output["files"] if "dev.resource" in f["path"]]
    assert len(env_files) == 1
    assert "*** Variables ***" in env_files[0]["content"]


def test_environment_variables_yaml():
    """Variables format=yaml produces .yaml files."""
    data = {
        "domains": [],
        "environments": ["staging"],
        "variables_format": "yaml",
    }
    output = run_architect_ok(data)
    file_paths = [f["path"] for f in output["files"]]
    assert any("staging.yaml" in p for p in file_paths)
    yaml_files = [f for f in output["files"] if "staging.yaml" in f["path"]]
    assert len(yaml_files) == 1
    assert "variables.yaml" in yaml_files[0]["content"] or "URL" in yaml_files[0]["content"]


def test_environment_variables_python():
    """Variables format=python produces .py files with Python variable syntax."""
    data = {
        "domains": [],
        "environments": ["local"],
        "variables_format": "python",
    }
    output = run_architect_ok(data)
    file_paths = [f["path"] for f in output["files"]]
    assert any("local.py" in p for p in file_paths)
    py_files = [f for f in output["files"] if "local.py" in f["path"]]
    assert len(py_files) == 1
    assert "URL = " in py_files[0]["content"]


def test_unknown_variables_format_warns():
    """Unknown variables_format generates a warning and defaults to resource."""
    data = {
        "domains": [],
        "environments": ["test"],
        "variables_format": "toml",
    }
    output = run_architect_ok(data)
    assert any("unknown" in w.lower() and "toml" in w.lower() for w in output["warnings"])
    # Should default to resource format
    file_paths = [f["path"] for f in output["files"]]
    assert any("test.resource" in p for p in file_paths)


def test_by_domain_naming():
    """resource_naming='by-domain' creates per-domain files."""
    data = {
        "domains": ["api", "ui"],
        "resource_naming": "by-domain",
    }
    output = run_architect_ok(data)
    file_paths = [f["path"] for f in output["files"]]
    assert any("api.resource" in p for p in file_paths)
    assert any("ui.resource" in p for p in file_paths)


def test_libraries_in_common_resource():
    """Libraries appear in common.resource content."""
    data = {
        "domains": [],
        "libraries": ["Browser", "Collections", "String"],
    }
    output = run_architect_ok(data)
    common_files = [f for f in output["files"] if "common.resource" in f["path"]]
    assert len(common_files) == 1
    content = common_files[0]["content"]
    assert "Library    Browser" in content
    assert "Library    Collections" in content
    assert "Library    String" in content


def test_empty_domains():
    """Empty domains list still creates common.resource."""
    data = {"domains": []}
    output = run_architect_ok(data)
    file_paths = [f["path"] for f in output["files"]]
    assert any("common.resource" in p for p in file_paths)
    # Only common.resource, no domain files
    assert len(output["files"]) == 1


def test_meta_output():
    """Meta section has resource_dir and resource_naming."""
    data = {
        "domains": ["auth"],
        "resource_naming": "by-domain",
    }
    output = run_architect_ok(data)
    assert "meta" in output
    assert "resource_dir" in output["meta"]
    assert "resource_naming" in output["meta"]
    assert output["meta"]["resource_naming"] == "by-domain"


def test_detect_existing_resource_dir():
    """Detects existing resources/ dir when project_root is provided."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a 'keywords' dir to simulate an existing project
        (Path(tmpdir) / "keywords").mkdir()
        data = {
            "project_root": tmpdir,
            "domains": ["search"],
        }
        output = run_architect_ok(data)
        # Should detect 'keywords' as the resource dir
        assert output["meta"]["resource_dir"] == "keywords"
