"""Example keyword library for the rf-python-library skill (RF 7.0+).

The default template applied to an in-memory inventory. The tests of one suite
share the stock, so the library uses ``SUITE`` scope (see the scope table in
SKILL.md) and offers `Clear Inventory` for a suite setup or teardown.
"""

from typing import Literal

from robot.api import logger
from robot.api.deco import keyword, library


@library(scope="SUITE", version="1.0.0")
class ExampleLibrary:
    """Keeps an in-memory inventory that the tests of one suite share.

    Import it with an optional unit: ``Library    ExampleLibrary    unit=boxes``.
    Call `Clear Inventory` in a suite setup or teardown to start from an empty stock.
    """

    def __init__(self, unit: str = "pcs") -> None:
        self._unit = unit
        self._stock: dict[str, int] = {}
        self._mode = "OFF"

    @keyword
    def add_item(self, name: str, quantity: int = 1) -> int:
        """Add ``quantity`` items called ``name`` and return the new count.

        Args:
            name: Item name, for example ``apple``.
            quantity: Number of items to add; must be positive.

        Example:
        | ${count}=    Add Item    apple    3
        """
        if quantity < 1:
            raise ValueError(f"quantity must be positive, got {quantity}")
        self._stock[name] = self._stock.get(name, 0) + quantity
        logger.info(f"{name}: {self._stock[name]} {self._unit}")
        return self._stock[name]

    @keyword
    def item_count_should_be(self, name: str, expected: int) -> None:
        """Fail unless ``name`` has exactly ``expected`` items."""
        actual = self._stock.get(name, 0)
        if actual != expected:
            raise AssertionError(f"{name}: expected {expected} {self._unit}, got {actual}")

    @keyword
    def set_mode(self, mode: Literal["ON", "OFF"]) -> str:
        """Switch the inventory mode. ``on``/``off`` are accepted case-insensitively."""
        self._mode = mode
        return self._mode

    @keyword
    def clear_inventory(self) -> None:
        """Remove every item. Use it in a suite setup or teardown."""
        self._stock.clear()
        self._mode = "OFF"
