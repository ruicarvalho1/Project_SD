from Blockchain import blockchain_client
from Login_Client.identity.wallet_manager import load_wallet
from .auction_room import enter_auction_room
from .auction_utils import broadcast_to_peers
from .auction_display import display_auction_header
from .auction_input import input_with_timeout
import datetime

def auction_menu(user_folder, username, p2p_client):
    while True:
        print("\n=====================================")
        print("              AUCTION MENU           ")
        print("=====================================")
        print(f"User: {username}")

        try:
            addr = (user_folder / "wallet_address.txt").read_text().strip()
            balance = blockchain_client.get_internal_balance(addr)
            print(f"Wallet: {addr}")
            print(f"Balance: {balance} ETH")
        except Exception:
            pass

        print("-------------------------------------")
        print("1. Join Live Auction (Room Mode)")
        print("2. Create New Auction")
        print("3. Exit")
        print("-------------------------------------")

        choice = input("Option: ").strip().upper()

        if choice == "1":
            select_and_enter_room(user_folder, username, p2p_client)
        elif choice == "2":
            create_auction(user_folder, username, p2p_client)
        elif choice == "3":
            return
        else:
            print("Invalid option.")


def select_and_enter_room(user_folder, username, p2p_client):
    print("\n--- LOADING AUCTIONS ---")
    try:
        auctions = blockchain_client.get_all_auctions()
        if not auctions:
            print(" No active auctions.")
            input("Press Enter to return...")
            return

        print(f"{'ID':<4} | {'Item':<20} | {'Highest Bid':<12} | {'Time Left'}")
        print("-" * 60)

        now = datetime.datetime.now().timestamp()
        for auc in auctions:
            if not auc["active"]:
                continue

            time_left = auc["close_date"] - now
            time_str = f"{int(time_left / 60)} min" if time_left > 0 else "ENDED"

            print(
                f"{auc['id']:<4} | {auc['description']:<20} | "
                f"{auc['highest_bid']:<12} | {time_str}"
            )

        print("-" * 60)
        auction_id = input("Enter auction ID to join (or 'B' to return): ").strip()

        if auction_id.upper() == "B":
            return

        enter_auction_room(user_folder, username, auction_id, p2p_client)

    except Exception as e:
        print(f" [ERROR] {e}")


def create_auction(user_folder, username, p2p_client):
    print("\n=== CREATE AUCTION ===")

    desc = input("Item Description: ").strip()
    duration = input("Duration (minutes): ").strip()
    min_bid = input("Min Bid (Tokens): ").strip()

    if not desc or not duration or not min_bid:
        return

    password = input("Wallet Password: ").strip()

    try:
        account = load_wallet(user_folder, password)
        print(" Sending transaction...")
        tx = blockchain_client.create_auction(account, desc, duration, min_bid)
        print(f" Auction created. Tx: {tx}")

        payload = {
            "description": desc,
            "min_bid": min_bid,
            "tx_hash": str(tx)
        }
        broadcast_to_peers("NEW_AUCTION", payload, exclude_user=username)

    except Exception as e:
        print(f" [ERROR] {e}")

    input("Press Enter to return...")
