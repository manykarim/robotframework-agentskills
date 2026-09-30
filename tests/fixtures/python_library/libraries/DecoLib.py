"""@library class: one public method forgot @keyword (public_method_not_keyword)."""
from robot.api.deco import keyword, library


@library(scope="SUITE")
class DecoLib:
    """Decorated library."""

    def forgot_decorator(self):
        return 1

    @keyword
    def decorated(self) -> int:
        """Return two."""
        return 2
