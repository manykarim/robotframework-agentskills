"""Test doubles: a fake SkillRunner that never calls a model."""

from __future__ import annotations

import itertools
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from rf_skill_eval.domain.profile import Profile
from rf_skill_eval.domain.run import Run
from rf_skill_eval.domain.task import Task
from rf_skill_eval.infrastructure.telemetry.session_parser import parse_result_usage

_counter = itertools.count()


def result_line(*, cost: float = 0.01, input_tokens: int = 100, output_tokens: int = 50,
                turns: int = 2, duration_ms: int = 1000) -> dict[str, object]:
    return {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "duration_ms": duration_ms,
        "num_turns": turns,
        "total_cost_usd": cost,
        "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens},
    }


def skill_call(skill: str, tool_id: str = "toolu_x") -> list[dict[str, object]]:
    return [
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": tool_id, "name": "Skill", "input": {"skill": skill}}]}},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": tool_id, "content": f"Launching skill: {skill}"}]}},
    ]


@dataclass
class FakeRunner:
    """Writes files/transcripts decided by ``behaviour(task, profile, replicate)``.

    ``behaviour`` returns ``(files, events, cost)``: files to create in the
    workspace, extra transcript events, and the reported cost.
    """

    behaviour: Callable[[Task, Profile, int], tuple[dict[str, str], list[dict[str, object]], float]] = (
        lambda _t, _p, _r: ({}, [], 0.01)
    )
    calls: list[tuple[str, str, int, Path]] = field(default_factory=list)

    def execute(self, task: Task, profile: Profile, output_dir: Path, *, replicate: int = 0) -> Run:
        run_id = f"{task.id}-{profile.name}-{next(_counter):04d}"
        artifacts = output_dir / run_id
        workspace = artifacts / "workspace"
        workspace.mkdir(parents=True)
        files, events, cost = self.behaviour(task, profile, replicate)
        for rel, content in files.items():
            target = workspace / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        transcript = artifacts / "stdout.stream.jsonl"
        lines = [*events, result_line(cost=cost)]
        transcript.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
        self.calls.append((task.id, profile.arm, replicate, workspace))
        now = datetime.now(UTC)
        return Run(
            id=run_id,
            task_id=task.id,
            profile_name=profile.name,
            started_at=now,
            finished_at=now,
            exit_code=0,
            artifacts_dir=artifacts,
            workspace_dir=workspace,
            model=task.model,
            arm=profile.arm,
            replicate=replicate,
            usage=parse_result_usage(transcript),
        )
