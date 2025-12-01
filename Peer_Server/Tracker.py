from flask import Flask, request, jsonify
import time
from django_client_peer import *

app = Flask(__name__)

# Lista de peers guardada em memória
peers = {}  # dict: peer_id -> {host, port, last_seen}


@app.route("/register", methods=["POST"])
def register_peer():
    data = request.json
    peer_id = data["peer_id"]
    host = data["host"]
    port = data["port"]

    # Save peer directly in Django DB
    publish_peer(peer_id, host, port, time.time())

    print(f"[+] Peer registado: {peer_id} — {host}:{port}")
    return jsonify({"status": "ok"}), 200

@app.route("/peers", methods=["GET"])
def get_peers():
    now = time.time()
    active_peers = []

    for peer_id, info in peers.items():
        if now - info["last_seen"] < 30:  # timeout 30s
            active_peers.append({
                "id": peer_id,
                "host": info["host"],
                "port": info["port"]
            })

    return jsonify(active_peers), 200


@app.route("/heartbeat", methods=["POST"])
def heartbeat():
    data = request.json
    peer_id = data["peer_id"]

    if peer_id in peers:
        peers[peer_id]["last_seen"] = time.time()

    return jsonify({"status": "alive"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)