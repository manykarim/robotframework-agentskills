"""Records which city and team were selected last.

State is kept at module level, so every import of this library (by path or by
name) sees the same selection.
"""

from robot.api.deco import keyword, library

_LAST: dict[str, str] = {}


@library(scope="GLOBAL")
class Selections:
    @keyword
    def record_selection(self, city: str, team: str) -> None:
        """Stores ``city`` and ``team`` as the current selection."""
        _LAST.clear()
        _LAST.update(city=city, team=team)

    @keyword
    def last_selection_should_be(self, city: str, team: str) -> None:
        """Fails unless the last recorded selection was ``city`` / ``team``."""
        got = (_LAST.get("city"), _LAST.get("team"))
        if got != (city, team):
            raise AssertionError(f"Last selection was city={got[0]!r} team={got[1]!r}, "
                                 f"expected city={city!r} team={team!r}")
