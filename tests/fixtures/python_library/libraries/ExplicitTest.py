"""Explicit scope="TEST" with state changed in a keyword: still warned (heuristic)."""
from robot.api.deco import keyword, library


@library(scope="TEST")
class ExplicitTest:
    """Per-test scratch values."""

    def __init__(self):
        self.values = []

    @keyword
    def remember(self, value: str) -> None:
        """Remember a value for this test."""
        self.values.append(value)
        self.last = value
