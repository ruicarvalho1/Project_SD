import json
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from timestamp import request_timestamp


def handle_bid(user_folder):
    auction_id = input("Auction ID: ").strip()
    value = input("Enter your bid value: ").strip()

    # 1. Build bid object
    bid = {
        "auction_id": auction_id,
        "bid_value": value,
    }

    # 2. JSON bytes
    bid_bytes = json.dumps(bid, sort_keys=True).encode()

    # 3. TSA timestamp request
    tsa_token = request_timestamp(bid_bytes)

    # 4. Load private key
    private_key_path = user_folder / "client_private_key.pem"
    private_key = serialization.load_pem_private_key(
        private_key_path.read_bytes(),
        password=None
    )

    # 5. Sign the bid
    signature = private_key.sign(
        bid_bytes,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    signature_b64 = base64.b64encode(signature).decode()

    # 6. Load certificate
    cert_pem = (user_folder / "client_cert.pem").read_text()

    # 7. FINAL BID MESSAGE
    final_bid_message = {
        "bid": bid,
        "signature_b64": signature_b64,
        "certificate_pem": cert_pem,
        "timestamp_token": tsa_token
    }

    # For now, just display the signed + timestamped bid
    print("\n=== FINAL BID MESSAGE ===")
    print(json.dumps(final_bid_message, indent=2))
