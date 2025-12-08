import typing
from pathlib import Path
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


def _load_ca_cert(user_folder: Path) -> typing.Union[x509.Certificate, None]:
    """
    Load the local CA certificate used to validate peer certificates.
    """
    try:
        ca_path = user_folder / "ca_cert.pem"
        ca_pem = ca_path.read_text()
        return x509.load_pem_x509_certificate(ca_pem.encode("utf-8"), default_backend())
    except Exception as e:
        print(f"[CERT] Could not load CA certificate: {e}")
        return None


def validate_peer_certificate(peer_pem: str, user_folder: Path, role: str) -> bool:
    """
    Basic validation of a peer certificate:
      - parse PEM
      - check validity period
      - check issuer == local CA
      - verify signature with CA public key

    Returns True if all checks pass, False otherwise.
    `role` is just a label ("seller" / "buyer") used for logging.
    """
    try:
        cert = x509.load_pem_x509_certificate(peer_pem.encode("utf-8"), default_backend())
    except Exception as e:
        print(f"[CERT] Invalid {role} certificate format: {e}")
        return False

    now = datetime.now(timezone.utc)

    # Check validity window
    if cert.not_valid_before > now or cert.not_valid_after < now:
        print(f"[CERT] {role} certificate outside validity window.")
        print(f"       not_before={cert.not_valid_before}, not_after={cert.not_valid_after}")
        return False

    # Load CA and check issuer / signature
    ca_cert = _load_ca_cert(user_folder)
    if not ca_cert:
        print("[CERT] WARNING: No CA certificate loaded. Skipping chain validation.")

        return True

    if cert.issuer != ca_cert.subject:
        print("[CERT] Certificate issuer does not match local CA.")
        print(f"       cert.issuer={cert.issuer.rfc4514_string()}")
        print(f"       ca.subject={ca_cert.subject.rfc4514_string()}")
        return False

    # Verify signature using CA public key
    try:
        ca_pub = ca_cert.public_key()
        ca_pub.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            padding.PKCS1v15(),
            cert.signature_hash_algorithm,
        )
    except Exception as e:
        print(f"[CERT] Failed to verify {role} certificate signature against CA: {e}")
        return False

    print(f"[CERT] {role} certificate OK.")
    print(f"       subject={cert.subject.rfc4514_string()}")
    print(f"       serial={hex(cert.serial_number)}")

    return True


def handle_cert_request(event_data: dict, p2p_client, user_folder: Path):

    if not p2p_client or not user_folder:
        return

    data = event_data.get("data", {}) or {}
    auction_id = data.get("auction_id")
    seller_cert_pem = data.get("seller_cert")
    seller_id = event_data.get("sender")

    if not auction_id or not seller_cert_pem or not seller_id:
        print("[CERT] Invalid CERT_REQUEST payload.")
        return

    # Validate seller certificate
    if not validate_peer_certificate(seller_cert_pem, user_folder, role="seller"):
        print("[CERT] Seller certificate validation failed. Not responding.")
        return

    # Store seller certificate locally
    try:
        certs_dir = user_folder / "cert_exchange"
        certs_dir.mkdir(exist_ok=True)
        seller_cert_path = certs_dir / f"seller_cert_auction_{auction_id}.pem"
        seller_cert_path.write_text(seller_cert_pem)
        print(f"[CERT] Seller certificate stored at: {seller_cert_path}")
    except Exception as e:
        print(f"[CERT] Failed to store seller certificate: {e}")

    # Load this peer's (winner) certificate
    try:
        my_cert_path = user_folder / "client_cert.pem"
        my_cert_pem = my_cert_path.read_text()
    except Exception as e:
        print(f"[CERT] Could not read my certificate for CERT_RESPONSE: {e}")
        return

    # Send CERT_RESPONSE directly to seller
    print(f"[CERT] Sending CERT_RESPONSE back to seller '{seller_id}' ...")

    ok = p2p_client.send_direct(
        peer_id=seller_id,  # peer_id = username
        msg_type="CERT_RESPONSE",
        msg_data={
            "auction_id": auction_id,
            "buyer_cert": my_cert_pem,
        },
    )

    if not ok:
        print("[CERT] Failed to send CERT_RESPONSE.")
    else:
        print("[CERT] CERT_RESPONSE sent successfully.")


def handle_cert_response(event_data: dict, user_folder: Path):

    data = event_data.get("data", {}) or {}
    auction_id = data.get("auction_id")
    buyer_cert_pem = data.get("buyer_cert")
    winner_id = event_data.get("sender")

    if not auction_id or not buyer_cert_pem or not winner_id:
        print("[CERT] Invalid CERT_RESPONSE payload.")
        return

    # Validate winner (buyer) certificate
    if not validate_peer_certificate(buyer_cert_pem, user_folder, role="buyer"):
        print("[CERT] Buyer certificate validation failed.")
        return

    # Store winner certificate locally
    try:
        certs_dir = user_folder / "cert_exchange"
        certs_dir.mkdir(exist_ok=True)
        buyer_cert_path = certs_dir / f"winner_cert_auction_{auction_id}.pem"
        buyer_cert_path.write_text(buyer_cert_pem)
        print(f"[CERT] Winner certificate stored at: {buyer_cert_path}")
        print(f"[CERT] Winner username: {winner_id}")
    except Exception as e:
        print(f"[CERT] Failed to store winner certificate: {e}")
