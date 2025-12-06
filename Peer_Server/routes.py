from flask import request, jsonify
from auth_utils import validate_token
from state import (
    PEERS, PEER_SIDS, SID_PEERS,
    update_peer_heartbeat, get_active_peers,
    update_auction_leader, load_auction_leaders,
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