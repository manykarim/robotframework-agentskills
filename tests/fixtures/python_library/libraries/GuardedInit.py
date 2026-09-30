"""Side effect guarded by robot_running / dry_run_active (inactive under libdoc)."""
from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn


@library(scope="GLOBAL")
class GuardedInit:
    """Guarded connection."""

    def __init__(self):
        self.connected = False
        if BuiltIn().robot_running and not BuiltIn().dry_run_active:
            print("REALLY CONNECTING")
            self.connected = True

    @keyword
    def is_connected(self) -> bool:
        """Return the connection state."""
        return self.connected
