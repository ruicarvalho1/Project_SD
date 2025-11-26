
import os
import base64
import uuid
import json
import datetime as dt
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography import x509
from cryptography.x509.oid import NameOID

BASE = os.path.dirname(os.path.abspath(__file__))
STORAGE = os.path.join(BASE, "storage")
os.makedirs(STORAGE, exist_ok=True)

TSA_KEY_PATH = os.path.join(STORAGE, "tsa_private_key.pem")
TSA_CERT_PATH = os.path.join(STORAGE, "tsa_cert.pem")
LOG_PATH = os.path.join(STORAGE, "tsa_tokens.log")

def bootstrap_tsa():
    if os.path.exists(TSA_KEY_PATH) and os.path.exists(TSA_CERT_PATH):
        return

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(TSA_KEY_PATH, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"PT"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"MyAuctionTSA"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"myauction.tsa"),
    ])
    now = dt.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(days=1))
        .not_valid_after(now + dt.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    with open(TSA_CERT_PATH, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print("TSA bootstrapped (key+cert created in storage/)")

bootstrap_tsa()

with open(TSA_KEY_PATH, "rb") as f:
    tsa_key = serialization.load_pem_private_key(f.read(), password=None)
with open(TSA_CERT_PATH, "rb") as f:
    tsa_cert_pem = f.read().decode()

app = Flask(__name__)

def _make_token_bytes(digest_bytes: bytes, timestamp_iso: str, nonce: str, serial: str) -> bytes:
    # canonical deterministic encoding: digest || timestamp || nonce || serial
    return digest_bytes + timestamp_iso.encode("utf-8") + nonce.encode("utf-8") + serial.encode("utf-8")

@app.route("/tsa_cert", methods=["GET"])
def get_tsa_cert():
    return tsa_cert_pem, 200, {"Content-Type": "application/x-pem-file"}

@app.route("/timestamp", methods=["POST"])
def timestamp():
    """
    Request JSON:
    {
      "digest_b64": "<base64 digest>",
      "digest_algo": "sha256"
    }

    Response JSON:
    {
      "digest_algo": "sha256",
      "digest_b64": "...",
      "timestamp": "2025-11-20T12:34:56.789000Z",
      "nonce": "<uuid4>",
      "serial": "<uuid4>",
      "signature_b64": "...",
      "tsa_cert_pem": "-----BEGIN CERTIFICATE-----..."
    }
    """
    data = request.get_json()
    if not data or "digest_b64" not in data or "digest_algo" not in data:
        return jsonify({"error": "Provide digest_b64 and digest_algo"}), 400

    if data["digest_algo"].lower() != "sha256":
        return jsonify({"error": "Only sha256 supported"}), 400

    try:
        digest_bytes = base64.b64decode(data["digest_b64"])
    except Exception:
        return jsonify({"error": "Invalid base64 digest_b64"}), 400

    now = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
    timestamp_iso = now.isoformat(timespec="microseconds")
    nonce = uuid.uuid4().hex
    serial = uuid.uuid4().hex

    token_bytes = _make_token_bytes(digest_bytes, timestamp_iso, nonce, serial)

    signature = tsa_key.sign(
        token_bytes,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256()
    )
    signature_b64 = base64.b64encode(signature).decode()

    resp = {
        "digest_algo": "sha256",
        "digest_b64": data["digest_b64"],
        "timestamp": timestamp_iso,
        "nonce": nonce,
        "serial": serial,
        "signature_b64": signature_b64,
        "tsa_cert_pem": tsa_cert_pem
    }

    # append a simple JSON line to log for audit
    with open(LOG_PATH, "a") as lf:
        lf.write(json.dumps(resp) + "\n")

    return jsonify(resp), 200

if __name__ == "__main__":
    app.run(port=7100, debug=True)

