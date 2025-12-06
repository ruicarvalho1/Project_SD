# routes.py
from flask import request, jsonify
from auth_utils import validate_token
import state
from state import (
    PEERS, PEER_SIDS, SID_PEERS,
    update_peer_heartbeat, get_active_peers,
    update_auction_leader, load_auction_leaders,
)


def register_http_routes(app, socketio):
    """
    Register all HTTP routes used by the peer tracker.

    Note:
    - WebSocket events are handled elsewhere (e.g. in socket_events.py).
    - These routes are classic HTTP endpoints.
    """

    # Load auction leaders once when routes are registered
    load_auction_leaders()

    @app.route("/register", methods=["POST"])
    def register_peer_http():
        """Simple HTTP registration that validates the token."""
        data = request.json or {}
        token = data.get("token")
        peer_id = validate_token(token)
        if not peer_id:
            return jsonify({"error": "Invalid token"}), 403
        return jsonify({"status": "ok", "message": "Use WebSocket for real-time."}), 200

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

        # Update server-side state for NEW_BID events
        if msg_type == "NEW_BID":
            auction_id = msg_data.get("auction_id")
            pseudonym_id = msg_data.get("pseudonym_id")
            if auction_id is not None and pseudonym_id:
                update_auction_leader(auction_id, pseudonym_id)

        # This is the event that will be delivered to connected peers
        msg = {
            "type": msg_type,
            "data": msg_data,
        }

        socketio.emit("new_event", msg)

        return jsonify({
            "status": "broadcast_sent",
            "receivers": len(PEER_SIDS) - 1
        }), 200

    @app.route("/peers", methods=["GET"])
    def get_peers():
        """Return the list of active peers known by the tracker."""
        return jsonify(get_active_peers()), 200

    @app.route("/heartbeat", methods=["POST"])
    def heartbeat():
        """Update the last_seen timestamp for a peer."""
        data = request.json or {}
        peer_id = data.get("peer_id")
        if peer_id in PEERS:
            update_peer_heartbeat(peer_id)
            return jsonify({"status": "alive"}), 200
        return jsonify({"error": "Unknown peer"}), 404

    @app.route("/auction_leader/<auction_id>", methods=["GET"])
    def get_auction_leader(auction_id):
        """Return current leader pseudonym for a given auction (if any)."""
        auction_id = str(auction_id)

        leader_info = state.AUCTION_LEADERS.get(auction_id)
        if not leader_info:
            return jsonify({"leader_pseudonym": None}), 200
        return jsonify({
            "leader_pseudonym": leader_info.get("leader_pseudonym")
        }), 200
