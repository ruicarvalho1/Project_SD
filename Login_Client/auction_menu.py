from Blockchain import blockchain_client  # Assumes transaction functions are here
import datetime
from Login_Client.identity.wallet_manager import load_wallet

def auction_menu(user_folder, username):
    while True:
        print("\n=====================================")
        print("              AUCTION MENU           ")
        print("=====================================")
        print(f"User: {username}")

        try:

            addr = (user_folder / "wallet_address.txt").read_text().strip()

            token_bal = blockchain_client.get_internal_balance(addr)

            print(f"Wallet: {addr}")
            print(f"Tokens: {token_bal} ETH")
        except:
            print("Wallet info unavailable")

        print("-------------------------------------")
        print("1. View All Auctions (Anonymous)")
        print("2. Create New Auction")
        print("3. Make a Bid")
        print("4. Exit")
        print("-------------------------------------")

        choice = input("Option: ").strip()

        if choice == "1":
            view_all_auctions()
        elif choice == "2":
            create_auction(user_folder, username)
        elif choice == "3":
            handle_bid(user_folder, username)
        elif choice == "4":
            return
        else:
            print("Invalid.")


def view_all_auctions():
    print("\n--- ACTIVE AUCTIONS ---")
    try:
        auctions = blockchain_client.get_all_auctions()
        if not auctions:
            print(" [INFO] No auctions found.")
            return

        print(f"{'ID':<4} | {'Item':<20} | {'Current Bid':<12} | {'Time Left'}")
        print("-" * 60)

        now = datetime.datetime.now().timestamp()

        for auc in auctions:
            if not auc['active']: continue

            time_left = auc['close_date'] - now
            time_str = f"{int(time_left / 60)} min" if time_left > 0 else "ENDED"

            print(f"{auc['id']:<4} | {auc['description']:<20} | {auc['highest_bid']:<12} | {time_str}")

    except Exception as e:
        print(f"Error: {e}")


def create_auction(user_folder, username):
    print("\n=== CREATE AUCTION ===")

    desc = input("Item Description: ").strip()
    duration = input("Duration (minutes): ").strip()
    min_bid = input("Min Bid (Tokens): ").strip()

    if not desc or not duration or not min_bid: return

    print("\n[SECURITY] Enter wallet password to pay Gas fees.")
    password = input("Password: ").strip()

    try:

        account = load_wallet(user_folder, password)
        print(" [Unlocked] Key decrypted.")

        print(" -> Sending to Blockchain...")
        tx = blockchain_client.create_auction(account, desc, duration, min_bid)
        print(f" [SUCCESS] Auction created anonymously! Tx: {tx}")

    except ValueError as e:
        print(f" [ERROR] Password: {e}")
    except Exception as e:
        print(f" [ERROR] Blockchain: {e}")


def handle_bid(user_folder, username):
    print("\n=== MAKE A BID ===")
    auction_id = input("Auction ID: ").strip()
    amount = input("Bid Amount (Tokens): ").strip()

    if not auction_id or not amount: return

    print("\n[SECURITY] Enter wallet password to sign transaction.")
    password = input("Password: ").strip()

    try:
        account = load_wallet(user_folder, password)
        print(" [Unlocked] Signing...")

        tx_hash = blockchain_client.place_bid_on_chain(account, auction_id, amount)
        print(f" [SUCCESS] Bid recorded! Tx Hash: {tx_hash}")

    except ValueError as e:
        print(f" [SECURITY ERROR] {e}")
    except Exception as e:
        print(f" [CONTRACT ERROR] {e}")