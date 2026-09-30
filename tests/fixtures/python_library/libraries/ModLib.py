"""Module library that imports a function (leaked_keyword)."""
from os.path import join  # noqa: F401  - becomes a keyword 'Join'


def my_keyword(value: str) -> str:
    """Echo the value."""
    return value
