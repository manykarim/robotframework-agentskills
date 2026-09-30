"""Naive solution: default TEST scope, so the stock resets for every test."""

from robot.api.deco import keyword, library


@library
class Inventory:
    """In-memory inventory."""

    def __init__(self) -> None:
        self._stock: dict[str, int] = {}

    @keyword
    def add_item(self, name: str, quantity: int) -> int:
        """Add ``quantity`` items called ``name``."""
        self._stock[name] = self._stock.get(name, 0) + quantity
        return self._stock[name]

    @keyword
    def item_count_should_be(self, name: str, expected: int) -> None:
        """Fail unless ``name`` has ``expected`` items."""
        actual = self._stock.get(name, 0)
        if actual != expected:
            raise AssertionError(f"{name}: expected {expected}, got {actual}")

    @keyword
    def clear_inventory(self) -> None:
        """Empty the stock."""
        self._stock.clear()
