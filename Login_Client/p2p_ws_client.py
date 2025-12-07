import socketio
import threading
import requests

GLOBAL_SESSION_TOKEN = None
TRACKER_WS_URL = "http://127.0.0.1:5555"


def set_global_token(token: str) -> None:
    """Store the global session token used for authenticated broadcasts."""
    global GLOBAL_SESSION_TOKEN
    GLOBAL_SESSION_TOKEN = token


class P2PTrackerClient:
    """WebSocket client for real-time communication with the tracker."""

    def __init__(self, username: str):
        self.username = username
        self.sio = socketio.Client(reconnection=True)
        self.is_authenticated = False
        self.refresh_callback = None

        @self.sio.on("connect")
        def on_connect():
            pass

        @self.sio.on("disconnect")
        def on_disconnect():
            self.is_authenticated = False

        @self.sio.on("status")
        def on_status(data):
            if data.get("message") == "Authenticated":
                self.is_authenticated = True

        @self.sio.on("new_event")
        def on_new_event(data):
            """
            Generic event from tracker.

            If a refresh callback is registered, we try to call it with the
            event data. If the callback does not accept parameters, we fall
            back to calling it without arguments.
            """
            if self.refresh_callback:
                try:
                    self.refresh_callback(data)
                except TypeError:
                    # For callbacks that don't accept parameters
                    self.refresh_callback()

    def set_refresh_callback(self, callback_func):
        """Register the refresh function used by the client (menu or auction room)."""
        self.refresh_callback = callback_func

    def connect_and_auth(self, token: str, p2p_port: int) -> bool:
        """Connect to tracker and authenticate using JWT."""
        try:
            self.sio.connect(
                TRACKER_WS_URL,
                transports=["websocket", "polling"],
            )
            self.sio.emit("authenticate", {"token": token, "port": p2p_port})
            threading.Thread(target=self.sio.wait, daemon=True).start()
        except socketio.exceptions.ConnectionError:
            return False
        return True

    def broadcast_event(self, message_type: str, payload: dict) -> None:
        """
        Sends a broadcast event to the tracker via HTTP.

        The tracker will:
        - validate the token,
        - optionally update its internal state (e.g., auction leader),
        - broadcast "new_event" to all connected peers.
        """
        if not GLOBAL_SESSION_TOKEN:
            return

        try:
            requests.post(
                f"{TRACKER_WS_URL}/broadcast",
                json={
                    "token": GLOBAL_SESSION_TOKEN,
                    "payload": {
                        "type": message_type,
                        "data": payload,
                    },
                },
                timeout=2,
            )
        except Exception:
            pass
