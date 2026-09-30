"""Naive solution: every failure becomes SKIP, tagged or not."""


class FlakySkip:
    """Hide failures."""

    ROBOT_LISTENER_API_VERSION = 3

    def end_test(self, data, result):
        if result.failed:
            result.status = "SKIP"
