from flask import request, jsonify
from auth_utils import validate_token
import json
from state import (
    PEERS, PEER_SIDS, SID_PEERS,
    update_peer_heartbeat, get_active_peers,
    update_auction_leader, load_auction_leaders,save_map, load_map,
    AUCTION_LEADERS,
)
from pseudonym_validation import validate_delegation_and_pseudonym


def register_http_routes(app, socketio):

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

        msg_type = payload.get("type")
        msg_data = payload.get("data") or {}

        if msg_type == "NEW_BID":
            # Validate pseudonym delegation token and signature
            if not validate_delegation_and_pseudonym(msg_data, sender_id):
                return jsonify({"error": "Invalid pseudonym delegation token or signature"}), 400

            auction_id = msg_data.get("auction_id")
            pseudonym_id = msg_data.get("pseudonym_id")
            if auction_id is not None and pseudonym_id:
                update_auction_leader(auction_id, pseudonym_id)
                print(f"[TRACKER] Auction {auction_id}: leader = {pseudonym_id}")
            else:
                print("[TRACKER] NEW_BID missing auction_id or pseudonym_id")

        msg = {
            "type": msg_type,
            "data": msg_data,
        }

        # broadcasting via Socket.IO
        socketio.emit("new_event", msg)
        return jsonify({
            "status": "broadcast_sent",
            "receivers": len(PEER_SIDS)
        }), 200

    @app.route("/peers", methods=["GET"])
    def get_peers():
        return jsonify(get_active_peers()), 200

    @app.route("/heartbeat", methods=["POST"])
    def heartbeat():
        peer_id = request.json.get("peer_id")
        if peer_id in PEERS:
            update_peer_heartbeat(peer_id)
            return jsonify({"status": "alive"}), 200
        return jsonify({"error": "Unknown peer"}), 404

    load_auction_leaders()

    @app.route("/auction_leader/<auction_id>", methods=["GET"])
    def get_auction_leader(auction_id):
        """Return current leader pseudonym for a given auction (if any)."""
        auction_id = str(auction_id)

        load_auction_leaders()

        leader_info = AUCTION_LEADERS.get(auction_id)
        print(f"[DEBUG] get_auction_leader({auction_id}) -> {leader_info}")

        if not leader_info:
            return jsonify({"leader_pseudonym": None}), 200

        return jsonify({
            "leader_pseudonym": leader_info.get("leader_pseudonym")
        }), 200

    @app.route("/associate_pseudonym", methods=["POST"])
    def associate_pseudonym():
        data = request.json

        pseudonym = data.get("pseudonym_pubkey")
        peer_id = data.get("peer_id")

        if not pseudonym or not peer_id:
            return jsonify({"error": "missing fields"}), 400

        mapping = load_map()
        mapping[pseudonym] = peer_id
        save_map(mapping)

        return jsonify({"status": "ok"}), 200
    
    @app.route("/resolve", methods=["POST"])
    def resolve_pseudonym():
        data = request.json
        auction_id = data.get("auction_id")
        pseudonym = data.get("pseudonym")
        seller_id = data.get("seller_id")  # provided by seller client

        if not auction_id or not pseudonym or not seller_id:
            return jsonify({"error": "missing fields"}), 400

        mapping = load_map()    
        key = f"{auction_id}:{pseudonym}"

        if key not in mapping:
            return jsonify({"error": "not found"}), 404

        entry = mapping[key]

        if entry["seller_id"] != seller_id:
            return jsonify({"error": "not your auction"}), 403

        return jsonify({
            "peer_id": entry["peer_id"]
        }), 200



    @app.route("/direct", methods=["POST"])
    def direct_message():
        data = request.json
        token = data.get("token")
        peer_id = data.get("peer_id")   
        payload = data.get("payload")

        sender_id = validate_token(token)
        if not sender_id:
            return jsonify({"error": "Access denied"}), 403

        sid = PEER_SIDS.get(peer_id)
        if not sid:
            return jsonify({"error": "Target not connected"}), 404

        msg = {
            "sender": sender_id,
            "type": payload.get("type"),
            "data": payload.get("data")
        }

        socketio.emit("new_event", msg, room=sid)
        return jsonify({"status": "direct_sent"}), 200
