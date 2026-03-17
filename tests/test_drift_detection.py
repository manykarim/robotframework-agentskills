"""Verify root skill scripts stay in sync with plugin copies."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCRIPT_PAIRS = [
    (
        "skills/robotframework-keyword-builder/scripts/keyword_builder.py",
        "plugins/rf-agentskills/scripts/keyword_builder.py",
    ),
    (
        "skills/robotframework-testcase-builder/scripts/testcase_builder.py",
        "plugins/rf-agentskills/scripts/testcase_builder.py",
    ),
    (
        "skills/robotframework-resource-architect/scripts/resource_architect.py",
        "plugins/rf-agentskills/scripts/resource_architect.py",
    ),
    (
        "skills/robotframework-libdoc-search/scripts/rf_libdoc.py",
        "plugins/rf-agentskills/scripts/rf_libdoc.py",
    ),
    (
        "skills/robotframework-results/scripts/rf_results.py",
        "plugins/rf-agentskills/scripts/rf_results.py",
    ),
]


def test_root_and_plugin_scripts_in_sync():
    """Root skill scripts must be identical to plugin copies."""
    for root_rel, plugin_rel in SCRIPT_PAIRS:
        root_path = ROOT / root_rel
        plugin_path = ROOT / plugin_rel
        assert root_path.exists(), f"Missing root script: {root_rel}"
        assert plugin_path.exists(), f"Missing plugin script: {plugin_rel}"
        root_content = root_path.read_text()
        plugin_content = plugin_path.read_text()
        assert root_content == plugin_content, (
            f"DRIFT DETECTED: {root_rel} differs from {plugin_rel}. "
            f"Run: diff {root_rel} {plugin_rel}"
        )
