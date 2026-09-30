"""Skill-load detection and usage parsing from recorded transcripts (tasks 2.4, 5.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from rf_skill_eval.infrastructure.telemetry.session_parser import parse_result_usage
from rf_skill_eval.infrastructure.telemetry.skill_loads import (
    detect_skill_loads_in_file,
    read_skill_name,
    skill_dir_map,
)

_T = Path(__file__).parent / "fixtures" / "transcripts"
_REPO = Path(__file__).resolve().parents[2]
_NAMES = {"rf-browser": "rf-browser", "rf-setup": "rf-setup", "rf-selenium": "rf-selenium"}


def test_skill_tool_with_plugin_prefix_counts_as_load() -> None:
    loads = detect_skill_loads_in_file(_T / "skill-tool-load.stream.jsonl", _NAMES)
    assert [(ld.skill, ld.via, ld.successful) for ld in loads] == [
        ("rf-browser", "skill_tool", True),
        ("rf-setup", "skill_tool", True),  # other skill recorded for confusion reports
    ]


def test_read_of_skill_md_counts_as_load() -> None:
    loads = detect_skill_loads_in_file(_T / "read-skill-md-load.stream.jsonl", _NAMES)
    assert [(ld.skill, ld.via) for ld in loads] == [("rf-browser", "read")]


def test_read_uses_frontmatter_name_to_dir_map() -> None:
    # Directory renamed but name unchanged: detection follows the map.
    loads = detect_skill_loads_in_file(
        _T / "read-skill-md-load.stream.jsonl", {"web-ui": "rf-browser"}
    )
    assert [ld.skill for ld in loads] == ["web-ui"]


def test_no_load_negative_case() -> None:
    assert detect_skill_loads_in_file(_T / "no-load.stream.jsonl", _NAMES) == []


def test_failed_skill_call_is_a_load_but_not_successful() -> None:
    loads = detect_skill_loads_in_file(_T / "failed-skill-load.stream.jsonl", _NAMES)
    assert [(ld.skill, ld.successful) for ld in loads] == [("rf-browser", False)]


def test_unknown_skills_are_ignored() -> None:
    assert detect_skill_loads_in_file(_T / "skill-tool-load.stream.jsonl", {"rf-x": "rf-x"}) == []


def test_skill_dir_map_reads_real_repo_frontmatter() -> None:
    mapping = skill_dir_map(_REPO / "skills")
    assert mapping["rf-browser"] == "rf-browser"
    assert len(mapping) >= 10
    assert read_skill_name(_REPO / "skills" / "rf-libdoc" / "SKILL.md") == "rf-libdoc"


def test_usage_parsed_from_result_line() -> None:
    usage = parse_result_usage(_T / "skill-tool-load.stream.jsonl")
    assert usage is not None
    assert usage.input_tokens == 12
    assert usage.cache_creation_input_tokens == 3000
    assert usage.cache_read_input_tokens == 15000
    assert usage.total_input_tokens == 18012
    assert usage.output_tokens == 420
    assert usage.num_turns == 3
    assert usage.duration_ms == 8123
    assert usage.total_cost_usd == pytest.approx(0.0123)
    assert usage.is_error is False


def test_usage_missing_without_result_line(tmp_path: Path) -> None:
    assert parse_result_usage(_T / "timeout-no-result.stream.jsonl") is None
    assert parse_result_usage(tmp_path / "missing.jsonl") is None
