from flask import request
from flask_socketio import emit, disconnect
from auth_utils import validate_token
from state import PEERS, PEER_SIDS, SID_PEERS, STATE_LOCK
import time

def register_socket_events(socketio):

    @socketio.on("connect")
    def handle_connect():
        print(f"[SOCKET] Connected: {request.sid}")

    @socketio.on("disconnect")
    def handle_disconnect():
        sid = request.sid
        if sid in SID_PEERS:
            peer_id = SID_PEERS[sid]
            with STATE_LOCK:
                PEERS.pop(peer_id, None)
                PEER_SIDS.pop(peer_id, None)
                SID_PEERS.pop(sid, None)
            print(f"[SOCKET] Disconnected: {peer_id}")

    @socketio.on("authenticate")
    def handle_authentication(data):
        token = data.get("token")
        port = data.get("port")

        peer_id = validate_token(token)
        if not peer_id:
            print(f"[SOCKET] Invalid token: {request.sid}")
            disconnect()
            return

        sid = request.sid
        client_ip = request.remote_addr

        with STATE_LOCK:
            PEER_SIDS[peer_id] = sid
            SID_PEERS[sid] = peer_id
            PEERS[peer_id] = {
                "host": client_ip,
                "port": port,
                "last_seen": time.time()
            }

        print(f"[SOCKET] Authenticated: {peer_id} @ {client_ip}")
        emit("status", {"message": "Authenticated", "user": peer_id})

