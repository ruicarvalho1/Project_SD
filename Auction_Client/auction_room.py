import json
import base64
import time
from datetime import datetime, timezone

from Blockchain import blockchain_client
from Login_Client.identity.wallet_manager import load_wallet

from .auction_input import input_with_timeout
from .auction_display import display_auction_header
from .auction_utils import (
    signal_refresh,
    NEEDS_REFRESH,
)

from Login_Client.timestamp import request_timestamp


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
            # When a NEW_BID arrives from any peer → trigger a refresh
            p2p_client.set_refresh_callback(lambda *_: signal_refresh())
    except AttributeError:
        print("[WARNING] P2P client does not support refresh callbacks.")

    global NEEDS_REFRESH
    first_loop = True

    while True:
        # Redraw header:
        # - on first iteration
        # - whenever a refresh was signaled
        if NEEDS_REFRESH or first_loop:
            if not display_auction_header(auction_id, wallet_address, pseudonym_id):
                # Auction ended or error fetching state
                break
            NEEDS_REFRESH = False
            first_loop = False

        bid_amount = input_with_timeout(
            " Enter bid amount ('R' refresh / 'EXIT' leave): ",
            timeout=1.0,
        )

        # Timeout: no user input during the timeout period
        if bid_amount is None:
            # Force redraw on next loop (updates TIME LEFT and CURRENT BID)
            NEEDS_REFRESH = True
            continue

        bid_amount = bid_amount.strip().upper()

        # Ignore empty ENTER (no action)
        if not bid_amount:
            continue

        if bid_amount == "EXIT":
            print(" Leaving auction room...")
            break
        elif bid_amount == "R":
            # Explicit refresh
            NEEDS_REFRESH = True
            continue
        elif not bid_amount.isdigit():
            print("Invalid action. Enter a numeric value, 'R', or 'EXIT'.")
            time.sleep(1)
            continue

        # Submit bid on-chain and broadcast the event via P2P
        try:
            # 1) Build canonical message for TSA / pseudonym
            msg_obj_for_tsa = {
                "auction_id": auction_id,
                "amount": bid_amount,
                "pseudonym_id": pseudonym_id,
            }
            msg_bytes_for_tsa = json.dumps(
                msg_obj_for_tsa, sort_keys=True
            ).encode("utf-8")

            # 2) Request timestamp from TSA (token with "timestamp" in ISO)
            tsa_token = request_timestamp(msg_bytes_for_tsa)

            tsa_iso = tsa_token["timestamp"]
            tsa_dt = datetime.fromisoformat(tsa_iso.replace("Z", "+00:00"))
            tsa_timestamp = int(tsa_dt.timestamp())

            # 3) Send bid to blockchain with TSA timestamp for tie-breaking
            tx_hash = blockchain_client.place_bid_on_chain(
                account,
                auction_id,
                bid_amount,
                tsa_timestamp,
            )
            print(f" Bid accepted. Tx: {tx_hash}")

            # 4) Mark local refresh (will redraw header on next loop)
            signal_refresh()

            # 5) Prepare message for pseudonym signature (includes tx_hash)
            msg_obj = {
                "auction_id": auction_id,
                "amount": bid_amount,
                "tx_hash": str(tx_hash),
                "pseudonym_id": pseudonym_id,
            }
            msg_bytes = json.dumps(msg_obj, sort_keys=True).encode("utf-8")

            # Sign with the pseudonym private key
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
                "tsa_token": tsa_token,
            }

            if p2p_client is not None:
                try:
                    p2p_client.broadcast_event("NEW_BID", payload)
                except Exception as e:
                    print(f" [P2P WARNING] Failed to broadcast NEW_BID: {e}")

            time.sleep(0.5)

        except ValueError as e:
            print(f" Invalid bid or insufficient balance: {e}")
            time.sleep(2)
        except Exception as e:
            print(f" [CONTRACT ERROR] {e}")
            time.sleep(3)
