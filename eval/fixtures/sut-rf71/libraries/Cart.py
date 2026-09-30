"""A shopping cart 'application' (new cart per test)."""

from robot.api.deco import keyword, library


@library(scope="TEST")
class Cart:
    def __init__(self) -> None:
        self._items: dict[str, int] = {}
        self._open = False

    @keyword
    def open_cart(self) -> None:
        self._open, self._items = True, {}

    @keyword
    def add_product(self, product: str, quantity: int) -> None:
        if not self._open:
            raise AssertionError("Open the cart first.")
        if quantity < 1:
            raise AssertionError(f"Quantity must be positive, got {quantity}.")
        self._items[product] = self._items.get(product, 0) + quantity

    @keyword
    def cart_should_contain(self, product: str, quantity: int) -> None:
        got = self._items.get(product, 0)
        if got != quantity:
            raise AssertionError(f"Cart has {got} x {product}, expected {quantity}.")

    @keyword
    def cart_size_should_be(self, size: int) -> None:
        got = sum(self._items.values())
        if got != size:
            raise AssertionError(f"Cart has {got} items, expected {size}.")
