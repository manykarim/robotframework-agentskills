"""Decorator without functools.wraps (signature_lost)."""


def deco(func):
    def inner(*args, **kwargs):
        return func(*args, **kwargs)
    return inner


class WrapLib:
    """Wrapped."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    @deco
    def wrapped_keyword(self, a: int) -> int:
        """Doc."""
        return a
