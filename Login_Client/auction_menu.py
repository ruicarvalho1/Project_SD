import json
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from timestamp import request_timestamp

def auction_menu(user_folder, username):

    while True:
        print("\n=====================================")
        print("              AUCTION MENU           ")
        print("=====================================")
        print(f"Logged in as: {username}")
        print("-------------------------------------")
        print("1. View All Auctions")
        print("2. View My Auctions")
        print("3. Create New Auction")
        print("4. Make a Bid")
        print("5. Exit")
        print("-------------------------------------")

        choice = input("Choose an option: ").strip()

        match choice:
            case "1":
                view_all_auctions()

            case "2":
                view_my_auctions(username)

            case "3":
                create_auction(username)

            case "4":
                handle_bid(user_folder)

            case "5":
                print("Exiting...")
                return

            case _:
                print("Invalid option. Please try again.")

def view_all_auctions():
    print("Fazer função")

def view_my_auctions(username):
    print("Fazer função")
    
def create_auction(username):
    print("Fazer função")

# Melhorar esta função
def handle_bid(user_folder):
    
    print("\n=== Make a Bid ===")

    auction_id = input("Auction ID: ").strip()
    value = input("Bid Value: ").strip()


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
