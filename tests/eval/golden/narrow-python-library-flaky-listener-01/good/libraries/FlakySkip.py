"""Reference solution: listener API v3."""


class FlakySkip:
    """Report failures of tests tagged ``flaky`` as skipped."""

    ROBOT_LISTENER_API_VERSION = 3

    def end_test(self, data, result):
        if result.failed and "flaky" in result.tags:
            result.message = f"Flaky failure skipped: {result.message}"
            result.status = "SKIP"
