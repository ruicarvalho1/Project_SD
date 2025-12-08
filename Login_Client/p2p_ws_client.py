import socketio
import threading
import requests

GLOBAL_SESSION_TOKEN = None
TRACKER_WS_URL = "http://127.0.0.1:5555"


def set_global_token(token: str) -> None:
    """Store the global session token used for authenticated requests."""
    global GLOBAL_SESSION_TOKEN
    GLOBAL_SESSION_TOKEN = token


class P2PTrackerClient:
    """WebSocket client to interact with the P2P tracker server."""
    def __init__(self, username: str):
        self.username = username
        self.sio = socketio.Client(reconnection=True)
        self.is_authenticated = False

        self.refresh_callback = None
        self.direct_handler = None

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
            if self.refresh_callback:
                try:
                    self.refresh_callback(data)
                except TypeError:
                    self.refresh_callback()

        @self.sio.on("direct_message")
        def on_direct_message(msg):
            if self.direct_handler:
                try:
                    self.direct_handler(msg)
                except TypeError:
                    self.direct_handler()


    # Callback registration
    def set_refresh_callback(self, callback_func):
        """Register the callback for broadcast events (new_event)."""
        self.refresh_callback = callback_func

    def set_direct_handler(self, callback_func):
        """Register the callback for direct peer-to-peer messages."""
        self.direct_handler = callback_func


    # Connection and Authentication
    def connect_and_auth(self, token: str, p2p_port: int) -> bool:
        """Connect to the tracker and authenticate using JWT."""
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


    # Public broadcast
    def broadcast_event(self, message_type: str, payload: dict) -> None:
        """
        Send a broadcast event to the tracker.
        Tracker validates the token and rebroadcasts to all peers.
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


    # Pseudonym association (used to resolve winner later)
    def associate_pseudonym(self, auction_id: int, pseudonym_id: str) -> None:
        """Tell the tracker that pseudonym_id belongs to this peer for a given auction."""
        try:
            requests.post(
                f"{TRACKER_WS_URL}/associate_pseudonym",
                json={
                    "auction_id": str(auction_id),
                    "pseudonym": pseudonym_id,
                    "peer_id": self.username,
                },
                timeout=2,
            )
        except Exception:
            pass


    # Resolve (auction_id, pseudonym) → peer_id
    def resolve_winner(self, auction_id: int, pseudonym_id: str):
        """Ask the tracker which peer_id owns the given pseudonym for an auction."""
        try:
            resp = requests.post(
                f"{TRACKER_WS_URL}/resolve",
                json={
                    "auction_id": str(auction_id),
                    "pseudonym": pseudonym_id,
                },
                timeout=2,
            )
            if resp.status_code != 200:
                return None
            return resp.json().get("peer_id")
        except Exception:
            return None


    # Direct peer-to-peer messaging
    def send_direct(self, peer_id: str, payload: dict) -> bool:

        if not GLOBAL_SESSION_TOKEN:
            return False

        try:
            resp = requests.post(
                f"{TRACKER_WS_URL}/direct",
                json={
                    "token": GLOBAL_SESSION_TOKEN,
                    "peer_id": peer_id,
                    "payload": payload,
                },
                timeout=2,
            )
            return resp.status_code == 200
        except Exception:
            return False
