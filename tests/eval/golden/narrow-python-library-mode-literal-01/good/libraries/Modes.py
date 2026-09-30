"""Reference solution: Literal restricts the values and matches case-insensitively."""

from typing import Literal

from robot.api.deco import keyword, library


@library(scope="GLOBAL")
class Modes:
    """Mode switching."""

    @keyword
    def set_mode(self, mode: Literal["ON", "OFF"]) -> str:
        """Set the mode: ``ON`` or ``OFF`` in any case."""
        return mode
