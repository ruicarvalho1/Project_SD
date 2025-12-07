import base64
import hashlib
import requests
from datetime import datetime, timezone
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

TSA_URL = "http://localhost:7100/timestamp"
TSA_CERT_URL = "http://localhost:7100/tsa_cert"

def sha256_bytes(data: bytes) -> bytes:
    h = hashlib.sha256()
    h.update(data)
    return h.digest()

def verify_tsa_token(token: dict, original_data: bytes):
    """Verifies the TSA signature just to confirm TSA is working."""
    digest_b64 = token["digest_b64"]
    digest_bytes = base64.b64decode(digest_b64)

    if digest_bytes != sha256_bytes(original_data):
        print("Digest mismatch! TSA token does not match original data.")
        return False

    tsa_cert_pem = token["tsa_cert_pem"]
    tsa_cert = x509.load_pem_x509_certificate(tsa_cert_pem.encode())
    pubkey = tsa_cert.public_key()

    timestamp_iso = token["timestamp"]
    nonce = token["nonce"]
    serial = token["serial"]

    full_token_bytes = (
        digest_bytes
        + timestamp_iso.encode()
        + nonce.encode()
        + serial.encode()
    )

    signature = base64.b64decode(token["signature_b64"])

    try:
        pubkey.verify(
            signature,
            full_token_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        print("TSA signature verified successfully!")
        return True
    except Exception as e:
        print("TSA signature verification failed:", e)
        return False

def request_timestamp(data: bytes) -> dict:
    digest = sha256_bytes(data)
    digest_b64 = base64.b64encode(digest).decode()

    payload = {
        "digest_b64": digest_b64,
        "digest_algo": "sha256",
    }

    resp = requests.post(TSA_URL, json=payload)
    resp.raise_for_status()
    return resp.json()


def request_timestamp_unix(data: bytes) -> tuple[int, dict]:
    """
    Requests a timestamp token from the TSA server for the given data.
    """
    token = request_timestamp(data)

    ts_str = token["timestamp"]
    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    ts_unix = int(dt.replace(tzinfo=timezone.utc).timestamp())

    return ts_unix, token
