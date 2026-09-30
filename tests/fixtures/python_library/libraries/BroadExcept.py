"""Broad except without re-raise (broad_except); re-raising handler is fine."""
from robot.api.deco import keyword, library


@library(scope="GLOBAL")
class BroadExcept:
    """Error handling."""

    @keyword
    def swallow(self) -> None:
        """Swallow everything."""
        try:
            int("x")
        except Exception:
            pass

    @keyword
    def reraise(self) -> None:
        """Re-raise."""
        try:
            int("x")
        except Exception as err:
            raise AssertionError("bad") from err
