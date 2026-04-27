"""JSON report writer."""

from __future__ import annotations

import json
from pathlib import Path

from ..domain.scorecard import Scorecard


class JsonReportWriter:
    """Satisfies the :class:`ReportWriter` port with plain JSON output."""

    def write(self, scorecards: list[Scorecard], output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "scorecards": [
                {
                    **sc.model_dump(mode="json"),
                    "pass_rate": sc.pass_rate,
                    "total_score": sc.total_score,
                    "all_passed": sc.all_passed,
                }
                for sc in scorecards
            ],
            "summary": {
                "count": len(scorecards),
                "all_passed": all(sc.all_passed for sc in scorecards),
            },
        }
        output_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return output_path
