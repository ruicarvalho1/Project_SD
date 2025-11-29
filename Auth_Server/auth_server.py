from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import os, sys
import base64
import datetime
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from flask import Flask, request, jsonify
from CA_Server.core.django_client import get_trusted_user_cert


app = Flask(__name__)

AUTH_SESSIONS = {}


@app.route("/auth/challenge", methods=["POST"])
def request_challenge():
    """
    Phase 1: Client requests a challenge nonce.
    """
    data = request.get_json()
    username = data.get("username")

    if not username:
        return jsonify({"error": "Username required"}), 400

    # 1. Generate Nonce
    nonce = os.urandom(32)

    # 2. Save Session with Expiry
    AUTH_SESSIONS[username] = {
        'nonce': nonce,
        'expires_at': datetime.datetime.utcnow() + datetime.timedelta(minutes=2)
    }

    print(f" [AUTH] Challenge generated for {username}")

    return jsonify({
        "nonce": base64.b64encode(nonce).decode()
    })


@app.route("/auth/login", methods=["POST"])
def perform_login():
    """
    Phase 2 : Client responds with signed nonce for authentication.
    """
    data = request.get_json()
    username = data.get("username")
    signature_b64 = data.get("signature")

    if not username or not signature_b64:
        return jsonify({"error": "Missing credentials"}), 400

    # 1. Retrieve Session
    if username not in AUTH_SESSIONS:
        return jsonify({"error": "Challenge not requested or expired"}), 400

    session = AUTH_SESSIONS.pop(username)

    if datetime.datetime.utcnow() > session['expires_at']:
        return jsonify({"error": "Time limit exceeded"}), 408


    user_cert = get_trusted_user_cert(username)

    if not user_cert:
        return jsonify({"error": "User not found or certificate revoked"}), 403

    # 3. Verify Signature
    try:
        signature = base64.b64decode(signature_b64)
        public_key = user_cert.public_key()


        public_key.verify(
            signature,
            session['nonce'],
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    except Exception as e:
        print(f" [FAIL] Signature check failed for {username}: {e}")
        return jsonify({"error": "Invalid signature"}), 401

    print(f" [SUCCESS] {username} logged in.")
    return jsonify({"status": "authenticated", "token": "TODO_GENERATE_JWT"}), 200


if __name__ == "__main__":
    app.run(port=6001, debug=True)