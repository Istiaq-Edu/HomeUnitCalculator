"""Temporary local HTTP server to catch the OAuth2 callback redirect.

Starts on http://localhost:{port}/callback, captures the authorization code
from the query string, and returns a user-friendly HTML page to the browser.
"""

import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class _CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler that captures the OAuth2 callback parameters."""

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        server: "OAuthCallbackServer" = self.server  # type: ignore

        # Extract parameters
        server.auth_code = params.get("code", [None])[0]
        server.state = params.get("state", [None])[0]
        server.error = params.get("error", [None])[0]
        server.error_description = params.get("error_description", [None])[0]
        server.received = True

        # Check state mismatch
        if server.expected_state and server.state != server.expected_state:
            server.state_mismatch = True
            self._send_html(
                "<html><body><h2>Authorization Error</h2>"
                "<p>State mismatch detected. Please try again.</p>"
                "<p>You can close this tab.</p></body></html>",
                status=400,
            )
            return

        if server.error:
            self._send_html(
                f"<html><body><h2>Authorization Denied</h2>"
                f"<p>{server.error}: {server.error_description or ''}</p>"
                f"<p>You can close this tab and try again.</p></body></html>",
                status=400,
            )
            return

        self._send_html(
            "<html><body style='font-family: sans-serif; text-align: center; margin-top: 50px;'>"
            "<h2>✅ Authorization Successful</h2>"
            "<p>You can close this tab and return to Home Unit Calculator.</p>"
            "</body></html>"
        )

    def _send_html(self, html: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress default logging
        pass


class OAuthCallbackServer(HTTPServer):
    """HTTP server that listens for the OAuth2 callback on localhost.

    Attributes:
        auth_code: The authorization code from the callback (or None).
        state: The state parameter from the callback.
        error: Error code if the user denied authorization (or None).
        error_description: Human-readable error description (or None).
        received: True once the callback has been received.
        state_mismatch: True if the state didn't match expected_state.
        expected_state: The state the app sent (for CSRF protection).
    """

    def __init__(self, port: int = 8765, expected_state: str | None = None):
        super().__init__(("127.0.0.1", port), _CallbackHandler)
        self.auth_code: str | None = None
        self.state: str | None = None
        self.error: str | None = None
        self.error_description: str | None = None
        self.received: bool = False
        self.state_mismatch: bool = False
        self.expected_state = expected_state
        self.timeout = 0.5  # For handle_request non-blocking

    def wait_for_callback(self, timeout: float = 120.0) -> bool:
        """Block until the callback is received or timeout elapses.

        Returns True if callback was received, False on timeout.
        """
        import time

        start = time.time()
        while not self.received and (time.time() - start) < timeout:
            self.handle_request()
        return self.received
