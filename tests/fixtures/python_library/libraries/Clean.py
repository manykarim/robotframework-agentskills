"""A clean library: no findings at all."""
from enum import Enum

from robot.api import logger
from robot.api.deco import keyword, library


class Mode(Enum):
    ON = "ON"
    OFF = "OFF"


@library(scope="GLOBAL", version="1.0")
class Clean:
    """Stateless helpers."""

    @keyword
    def set_mode(self, mode: Mode) -> str:
        """Return the mode name."""
        logger.info(f"mode {mode.name}")
        return mode.name
