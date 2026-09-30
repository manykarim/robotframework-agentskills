"""Output during init: print and logger.warn (output_during_import)."""
from robot.api import logger


class PrintInit:
    """Noisy init."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self, host: str = "localhost"):
        print(f"connecting to {host}")
        logger.warn("init warn from PrintInit")

    def ping(self) -> str:
        """Ping."""
        return "pong"
