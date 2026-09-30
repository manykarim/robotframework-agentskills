"""Inline type in an embedded name (keyword_creation_failed + no_keywords)."""
from robot.api.deco import keyword


@keyword("Take ${qty: int} pears")
def take(qty):
    return qty
