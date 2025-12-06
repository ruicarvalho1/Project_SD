import base64
import json
from datetime import datetime, timezone

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate


AUTH_SERVER_BASE = "http://127.0.0.1:8000"
GET_USER_CERT_ENDPOINT = "/api/get_user_cert/"


def _fetch_user_certificate(username: str):
    """
    Fetch the user's certificate from the Django CA service.
    """
    try:
        resp = requests.post(
            AUTH_SERVER_BASE + GET_USER_CERT_ENDPOINT,
            json={"username": username},
            timeout=3,
        )
        if resp.status_code != 200:
            print(f"[PSEUDONYM] Failed to fetch cert for {username}: {resp.text}")
            return None, None

        data = resp.json()
        return data.get("certificate_pem"), data.get("serial_number")
    except Exception as e:
        print(f"[PSEUDONYM] Error contacting auth server: {e}")
        return None, None


def _parse_token_time(value: str) -> datetime:
    """
    Normalize time strings from the delegation token into a timezone-aware UTC datetime.

    """
    if not isinstance(value, str):
        raise ValueError(f"Invalid time value type: {type(value)}")

    v = value.strip()

    if v.endswith("Z"):
        v = v[:-1]

    dt = datetime.fromisoformat(v)

    # If naive, force UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def _validate_delegation_token_structure(token: dict, msg_data: dict) -> bool:
    """
    Basic structural and temporal validation of the delegation token.
    """
    required_fields = [
        "auction_id",
        "pseudonym_id",
        "pseudonym_pubkey",
        "user_cert_serial",
        "not_before",
        "not_after",
        "signature",
    ]

    for field in required_fields:
        if field not in token:
            print(f"[PSEUDONYM] Delegation token missing field: {field}")
            return False

    # Bind auction_id and pseudonym_id to the message
    if str(token["auction_id"]) != str(msg_data.get("auction_id")):
        print("[PSEUDONYM] Token auction_id does not match message auction_id")
        return False

    if str(token["pseudonym_id"]) != str(msg_data.get("pseudonym_id")):
        print("[PSEUDONYM] Token pseudonym_id does not match message pseudonym_id")
        return False

    # Check temporal validity
    try:
        now = datetime.now(timezone.utc)
        not_before = _parse_token_time(token["not_before"])
        not_after = _parse_token_time(token["not_after"])

        if not (not_before <= now <= not_after):
            print("[PSEUDONYM] Delegation token is outside its validity window")
            return False
    except Exception as e:
        print(f"[PSEUDONYM] Failed to parse token time window: {e}")
        return False

    return True


def _verify_delegation_signature(token: dict, username: str) -> bool:
    """
    Verify that the delegation token was signed by the user's real identity
    (using the certificate stored in Django).
    """
    cert_pem, serial_number = _fetch_user_certificate(username)
    if not cert_pem or not serial_number:
        print("[PSEUDONYM] Could not retrieve user certificate from auth server")
        return False

    # Serial must match
    if str(serial_number) != str(token.get("user_cert_serial")):
        print("[PSEUDONYM] user_cert_serial mismatch between token and database")
        return False

    try:
        cert = load_pem_x509_certificate(cert_pem.encode("utf-8"), default_backend())
        public_key = cert.public_key()
    except Exception as e:
        print(f"[PSEUDONYM] Failed to load user certificate: {e}")
        return False

    sig_b64 = token.get("signature")
    if not sig_b64:
        print("[PSEUDONYM] Delegation token missing signature field")
        return False

    try:
        signature = base64.b64decode(sig_b64)
    except Exception as e:
        print(f"[PSEUDONYM] Failed to decode delegation signature: {e}")
        return False

    payload = {k: v for k, v in token.items() if k != "signature"}
    message = json.dumps(payload, sort_keys=True).encode("utf-8")

    try:
        public_key.verify(
            signature,
            message,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except Exception as e:
        print(f"[PSEUDONYM] Delegation token signature invalid: {e}")
        return False


def _verify_pseudonym_signature(token: dict, msg_data: dict) -> bool:
    """
    Verify that the bid was signed by the pseudonym private key, using the
    public key included in the delegation token.
    """
    pseudo_sig_b64 = msg_data.get("pseudonym_signature")
    if not pseudo_sig_b64:
        print("[PSEUDONYM] Missing pseudonym_signature in message")
        return False

    try:
        pseudo_sig = base64.b64decode(pseudo_sig_b64)
    except Exception as e:
        print(f"[PSEUDONYM] Failed to decode pseudonym_signature: {e}")
        return False

    pseudo_pub_b64 = token.get("pseudonym_pubkey")
    if not pseudo_pub_b64:
        print("[PSEUDONYM] Token missing pseudonym_pubkey")
        return False

    try:
        pseudo_pub_pem = base64.b64decode(pseudo_pub_b64)
        pseudo_pub_key = serialization.load_pem_public_key(
            pseudo_pub_pem,
            backend=default_backend(),
        )
    except Exception as e:
        print(f"[PSEUDONYM] Failed to load pseudonym public key: {e}")
        return False

    msg_obj = {
        "auction_id": msg_data.get("auction_id"),
        "amount": msg_data.get("amount"),
        "tx_hash": str(msg_data.get("tx_hash")),
        "pseudonym_id": msg_data.get("pseudonym_id"),
    }
    message = json.dumps(msg_obj, sort_keys=True).encode("utf-8")

    try:
        pseudo_pub_key.verify(pseudo_sig, message)
        return True
    except TypeError:
        # RSA/PKCS#1 v1.5 + SHA-256
        try:
            pseudo_pub_key.verify(
                pseudo_sig,
                message,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return True
        except Exception as e:
            print(f"[PSEUDONYM] Pseudonym signature invalid: {e}")
            return False
    except Exception as e:
        print(f"[PSEUDONYM] Pseudonym signature invalid: {e}")
        return False


def validate_delegation_and_pseudonym(msg_data: dict, sender_id: str) -> bool:
    """
    High-level validation used by /broadcast on NEW_BID events.

    Steps:
    1) Validate delegation_token structure + time window.
    2) Verify delegation_token signature with the user's certificate.
    3) Verify pseudonym_signature using the pseudonym public key.
    """
    delegation_token = msg_data.get("delegation_token")

    if delegation_token is None:
        print("[PSEUDONYM] NEW_BID without delegation_token")
        return False

    if isinstance(delegation_token, str):
        try:
            delegation_token = json.loads(delegation_token)
        except Exception as e:
            print(f"[PSEUDONYM] Failed to parse delegation_token JSON string: {e}")
            return False

    if not isinstance(delegation_token, dict):
        print("[PSEUDONYM] delegation_token is not a dict")
        return False

    if not _validate_delegation_token_structure(delegation_token, msg_data):
        return False

    if not _verify_delegation_signature(delegation_token, sender_id):
        return False

    if not _verify_pseudonym_signature(delegation_token, msg_data):
        return False

    return True
