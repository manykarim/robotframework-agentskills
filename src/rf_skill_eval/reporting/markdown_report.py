"""Markdown report writer — GitHub-friendly summary via Jinja2."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from ..domain.scorecard import Scorecard


class MarkdownReportWriter:
    """Satisfies the :class:`ReportWriter` port with Markdown output."""

    def __init__(self) -> None:
        templates_dir = Path(__file__).parent / "templates"
        self._env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(enabled_extensions=("html",)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def write(self, scorecards: list[Scorecard], output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        template = self._env.get_template("summary.md.j2")
        body = template.render(
            scorecards=scorecards,
            total=len(scorecards),
            all_passed=all(sc.all_passed for sc in scorecards),
        )
        output_path.write_text(body, encoding="utf-8")
        return output_path
