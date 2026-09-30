"""RF 7.0+ example: values shared by every environment.

Import in a suite with ``Variables    ../variables/common.py``. Module-level
names become variables; ``LIST__`` and ``DICT__`` prefixes create list and
dictionary variables; names starting with an underscore are skipped.
"""

RETRIES = 3
TIMEOUT = "10 seconds"
LIST__BROWSERS = ["chromium", "firefox"]
DICT__ADMIN = {"name": "admin", "role": "owner"}
