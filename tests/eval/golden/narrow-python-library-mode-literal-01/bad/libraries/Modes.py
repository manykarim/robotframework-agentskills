"""Naive solution: a plain str argument accepts any value."""

from robot.api.deco import keyword, library


@library(scope="GLOBAL")
class Modes:
    """Mode switching."""

    @keyword
    def set_mode(self, mode: str) -> str:
        """Set the mode."""
        return mode.upper()
