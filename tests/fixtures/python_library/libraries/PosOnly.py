"""Positional-only argument (positional_only_argument)."""


def pos_keyword(a: int, /, b: int = 1) -> int:
    """Doc."""
    return a + b
