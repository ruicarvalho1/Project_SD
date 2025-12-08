from flask import request, jsonify
from auth_utils import validate_token

from state import (
    PEERS,
    PEER_SIDS,
    SID_PEERS,
    update_peer_heartbeat,
    get_active_peers,
    update_auction_leader,
    load_auction_leaders,
    save_map,
    load_map,
    AUCTION_LEADERS,
)

from pseudonym_validation import validate_delegation_and_pseudonym


def register_http_routes(app, socketio):

    # Basic HTTP test endpoint to validate JWT.
    @app.route("/register", methods=["POST"])
    def register_peer_http():
        data = request.json or {}
        token = data.get("token")
        peer_id = validate_token(token)
        if not peer_id:
            return jsonify({"error": "Invalid token"}), 403
        return jsonify({"status": "ok", "message": "Use WebSocket for real-time."}), 200

    # Public broadcast endpoint (NEW_BID, NEW_AUCTION, etc.).
    @app.route("/broadcast", methods=["POST"])
    def broadcast_message():
        data = request.json or {}
        token = data.get("token")
        payload = data.get("payload") or {}

        sender_id = validate_token(token)
        if not sender_id:
            return jsonify({"error": "Access denied"}), 403

        msg_type = payload.get("type")
        msg_data = payload.get("data") or {}

        # Validate pseudonym on NEW_BID and update auction leader.
        if msg_type == "NEW_BID":
            if not validate_delegation_and_pseudonym(msg_data, sender_id):
                return jsonify({"error": "Invalid pseudonym delegation token or signature"}), 400

            auction_id = msg_data.get("auction_id")
            pseudonym_id = msg_data.get("pseudonym_id")

            if auction_id is not None and pseudonym_id:
                update_auction_leader(auction_id, pseudonym_id)
                print(f"[TRACKER] Auction {auction_id}: leader = {pseudonym_id}")

        # Broadcast to all peers via Socket.IO
        msg = {
            "type": msg_type,
            "data": msg_data,
        }

        socketio.emit("new_event", msg)
        return jsonify({
            "status": "broadcast_sent",
            "receivers": len(PEER_SIDS)
        }), 200

    # Returns list of currently active peers.
    @app.route("/peers", methods=["GET"])
    def get_peers():
        return jsonify(get_active_peers()), 200

    # Peer heartbeat endpoint.
    @app.route("/heartbeat", methods=["POST"])
    def heartbeat():
        data = request.json or {}
        peer_id = data.get("peer_id")
        if peer_id in PEERS:
            update_peer_heartbeat(peer_id)
            return jsonify({"status": "alive"}), 200
        return jsonify({"error": "Unknown peer"}), 404

    # Load auction leaders from disk.
    load_auction_leaders()

    # Return current leader pseudonym for an auction.
    @app.route("/auction_leader/<auction_id>", methods=["GET"])
    def get_auction_leader(auction_id):
        auction_id = str(auction_id)

        load_auction_leaders()
        leader_info = AUCTION_LEADERS.get(auction_id)

        if not leader_info:
            return jsonify({"leader_pseudonym": None}), 200

        return jsonify({
            "leader_pseudonym": leader_info.get("leader_pseudonym")
        }), 200

    # Associate pseudonym → peer_id for an auction.
    @app.route("/associate_pseudonym", methods=["POST"])
    def associate_pseudonym():
        data = request.json or {}

        auction_id = data.get("auction_id")
        pseudonym = data.get("pseudonym")
        peer_id = data.get("peer_id")

        if not auction_id or not pseudonym or not peer_id:
            return jsonify({"error": "missing fields"}), 400

        key = f"{auction_id}:{pseudonym}"

        mapping = load_map() or {}
        mapping[key] = peer_id
        save_map(mapping)

        return jsonify({"status": "ok"}), 200

    # Resolve pseudonym → peer_id for certificate exchange.
    @app.route("/resolve", methods=["POST"])
    def resolve_pseudonym():
        data = request.json or {}
        auction_id = data.get("auction_id")
        pseudonym = data.get("pseudonym")

        if not auction_id or not pseudonym:
            return jsonify({"error": "missing fields"}), 400

        mapping = load_map() or {}
        key = f"{auction_id}:{pseudonym}"

        peer_id = mapping.get(key)
        if not peer_id:
            return jsonify({"error": "not found"}), 404

        return jsonify({"peer_id": peer_id}), 200

    # Send direct message to a specific peer (CERT_REQUEST, CERT_RESPONSE, etc.).
    @app.route("/direct", methods=["POST"])
    def direct_message():
        data = request.json or {}
        token = data.get("token")
        target_peer_id = data.get("peer_id")
        payload = data.get("payload") or {}

        sender_id = validate_token(token)
        if not sender_id:
            return jsonify({"error": "Access denied"}), 403

        sid = PEER_SIDS.get(target_peer_id)
        if not sid:
            return jsonify({"error": "Target not connected"}), 404

        msg = {
            "sender": sender_id,
            "payload": payload,
        }

        socketio.emit("direct_message", msg, room=sid)
        return jsonify({"status": "direct_sent"}), 200
