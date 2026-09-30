"""Union with str (union_with_str), untyped and optional-str arguments."""
from typing import Literal, Optional


class UnionLib:
    """Unions."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def union_keyword(self, value: int | str) -> None:
        """Union with str."""

    def optional_text(self, text: Optional[str] = None) -> None:
        """Optional str is fine."""

    def mode_keyword(self, mode: Literal["ON", "OFF"], n=3) -> None:
        """Literal is fine."""

    def untyped(self, x) -> None:
        """Untyped argument."""
