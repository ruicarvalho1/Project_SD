import jwt
import time
import sys
import os
import requests
from flask import Flask, request, jsonify
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend

app = Flask(__name__)

CA_API_URL = "http://127.0.0.1:8000/api/get_ca_cert/"

# Stores active peers by peer_id
peers = {}

# Maximum time (in seconds) a peer can stay without sending a heartbeat
TIMEOUT_SECONDS = 30

# Cached CA public key
CA_PUBLIC_KEY_CACHE = None


def fetch_ca_public_key():
    """
    Fetch the CA's public key once and cache it.
    """
    global CA_PUBLIC_KEY_CACHE
    if CA_PUBLIC_KEY_CACHE:
        return CA_PUBLIC_KEY_CACHE

    try:
        response = requests.post(CA_API_URL, json={})

        if response.status_code == 200:
            data = response.json()
            cert_pem = data.get("certificate_pem")
            if not cert_pem:
                return None

            cert = load_pem_x509_certificate(cert_pem.encode(), default_backend())
            CA_PUBLIC_KEY_CACHE = cert.public_key()
            print("[SUCCESS] CA public key loaded.")
            return CA_PUBLIC_KEY_CACHE

    except Exception as e:
        print(f"[CRITICAL] Failed to contact CA: {e}")
        return None


def validate_token(token):
    """
    Validate the token signature using the CA public key.
    Returns the peer_id (sub) if valid, otherwise None.
    """
    public_key = fetch_ca_public_key()
    if not public_key:
        return None

    try:
        payload = jwt.decode(token, public_key, algorithms=["RS256"])
        return payload["sub"]
    except Exception as e:
        print(f"[TOKEN REJECTED] {e}")
        return None


@app.route("/register", methods=["POST"], strict_slashes=False)
def register_peer():
    """
    Register a peer in the tracker using a valid JWT.
    """
    data = request.json
    token = data.get("token")
    port = data.get("port")

    print("\n" + "=" * 60)
    print(" [TRACKER] Registration request received")
    print("=" * 60)

    if token:
        print(" [TRACKER] Token received:")
        print(token)
    else:
        print(" [TRACKER] Warning: Request without token")

    print("-" * 60)

    if not token or not port:
        return jsonify({"error": "Missing data"}), 400

    peer_id = validate_token(token)

    if not peer_id:
        print(" [TRACKER] Access denied: Invalid token")
        return jsonify({"error": "Invalid token"}), 403

    client_ip = request.remote_addr
    peers[peer_id] = {
        "host": client_ip,
        "port": port,
        "last_seen": time.time()
    }

    print(f" [TRACKER] Peer accepted: {peer_id} at {client_ip}:{port}")
    print("=" * 60 + "\n")

    return jsonify({"status": "connected", "your_ip": client_ip}), 200


@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    """
    Receive heartbeat signals from peers to keep them active.
    """
    data = request.json
    peer_id = data.get("peer_id")

    if peer_id in peers:
        peers[peer_id]["last_seen"] = time.time()
        return jsonify({"status": "alive"}), 200

    return jsonify({"error": "Unknown peer"}), 404


@app.route("/peers", methods=["GET"])
def get_peers():
    """
    Return all active peers and remove those that timed out.
    """
    now = time.time()
    active = []
    to_remove = []

    for pid, info in peers.items():
        if now - info["last_seen"] < TIMEOUT_SECONDS:
            active.append({
                "peer_id": pid,
                "host": info["host"],
                "port": info["port"]
            })
        else:
            to_remove.append(pid)

    for pid in to_remove:
        del peers[pid]

    return jsonify(active), 200


if __name__ == "__main__":
    print("[TRACKER] Running on port 5555...")
    fetch_ca_public_key()
    app.run(host="0.0.0.0", port=5555, debug=True)
