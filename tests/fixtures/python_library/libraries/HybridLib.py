"""Hybrid API library (get_keyword_names without run_keyword)."""


class HybridLib:
    """Hybrid."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def get_keyword_names(self):
        return ["hello"]

    def hello(self, name: str) -> str:
        """Greet."""
        return f"Hello, {name}"
