import time
from Blockchain import blockchain_client
from Login_Client.identity.wallet_manager import load_wallet
from .auction_input import input_with_timeout
from .auction_display import display_auction_header
from .auction_utils import broadcast_to_peers, signal_refresh, NEEDS_REFRESH


def enter_auction_room(user_folder, username, auction_id, p2p_client):
    print("\n Wallet unlock required.")
    password = input(" Wallet Password: ").strip()

    try:
        account = load_wallet(user_folder, password)
        print(" Wallet unlocked.")
    except Exception:
        print(" Invalid password.")
        return

    try:
        p2p_client.set_refresh_callback(signal_refresh)
    except AttributeError:
        print("[WARNING] P2P client does not support refresh callbacks.")

    global NEEDS_REFRESH

    while True:
        if not display_auction_header(auction_id):
            break

        NEEDS_REFRESH = False

        bid_amount = input_with_timeout(
            " Enter bid amount ('R' refresh / 'EXIT' leave): ",
            timeout=4.0
        )

        if bid_amount is None:
            if NEEDS_REFRESH:
                print(" New bid detected. Refreshing...")
            continue

        bid_amount = bid_amount.strip().upper()

        if bid_amount == "EXIT":
            print(" Leaving auction room...")
            break
        elif bid_amount == "R":
            continue
        elif not bid_amount:
            continue

        try:
            tx_hash = blockchain_client.place_bid_on_chain(
                account, auction_id, bid_amount
            )
            print(f" Bid accepted. Tx: {tx_hash}")

            payload = {
                "auction_id": auction_id,
                "amount": bid_amount,
                "tx_hash": str(tx_hash)
            }
            broadcast_to_peers("NEW_BID", payload, exclude_user=username)
            time.sleep(1)

        except ValueError as e:
            print(f" Invalid bid or insufficient balance: {e}")
            time.sleep(2)
        except Exception as e:
            print(f" [CONTRACT ERROR] {e}")
            time.sleep(3)
