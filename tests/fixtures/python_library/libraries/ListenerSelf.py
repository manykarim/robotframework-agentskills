"""Library as listener: end_test is a listener method, not a keyword (no findings)."""
from robot.api.deco import keyword, library


@library(scope="SUITE", listener="SELF")
class ListenerSelf:
    """Counts finished tests."""

    def __init__(self):
        self.finished = 0

    def end_test(self, data, result):
        self.finished += 1

    @keyword
    def finished_tests(self) -> int:
        """Number of finished tests."""
        return self.finished
