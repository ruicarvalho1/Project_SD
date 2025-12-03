import time
from Blockchain import blockchain_client
from Login_Client.identity.wallet_manager import load_wallet
from .auction_input import input_with_timeout
from .auction_display import display_auction_header
from .auction_utils import broadcast_to_peers, signal_refresh, NEEDS_REFRESH


def enter_auction_room(user_folder, username, auction_id, p2p_client):
    """
    Live auction session.
    Shows real-time updates and allows instant bidding.
    Ends when the user types 'EXIT'.
    """
    print("\n Wallet unlock required to join and bid.")
    password = input(" Wallet Password: ").strip()

    try:
        account = load_wallet(user_folder, password)
        print(" Wallet unlocked. Ready to bid.")
    except Exception:
        print(" Invalid password. Returning to menu.")
        return

    wallet_address = account.address

    try:
        # Register callback so P2P events trigger a refresh
        p2p_client.set_refresh_callback(signal_refresh)
    except AttributeError:
        print("[WARNING] P2P client missing set_refresh_callback")

    global NEEDS_REFRESH

    while True:

        # Auto-refresh on P2P event
        if NEEDS_REFRESH:
            print("\n" + "=" * 60)
            print(" Sync event detected. Reloading auction data...")
            NEEDS_REFRESH = False
            time.sleep(0.1)
            continue

        # Draw header UI
        if not display_auction_header(auction_id, wallet_address):
            break

        # Non-blocking input (timeout ensures UI keeps updating)
        bid_amount = input_with_timeout(
            " Enter bid ('R' refresh / 'EXIT' leave): ",
            timeout=4.0
        )

        # Timeout returns None
        if bid_amount is None:
            continue

        bid_amount = bid_amount.strip().upper()

        if bid_amount == "E" or bid_amount == "E":
            print(" Leaving auction room...")
            break
        elif bid_amount == "R":
            continue
        elif not bid_amount.isdigit():
            print("Invalid action. Enter a numeric value, 'R', or 'E(exit)'.")
            continue

        # Submit bid and broadcast event
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
            print(f" Invalid bid: {e}")
            time.sleep(2)
        except Exception as e:
            print(f" Contract error: {e}")
            time.sleep(3)
