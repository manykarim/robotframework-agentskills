"""__init__ raises (import_failed with the init message)."""


class InitRaises:
    """Fails to connect."""

    def __init__(self):
        raise RuntimeError("cannot connect to the database")

    def kw(self) -> None:
        """Doc."""
