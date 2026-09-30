"""A stand-in login backend: only demo/mode is a valid account."""

from robot.api.deco import keyword, library

VALID = ("demo", "mode")


@library(scope="SUITE")
class FakeAuth:
    def __init__(self) -> None:
        self._page = "login"
        self._user = ""
        self._password = ""
        self._error = ""

    @keyword
    def open_login_page(self) -> None:
        self._page, self._user, self._password, self._error = "login", "", "", ""

    @keyword
    def input_username(self, username: str) -> None:
        self._user = username

    @keyword
    def input_password(self, password: str) -> None:
        self._password = password

    @keyword
    def submit_credentials(self) -> None:
        if (self._user, self._password) == VALID:
            self._page, self._error = "welcome", ""
        else:
            self._page, self._error = "error", "Invalid username or password"

    @keyword
    def login_with_credentials(self, username: str, password: str) -> None:
        """Types ``username`` and ``password`` and submits them."""
        self.input_username(username)
        self.input_password(password)
        self.submit_credentials()

    @keyword
    def error_page_should_be_open(self) -> None:
        if self._page != "error":
            raise AssertionError(f"Expected the error page, but page is '{self._page}'.")

    @keyword
    def welcome_page_should_be_open(self) -> None:
        if self._page != "welcome":
            raise AssertionError(f"Expected the welcome page, but page is '{self._page}'.")
