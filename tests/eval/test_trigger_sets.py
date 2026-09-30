"""Trigger-set schema and the committed query sets (tasks 5.1, 5.5, 5.6)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from rf_skill_eval.application.catalog import load_trigger_set, load_trigger_sets, shipped_skills

_REPO = Path(__file__).resolve().parents[2]
_TRIGGERS = _REPO / "eval" / "triggers"
_SKILLS = shipped_skills(_REPO)


def _queries(pos: int, neg: int, *, splits: tuple[str, str] = ("train", "validation")) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for i in range(pos):
        out.append({"id": f"p{i}", "query": f"q{i}", "should_trigger": True, "split": splits[i % 2]})
    for i in range(neg):
        out.append({"id": f"n{i}", "query": f"n{i}", "should_trigger": False, "split": splits[i % 2]})
    return out


def _write(tmp_path: Path, skill: str = "rf-browser", **data: object) -> Path:
    payload: dict[str, object] = {"skill": skill, "queries": _queries(8, 8)}
    payload.update(data)
    path = tmp_path / f"{skill}.yaml"
    path.write_text(yaml.safe_dump(payload))
    return path


def test_minimal_valid_set_loads(tmp_path: Path) -> None:
    tset = load_trigger_set(_write(tmp_path), skills=_SKILLS)
    assert tset.runs == 3 and tset.threshold == 0.5
    assert tset.model == "claude-haiku-4-5-20251001"


@pytest.mark.parametrize(("pos", "neg"), [(7, 8), (8, 7)])
def test_too_few_queries_rejected(tmp_path: Path, pos: int, neg: int) -> None:
    with pytest.raises(ValueError, match=r"rf-browser\.yaml.*minimum 8"):
        load_trigger_set(_write(tmp_path, queries=_queries(pos, neg)), skills=_SKILLS)


def test_query_without_split_rejected(tmp_path: Path) -> None:
    queries = _queries(8, 8)
    del queries[0]["split"]
    with pytest.raises(ValueError, match="split"):
        load_trigger_set(_write(tmp_path, queries=queries), skills=_SKILLS)


def test_polarity_missing_from_a_split_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="validation split"):
        load_trigger_set(
            _write(tmp_path, queries=_queries(8, 8, splits=("train", "train"))), skills=_SKILLS
        )


def test_unknown_skill_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown skill 'rf-keyword-builder'"):
        load_trigger_set(_write(tmp_path, skill="rf-keyword-builder"), skills=_SKILLS)


def test_opus_and_old_models_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="--allow-opus"):
        load_trigger_set(_write(tmp_path, model="claude-opus-5-5"), skills=_SKILLS)
    with pytest.raises(ValueError, match="retired id"):
        load_trigger_set(_write(tmp_path, model="claude-haiku-4-5"), skills=_SKILLS)


def test_every_shipped_skill_has_exactly_one_valid_set() -> None:
    sets, problems = load_trigger_sets(_TRIGGERS, skills=_SKILLS)
    assert not problems, problems
    assert set(sets) == set(_SKILLS)


@pytest.mark.parametrize("skill", sorted(_SKILLS))
def test_committed_set_shape(skill: str) -> None:
    tset = load_trigger_set(_TRIGGERS / f"{skill}.yaml", skills=_SKILLS)
    for polarity in (True, False):
        # holdout queries are optional and never counted (tune-skill-descriptions)
        items = [q for q in tset.queries if q.should_trigger is polarity and q.split != "holdout"]
        assert len(items) >= 8
        train = sum(1 for q in items if q.split == "train")
        # roughly 60/40, stratified by polarity
        assert 0.5 <= train / len(items) <= 0.7, (skill, polarity, train, len(items))
    negatives = [q for q in tset.queries if not q.should_trigger]
    siblings = [q for q in negatives if q.note.startswith("sibling")]
    non_rf = [q for q in negatives if q.note.startswith("non-RF")]
    assert len(siblings) >= 3, skill
    assert len(non_rf) >= 2, skill
    positives = [q for q in tset.queries if q.should_trigger]
    assert sum(1 for q in positives if q.note.startswith("indirect")) >= 2, skill
    assert any(q.note == "edit existing file" for q in positives), skill


def test_browser_set_has_selenium_and_pytest_playwright_near_misses() -> None:
    tset = load_trigger_set(_TRIGGERS / "rf-browser.yaml", skills=_SKILLS)
    negatives = [q for q in tset.queries if not q.should_trigger]
    assert any("SeleniumLibrary" in q.query for q in negatives)
    assert any("pytest-playwright" in q.query for q in negatives)


@pytest.mark.parametrize(
    ("skill", "sibling"),
    [
        ("rf-browser", "rf-selenium"),
        ("rf-selenium", "rf-browser"),
        ("rf-requests", "rf-restinstance"),
        ("rf-restinstance", "rf-requests"),
        ("rf-results", "rf-robotcode"),
        ("rf-libdoc", "rf-robotcode"),
        ("rf-setup", "rf-browser"),
    ],
)
def test_sibling_near_misses_present(skill: str, sibling: str) -> None:
    tset = load_trigger_set(_TRIGGERS / f"{skill}.yaml", skills=_SKILLS)
    assert any(q.note == f"sibling {sibling}" for q in tset.queries if not q.should_trigger)


def test_no_query_is_both_a_positive_and_a_sibling_negative_for_its_own_set() -> None:
    sets, _ = load_trigger_sets(_TRIGGERS, skills=_SKILLS)
    for tset in sets.values():
        pos = {q.query for q in tset.queries if q.should_trigger}
        neg = {q.query for q in tset.queries if not q.should_trigger}
        assert not pos & neg, tset.skill


def test_readme_documents_discipline_and_is_linked() -> None:
    readme = (_TRIGGERS / "README.md").read_text()
    assert "Never edit validation queries" in readme
    assert "train" in readme and "validation" in readme
    assert "eval/triggers/README.md" in (_REPO / "eval" / "tasks" / "README.md").read_text()
