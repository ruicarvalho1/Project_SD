# auction_room.py
import json
import base64
import time

from Blockchain import blockchain_client
from Login_Client.identity.wallet_manager import load_wallet

from .auction_input import input_with_timeout
from .auction_display import display_auction_header
from .auction_utils import (
    signal_refresh,
    NEEDS_REFRESH,
)


def enter_auction_room(
    user_folder,
    username,
    auction_id,
    p2p_client,
    pseudonym_id=None,
    pseudonym_priv=None,
    delegation_token=None,
):
    """
    Live auction session.

    - Shows real-time auction information.
    - Allows the user to place bids.
    - Ends when the user types 'EXIT'.
    """
    print("\n [SETUP] Wallet unlock required.")
    password = input(" Wallet Password: ").strip()

    try:
        account = load_wallet(user_folder, password)
        print(" Wallet unlocked. Ready to bid.")
    except Exception:
        print(" Invalid password. Returning to menu.")
        return

    wallet_address = account.address

    # Register refresh callback with the P2P client (if supported)
    try:
        if p2p_client is not None:
            p2p_client.set_refresh_callback(signal_refresh)
    except AttributeError:
        print("[WARNING] P2P client does not support refresh callbacks.")

    global NEEDS_REFRESH

    while True:
        # Auto-refresh triggered by P2P events
        if NEEDS_REFRESH:
            print("\n" + "=" * 60)
            print(" Sync event detected. Reloading auction data...")
            NEEDS_REFRESH = False
            time.sleep(0.1)
            continue

        # Draw auction header (includes HIGH BID from Peer_Server)
        if not display_auction_header(auction_id, wallet_address, pseudonym_id):
            # Auction ended or error fetching state
            break

        # Non-blocking input (timeout so UI can be refreshed)
        bid_amount = input_with_timeout(
            " Enter bid amount ('R' refresh / 'EXIT' leave): ",
            timeout=4.0,
        )

        # Timeout returns None (no user input)
        if bid_amount is None:
            if NEEDS_REFRESH:
                print(" New bid detected. Refreshing...")
            continue

        bid_amount = bid_amount.strip().upper()

        if bid_amount == "EXIT":
            print(" Leaving auction room...")
            break
        elif bid_amount == "R":
            # Explicit refresh request
            continue
        elif not bid_amount.isdigit():
            print("Invalid action. Enter a numeric value, 'R', or 'EXIT'.")
            continue

        # Submit bid on-chain and broadcast the event via P2P
        try:
            tx_hash = blockchain_client.place_bid_on_chain(
                account,
                auction_id,
                bid_amount,
            )
            print(f" Bid accepted. Tx: {tx_hash}")

            # Trigger a refresh on the next loop
            signal_refresh()

            # Prepare message for pseudonym signature
            msg_obj = {
                "auction_id": auction_id,
                "amount": bid_amount,
                "tx_hash": str(tx_hash),
                "pseudonym_id": pseudonym_id,
            }
            msg_bytes = json.dumps(msg_obj, sort_keys=True).encode("utf-8")

            # Sign the message with the pseudonym private key
            if pseudonym_priv is not None:
                pseudo_sig_b64 = base64.b64encode(
                    pseudonym_priv.sign(msg_bytes)
                ).decode("utf-8")
            else:

                pseudo_sig_b64 = ""

            payload = {
                **msg_obj,
                "pseudonym_signature": pseudo_sig_b64,
                "delegation_token": delegation_token,
            }

            if p2p_client is not None:
                try:
                    p2p_client.broadcast_event("NEW_BID", payload)
                except Exception as e:
                    print(f" [P2P WARNING] Failed to broadcast NEW_BID: {e}")

            time.sleep(1)

        except ValueError as e:
            print(f" Invalid bid or insufficient balance: {e}")
            time.sleep(2)
        except Exception as e:
            print(f" [CONTRACT ERROR] {e}")
            time.sleep(3)