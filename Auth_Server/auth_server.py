from flask import Flask, request, jsonify
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
import requests

CA_CERT_URL = "http://127.0.0.1:5000/ca_cert"

app = Flask(__name__)

# -----------------------------------------
# 1) Bootstrap CA dynamically
# -----------------------------------------
print("Fetching CA certificate from:", CA_CERT_URL)
resp = requests.get(CA_CERT_URL)

if resp.status_code != 200:
    raise Exception("Auth Server cannot start: CA unreachable")

ca_cert_pem = resp.text
ca_cert = x509.load_pem_x509_certificate(ca_cert_pem.encode())

print("CA certificate loaded successfully.")


# -----------------------------------------
# 2) LOGIN endpoint
# -----------------------------------------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    if "certificate" not in data:
        return jsonify({"error": "Missing certificate"}), 400

    cert_pem = data["certificate"]

    # Load certificate sent by client
    try:
        client_cert = x509.load_pem_x509_certificate(cert_pem.encode())
    except Exception as e:
        return jsonify({"error": "Invalid certificate format"}), 400

    # Validate signature
    try:
        ca_cert.public_key().verify(
            client_cert.signature,
            client_cert.tbs_certificate_bytes,
            padding.PKCS1v15(),
            client_cert.signature_hash_algorithm,
        )
    except Exception as e:
        return jsonify({"error": "Certificate NOT signed by CA"}), 403

    # DO NOT return username (preserve anonymity)
    return jsonify({
        "message": "authenticated",
        "status": "ok"
    }), 200


if __name__ == "__main__":
    app.run(port=6001)
