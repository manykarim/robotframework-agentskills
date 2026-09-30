"""Custom argument converter example (RF 7.0+): ``Money`` from ``12.50 EUR``.

A module library. ``ROBOT_AUTO_KEYWORDS = False`` keeps the imported names
(``dataclass``, ``Decimal``) and the converter function from becoming keywords;
only ``@keyword`` functions are exposed.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from robot.api.deco import keyword

ROBOT_AUTO_KEYWORDS = False


@dataclass(frozen=True)
class Money:
    """An amount of money in one currency."""

    amount: Decimal
    currency: str


def parse_money(value: str) -> Money:
    """Convert ``'12.50 EUR'`` to ``Money``; raise ``ValueError`` on bad input."""
    try:
        amount, currency = value.split()
        return Money(Decimal(amount), currency.upper())
    except (ValueError, InvalidOperation):
        raise ValueError(f"expected '<amount> <currency>' like '12.50 EUR', got '{value}'") from None


ROBOT_LIBRARY_CONVERTERS = {Money: parse_money}


@keyword
def add_prices(first: Money, second: Money) -> Money:
    """Add two prices in the same currency, for example ``12.50 EUR`` and ``7.50 EUR``."""
    if first.currency != second.currency:
        raise ValueError(f"currency mismatch: {first.currency} and {second.currency}")
    return Money(first.amount + second.amount, first.currency)


@keyword
def price_should_be(actual: Money, expected: Money) -> None:
    """Fail unless ``actual`` equals ``expected`` (a ``Money`` or a string such as ``20 EUR``)."""
    if actual != expected:
        raise AssertionError(f"price {actual.amount} {actual.currency} != {expected.amount} {expected.currency}")
