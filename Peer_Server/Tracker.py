import jwt
import time
import requests
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, disconnect
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend
from threading import Lock

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

CA_API_URL = "http://127.0.0.1:8000/api/get_ca_cert/"

PEERS = {}
PEER_SIDS = {}
SID_PEERS = {}

TIMEOUT_SECONDS = 30
CA_PUBLIC_KEY_CACHE = None
thread_lock = Lock()


# Token validation
def fetch_ca_public_key():
    global CA_PUBLIC_KEY_CACHE
    if CA_PUBLIC_KEY_CACHE:
        return CA_PUBLIC_KEY_CACHE
    try:
        response = requests.post(CA_API_URL, json={})
        if response.status_code == 200:
            cert_pem = response.json().get("certificate_pem")
            cert = load_pem_x509_certificate(cert_pem.encode(), default_backend())
            CA_PUBLIC_KEY_CACHE = cert.public_key()
            return CA_PUBLIC_KEY_CACHE
    except:
        return None


def validate_token(token):
    public_key = fetch_ca_public_key()
    if not public_key:
        return None
    try:
        payload = jwt.decode(token, public_key, algorithms=["RS256"])
        return payload["sub"]
    except:
        return None


# WebSocket events
@socketio.on("connect")
def handle_connect():
    print(f"[SOCKET] Connected: {request.sid}")


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    if sid in SID_PEERS:
        peer_id = SID_PEERS[sid]
        with thread_lock:
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

    with thread_lock:
        PEER_SIDS[peer_id] = sid
        SID_PEERS[sid] = peer_id
        PEERS[peer_id] = {
            "host": client_ip,
            "port": port,
            "last_seen": time.time()
        }

    print(f"[SOCKET] Authenticated: {peer_id} @ {client_ip}")
    emit("status", {"message": "Authenticated", "user": peer_id})


# HTTP endpoints
@app.route("/register", methods=["POST"])
def register_peer_http():
    token = request.json.get("token")
    peer_id = validate_token(token)
    if not peer_id:
        return jsonify({"error": "Invalid token"}), 403
    return jsonify({"status": "ok", "message": "Use WebSocket for real-time."}), 200


@app.route("/broadcast", methods=["POST"])
def broadcast_message():
    data = request.json
    token = data.get("token")
    payload = data.get("payload")

    sender_id = validate_token(token)
    if not sender_id:
        return jsonify({"error": "Access denied"}), 403

    msg = {
        "sender": sender_id,
        "type": payload.get("type"),
        "data": payload.get("data")
    }

    socketio.emit("new_event", msg, broadcast=True, include_self=False)
    return jsonify({"status": "broadcast_sent", "receivers": len(PEER_SIDS) - 1}), 200


@app.route("/peers", methods=["GET"])
def get_peers():
    now = time.time()
    active = [
        {"peer_id": pid, "host": info["host"], "port": info["port"]}
        for pid, info in PEERS.items()
        if now - info["last_seen"] < TIMEOUT_SECONDS
    ]
    return jsonify(active), 200


@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    peer_id = request.json.get("peer_id")
    if peer_id in PEERS:
        PEERS[peer_id]["last_seen"] = time.time()
        return jsonify({"status": "alive"}), 200
    return jsonify({"error": "Unknown peer"}), 404


if __name__ == "__main__":
    print("[TRACKER] Starting SocketIO server on port 5555...")
    fetch_ca_public_key()
    socketio.run(app, host="0.0.0.0", port=5555, debug=True)
