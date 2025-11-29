import os
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives import serialization, hashes, padding
from core.django_client import get_trusted_user_cert
from core.ca_certgen import initialize_ca
from core.ca_state import ca_state
from core.csr_signer import sign_csr_request
import datetime, secrets, base64

app = Flask(__name__)


@app.route("/ca_cert", methods=["GET"])
def ca_cert_endpoint():
    if not ca_state.certificate:
        return jsonify({"error": "CA not initialized"}), 503

    pem_data = ca_state.certificate.public_bytes(serialization.Encoding.PEM).decode()
    return pem_data, 200, {"Content-Type": "text/plain"}


@app.route("/sign_csr", methods=["POST"])
def sign_csr():
    data = request.get_json()
    if not data or "csr" not in data:
        return jsonify({"error": "Missing CSR"}), 400

    try:
        cert_pem = sign_csr_request(data["csr"])
        return cert_pem, 200, {"Content-Type": "text/plain"}
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Processing failed", "details": str(e)}), 500




if __name__ == "__main__":

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        if not initialize_ca():
            print(" [FATAL] CA Failed to initialize.")
            exit(1)

    print(" [START] CA Server starting on port 5001...")
    app.run(port=5001, debug=True)