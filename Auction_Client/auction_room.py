# Auction_Client/auction_room.py
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
    fetch_remote_auction_leader,
)

from Login_Client.timestamp import request_timestamp


def enter_auction_room(
    user_folder,
    auction_id,
    p2p_client,
    pseudonym_id=None,
    pseudonym_priv=None,
    delegation_token=None,
):
    """
    Live auction session.

    All peers (seller, bidders, observers) see the final winner
    when the auction ends (by time or explicit close).
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
            # When a NEW_BID arrives via P2P, trigger a refresh
            p2p_client.set_refresh_callback(lambda *_: signal_refresh())
    except AttributeError:
        print("[WARNING] P2P client does not support refresh callbacks.")

    global NEEDS_REFRESH
    first_loop = True

    while True:
        # 1) Read on-chain state to check if the auction has ended
        details = blockchain_client.get_auction_details(auction_id)
        if not details:
            print(" [INFO] Auction not found on-chain.")
            announce_auction_winner(auction_id)
            break

        try:
            now_ts = blockchain_client.get_current_blockchain_timestamp()
        except RuntimeError:
            now_ts = int(time.time())

        close_date = details.get("close_date", 0)
        active = details.get("active", False)
        time_left = close_date - now_ts

        # 2) Draw header (includes TIME LEFT based on on-chain state)
        if NEEDS_REFRESH or first_loop:
            # Always show the current header before possibly announcing the end
            if not display_auction_header(auction_id, wallet_address, pseudonym_id):
                # If False, something went wrong / auction is no longer available
                announce_auction_winner(auction_id)
                break
            NEEDS_REFRESH = False
            first_loop = False

        # 3) If the auction has ended, show the winner and leave the room
        if time_left <= 0 or not active:
            announce_auction_winner(auction_id)
            break

        # 4) Non-blocking input so the TIME LEFT can be updated periodically
        bid_amount = input_with_timeout(
            " Enter bid amount ('R' refresh / 'EXIT' leave): ",
            timeout=5.0,
        )

        # No input during timeout → force refresh on next loop
        if bid_amount is None:
            NEEDS_REFRESH = True
            continue

        bid_amount = bid_amount.strip().upper()
        if not bid_amount:
            continue

        if bid_amount == "EXIT":
            print(" Leaving auction room...")
            break
        elif bid_amount == "R":
            NEEDS_REFRESH = True
            continue
        elif not bid_amount.isdigit():
            print(" Invalid action. Enter a numeric value, 'R', or 'EXIT'.")
            time.sleep(1)
            continue

        # 5) Send bid on-chain (with TSA) and broadcast via P2P
        try:
            # 5.1) Canonical message for TSA
            msg_obj_for_tsa = {
                "auction_id": auction_id,
                "amount": bid_amount,
                "pseudonym_id": pseudonym_id,
            }
            msg_bytes_for_tsa = json.dumps(
                msg_obj_for_tsa, sort_keys=True
            ).encode("utf-8")

            tsa_token = request_timestamp(msg_bytes_for_tsa)
            tsa_iso = tsa_token["timestamp"]
            tsa_dt = datetime.fromisoformat(tsa_iso.replace("Z", "+00:00"))
            tsa_timestamp = int(tsa_dt.timestamp())

            # 5.2) Place bid on-chain with TSA timestamp for tie-breaking
            tx_hash = blockchain_client.place_bid_on_chain(
                account,
                auction_id,
                bid_amount,
                tsa_timestamp,
            )
            print(f" Bid accepted. Tx: {tx_hash}")

            # Force view refresh
            signal_refresh()

            # 5.3) Message for pseudonym signature (includes tx_hash)
            msg_obj = {
                "auction_id": auction_id,
                "amount": bid_amount,
                "tx_hash": str(tx_hash),
                "pseudonym_id": pseudonym_id,
            }
            msg_bytes = json.dumps(msg_obj, sort_keys=True).encode("utf-8")

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
                    print(f" [P2P WARNING] Failed to broadcast: {e}")

            time.sleep(0.5)

        except ValueError as e:
            print(f" Invalid bid or insufficient balance: {e}")
            time.sleep(2)
        except Exception as e:
            print(f" [CONTRACT ERROR] {e}")
            time.sleep(3)


def announce_auction_winner(auction_id):
    """
    Reads the final auction result from the blockchain and the remote tracker,
    then prints the winning pseudonym and winning bid.
    """
    details = blockchain_client.get_auction_details(auction_id)
    print("\n=== AUCTION ENDED ===")

    if not details:
        print(f"Auction #{auction_id} ended or not found on-chain.")
        print("======================")
        return

    highest_bid = details.get("highest_bid", 0)

    # Fetch winning pseudonym from the remote tracker (off-chain)
    leader_pseudonym = fetch_remote_auction_leader(str(auction_id)) or "(unknown)"

    print(f"Auction #{auction_id} has finished.")
    if highest_bid == 0:
        print("No valid bids were placed. No winner.")
    else:
        print(f"Winning bid:       {highest_bid} ETH")
        print(f"Winning pseudonym: {leader_pseudonym}")
    print("======================")
