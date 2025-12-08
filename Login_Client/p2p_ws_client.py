# Login_Client/p2p_ws_client.py
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
    """WebSocket client for real-time communication with the tracker."""

    def __init__(self, username: str):
        self.username = username
        self.sio = socketio.Client(reconnection=True)
        self.is_authenticated = False

        # callbacks
        self.refresh_callback = None      # para "new_event"
        self.direct_handler = None        # para "direct_message"

        @self.sio.on("connect")
        def on_connect():
            # ligação estabelecida
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
            Evento broadcast vindo do tracker (NEW_BID, NEW_AUCTION, etc.).
            """
            if self.refresh_callback:
                try:
                    self.refresh_callback(data)
                except TypeError:
                    self.refresh_callback()

        @self.sio.on("direct_message")
        def on_direct_message(msg):
            """
            Mensagem direta (CERT_REQUEST, CERT_RESPONSE, etc.)
            enviada apenas para este peer.
            """
            if self.direct_handler:
                try:
                    self.direct_handler(msg)
                except TypeError:
                    self.direct_handler()

    # ------------------------------------------------------------------ #
    # Callbacks
    # ------------------------------------------------------------------ #
    def set_refresh_callback(self, callback_func):
        """Regista a função chamada nos broadcasts públicos (new_event)."""
        self.refresh_callback = callback_func

    def set_direct_handler(self, callback_func):
        """Regista a função chamada nas mensagens diretas (direct_message)."""
        self.direct_handler = callback_func

    # ------------------------------------------------------------------ #
    # Ligação e autenticação
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Broadcast público (NEW_BID, NEW_AUCTION, ...)
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Associação pseudónimo → peer_id (usado mais tarde para resolver vencedor)
    # ------------------------------------------------------------------ #
    def associate_pseudonym(self, auction_id: int, pseudonym_id: str) -> None:
        """
        Diz ao tracker: 'no leilão X, o pseudónimo Y pertence a este peer_id (username)'.
        Usa o endpoint /associate_pseudonym.
        """
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

    # ------------------------------------------------------------------ #
    # Resolver (auction_id, pseudonym) → peer_id
    # ------------------------------------------------------------------ #
    def resolve_winner(self, auction_id: int, pseudonym_id: str):
        """
        Pergunta ao tracker: 'no leilão X, o pseudónimo Y corresponde a que peer_id?'.
        Usa o endpoint /resolve.
        """
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
            data = resp.json()
            return data.get("peer_id")
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    # Mensagem direta para UM peer (CERT_REQUEST, CERT_RESPONSE, etc.)
    # ------------------------------------------------------------------ #
    def send_direct(self, peer_id: str, payload: dict) -> bool:
        """
        Envia uma mensagem privada para um peer específico (por peer_id),
        através do endpoint /direct.

        payload: dict com, por exemplo:
            {
                "type": "CERT_REQUEST",
                "auction_id": ...,
                "seller_cert": "...PEM..."
            }
        """
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
