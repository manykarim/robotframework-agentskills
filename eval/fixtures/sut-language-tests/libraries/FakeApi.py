"""An in-process fake API with a session, users and orders."""

from robot.api.deco import keyword, library


@library(scope="GLOBAL")
class FakeApi:
    def __init__(self) -> None:
        self._open = False
        self._users: dict[str, dict] = {}
        self._orders: dict[str, str] = {}

    @keyword
    def connect_api(self) -> None:
        self._open = True
        self._users = {"alice": {"role": "admin"}}
        self._orders = {}

    @keyword
    def disconnect_api(self) -> None:
        self._open = False

    def _require_session(self) -> None:
        if not self._open:
            raise AssertionError("No API session: run Open Api Session first.")

    @keyword
    def create_api_user(self, name: str, role: str = "user") -> None:
        self._require_session()
        self._users[name] = {"role": role}

    @keyword
    def api_user_should_exist(self, name: str) -> None:
        self._require_session()
        if name not in self._users:
            raise AssertionError(f"User '{name}' does not exist.")

    @keyword
    def delete_api_user(self, name: str) -> None:
        self._require_session()
        self._users.pop(name, None)

    @keyword
    def api_user_should_not_exist(self, name: str) -> None:
        self._require_session()
        if name in self._users:
            raise AssertionError(f"User '{name}' still exists.")

    @keyword
    def create_api_order(self, order_id: str, item: str) -> None:
        self._require_session()
        self._orders[order_id] = item

    @keyword
    def api_order_should_contain(self, order_id: str, item: str) -> None:
        self._require_session()
        if self._orders.get(order_id) != item:
            raise AssertionError(f"Order '{order_id}' has {self._orders.get(order_id)!r}, not {item!r}.")

    @keyword
    def cancel_api_order(self, order_id: str) -> None:
        self._require_session()
        self._orders.pop(order_id, None)

    @keyword
    def api_order_count_should_be(self, count: int) -> None:
        self._require_session()
        if len(self._orders) != count:
            raise AssertionError(f"{len(self._orders)} orders, expected {count}.")
