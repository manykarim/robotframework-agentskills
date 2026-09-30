"""__init__ hangs (timeout)."""
import time


class SleepInit:
    """Slow."""

    def __init__(self):
        time.sleep(5)

    def kw(self) -> None:
        """Doc."""
