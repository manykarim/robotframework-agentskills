"""Class library without scope that counts in a keyword (state_in_test_scope)."""


class StateLib:
    """Counter."""

    def __init__(self):
        self.count = 0

    def increment(self) -> int:
        """Add one."""
        self.count += 1
        return self.count
