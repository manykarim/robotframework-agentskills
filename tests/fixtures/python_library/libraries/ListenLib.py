"""Listener methods exposed as keywords (listener_method_exposed)."""


class ListenLib:
    """Listener without @library."""

    ROBOT_LISTENER_API_VERSION = 3
    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self):
        self.ROBOT_LIBRARY_LISTENER = self

    def end_test(self, data, result):
        pass

    def my_keyword(self) -> None:
        """Doc."""
