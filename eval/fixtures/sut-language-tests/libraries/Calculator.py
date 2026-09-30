"""A tiny calculator 'application' for BDD tasks."""

from robot.api.deco import keyword, library


@library(scope="TEST")
class Calculator:
    def __init__(self) -> None:
        self._result = 0

    @keyword
    def clear_calculator(self) -> None:
        self._result = 0

    @keyword
    def add_numbers(self, a: int, b: int) -> int:
        self._result = a + b
        return self._result

    @keyword
    def multiply_numbers(self, a: int, b: int) -> int:
        self._result = a * b
        return self._result

    @keyword
    def calculator_result_should_be(self, expected: int) -> None:
        if self._result != expected:
            raise AssertionError(f"{self._result} != {expected}")
