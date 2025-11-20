# ca_server.py (clean version - identity certificates only)
import os
import datetime
from flask import Flask, request, jsonify
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
ISSUED_DIR = os.path.join(STORAGE_DIR, "issued")
os.makedirs(ISSUED_DIR, exist_ok=True)

CA_KEY_PATH = os.path.join(STORAGE_DIR, "ca_private_key.pem")
CA_CERT_PATH = os.path.join(STORAGE_DIR, "ca_cert.pem")


# ---------------------------
# BOOTSTRAP CA IF MISSING
# ---------------------------
def bootstrap_ca():
    if os.path.exists(CA_KEY_PATH) and os.path.exists(CA_CERT_PATH):
        return

    print("Bootstrapping CA...")

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    with open(CA_KEY_PATH, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "PT"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MyAuctionCA"),
        x509.NameAttribute(NameOID.COMMON_NAME, "myauction.root.ca"),
    ])

    now = datetime.datetime.utcnow()

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(private_key, hashes.SHA256())
    )

    with open(CA_CERT_PATH, "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

    print("CA bootstrapped successfully.")


bootstrap_ca()


# ---------------------------
# LOAD CA MATERIAL
# ---------------------------
with open(CA_KEY_PATH, "rb") as f:
    ca_private_key = serialization.load_pem_private_key(f.read(), password=None)

with open(CA_CERT_PATH, "rb") as f:
    ca_cert = x509.load_pem_x509_certificate(f.read())


# ---------------------------
# FLASK SERVER
# ---------------------------
app = Flask(__name__)


@app.route("/ca_cert", methods=["GET"])
def ca_cert_endpoint():
    with open(CA_CERT_PATH, "r") as f:
        return f.read(), 200, {"Content-Type": "text/plain"}


@app.route("/sign_csr", methods=["POST"])
def sign_csr():
    data = request.get_json()

    if not data or "csr" not in data:
        return jsonify({"error": "Missing CSR"}), 400

    csr_pem = data["csr"]

    try:
        csr = x509.load_pem_x509_csr(csr_pem.encode())
    except Exception as e:
        return jsonify({"error": "Invalid CSR format", "details": str(e)}), 400

    # Verify CSR signature
    try:
        csr.public_key().verify(
            csr.signature,
            csr.tbs_certrequest_bytes,
            padding.PKCS1v15(),
            csr.signature_hash_algorithm,
        )
    except Exception as e:
        return jsonify({"error": "CSR signature verification failed", "details": str(e)}), 400

    # Minimal policy (RSA >= 2048)
    if csr.public_key().key_size < 2048:
        return jsonify({"error": "RSA key too small"}), 400

    now = datetime.datetime.utcnow()

    # BUILD CERTIFICATE FOR AUTHENTICATION
    builder = (
        x509.CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(ca_cert.subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False
        )
    )

    user_cert = builder.sign(private_key=ca_private_key, algorithm=hashes.SHA256())

    # Save certificate
    serial = user_cert.serial_number
    filename = os.path.join(ISSUED_DIR, f"{serial}.pem")

    with open(filename, "wb") as f:
        f.write(user_cert.public_bytes(serialization.Encoding.PEM))

    return user_cert.public_bytes(serialization.Encoding.PEM).decode(), 200, {"Content-Type": "text/plain"}


if __name__ == "__main__":
    app.run(port=5000)
