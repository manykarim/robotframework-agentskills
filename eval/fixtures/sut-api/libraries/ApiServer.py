"""Tiny stdlib HTTP API used by the sut-api fixture (no network, no deps).

Import it in a suite and start it from Suite Setup::

    Library    ../libraries/ApiServer.py
    Suite Setup       Start Api Server
    Suite Teardown    Stop Api Server

``Start Api Server`` binds 127.0.0.1 on a free port, sets the suite variable
``${API_URL}`` (e.g. ``http://127.0.0.1:43123``) and returns it.

Endpoints (JSON):

* ``GET  /health``            -> ``{"status": "ok"}``
* ``GET  /users``             -> list of users from ``data/users.json``
* ``GET  /users/<id>``        -> one user, 404 ``{"error": "not found"}`` otherwise
* ``POST /users``             -> echoes the JSON body with a new ``id``, status 201
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from robot.libraries.BuiltIn import BuiltIn

_DATA = Path(__file__).resolve().parent.parent / "data" / "users.json"


class _Handler(BaseHTTPRequestHandler):
    users: list[dict] = []

    def log_message(self, *args: object) -> None:  # keep robot console clean
        return

    def _send(self, status: int, payload: object) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.rstrip("/")
        if path == "/health":
            self._send(200, {"status": "ok"})
        elif path == "/users":
            self._send(200, self.users)
        elif path.startswith("/users/"):
            user = next((u for u in self.users if str(u["id"]) == path.rsplit("/", 1)[1]), None)
            self._send(200, user) if user else self._send(404, {"error": "not found"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/users":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send(400, {"error": "invalid json"})
            return
        body["id"] = max((u["id"] for u in self.users), default=0) + 1
        self._send(201, body)


class ApiServer:
    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self) -> None:
        self._server: ThreadingHTTPServer | None = None

    def start_api_server(self) -> str:
        """Start the API on a free local port; sets and returns ``${API_URL}``."""
        _Handler.users = json.loads(_DATA.read_text(encoding="utf-8"))
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{self._server.server_address[1]}"
        BuiltIn().set_suite_variable("${API_URL}", url)
        return url

    def stop_api_server(self) -> None:
        """Stop the API server started by `Start Api Server`."""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
