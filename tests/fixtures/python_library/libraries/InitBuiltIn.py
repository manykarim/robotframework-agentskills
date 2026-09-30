"""BuiltIn() used in __init__ (RobotNotRunningError while loading)."""
from robot.libraries.BuiltIn import BuiltIn


class InitBuiltIn:
    """Uses BuiltIn too early."""

    def __init__(self):
        self.builtin = BuiltIn().get_library_instance("BuiltIn")

    def kw(self) -> None:
        """Doc."""
