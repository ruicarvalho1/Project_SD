
import json
import base64
import time
from datetime import datetime
from pathlib import Path

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
    user_folder: Path,
    username: str,
    auction_id: int,
    p2p_client,
    pseudonym_id=None,
    pseudonym_priv=None,
    delegation_token=None,
):
    """
    Live auction session.

    - Shows data about the auction in real time(blockchain + tracker).
    - The user can bid while the auction is live
    - When the auction ends, the winner is annouced (his pseudonym) to everyone that is in the room
    - The seller iniates the certificate swapping, to reveal his identity to the winner( via P2P)
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

    # Callback P2P to refresh when NEW_BID arrives
    try:
        if p2p_client is not None:
            p2p_client.set_refresh_callback(lambda *_: signal_refresh())
    except AttributeError:
        print("[WARNING] P2P client does not support refresh callbacks.")

    global NEEDS_REFRESH
    first_loop = True

    while True:
      
        # Reads the on-chain state to see if the auction is still on
        
        details = blockchain_client.get_auction_details(auction_id)
        if not details:
            print(" [INFO] Auction not found on-chain.")
            announce_auction_winner(auction_id, wallet_address, user_folder, p2p_client)
            break

        try:
            now_ts = blockchain_client.get_current_blockchain_timestamp()
        except RuntimeError:
            now_ts = int(time.time())

        close_date = details.get("close_date", 0)
        active = details.get("active", False)
        time_left = close_date - now_ts

    
        # Constructs the header (CURRENT BID, HIGH BID, TIME LEFT, BALANCE)
        
        if NEEDS_REFRESH or first_loop:
            if not display_auction_header(auction_id, wallet_address, pseudonym_id):
               
                announce_auction_winner(auction_id, wallet_address, user_folder, p2p_client)
                break
            NEEDS_REFRESH = False
            first_loop = False

       
        #  # If its over, the winner is announced and leaves the room
      
        if time_left <= 0 or not active:
            announce_auction_winner(auction_id, wallet_address, user_folder, p2p_client)
            break

        # Input with timeout (5 seconds) to allow auto-refresh
        bid_amount = input_with_timeout(
            " Enter bid amount ('R' refresh / 'EXIT' leave): ",
            timeout=5.0,
        )

        # Timeout: none input → forces refresh on the next cicle
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

        # Sends bid to blockchain ( with TSA timestamp) and broadcasts via P2P
       
        try:
            #  Message to the TSA
            msg_obj_for_tsa = {
                "auction_id": auction_id,
                "amount": bid_amount,
                "pseudonym_id": pseudonym_id,
            }
            msg_bytes_for_tsa = json.dumps(
                msg_obj_for_tsa, sort_keys=True
            ).encode("utf-8")

            # Requests Timestamp
            tsa_token = request_timestamp(msg_bytes_for_tsa)
            tsa_iso = tsa_token["timestamp"]          
            tsa_dt = datetime.fromisoformat(tsa_iso.replace("Z", "+00:00"))
            tsa_timestamp = int(tsa_dt.timestamp())   # changes to uint (unity used for time in the smart contracts)

            # Bid on-chain withtimestamp TSA so it breaks ties
            tx_hash = blockchain_client.place_bid_on_chain(
                account,
                auction_id,
                bid_amount,
                tsa_timestamp,
            )
            print(f" Bid accepted. Tx: {tx_hash}")

           
            signal_refresh()

            # Broadcasts NEW_BID via P2P 
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
                    print(f" [P2P WARNING] Failed to broadcast NEW_BID: {e}")

            time.sleep(0.5)

        except ValueError as e:
            print(f" Invalid bid or insufficient balance: {e}")
            time.sleep(2)
        except Exception as e:
            print(f" [CONTRACT ERROR] {e}")
            time.sleep(3)


def announce_auction_winner(
    auction_id: int,
    wallet_address: str,
    user_folder: Path,
    p2p_client,
):
    """
    Reads the final result blockchain + tracker and shows:
      - winning bid values
      - winner's pseudonym

   The seller
      - resolves (auction_id, pseudonym) → peer_id winner via tracker;
      - sends CERT_REQUEST to that peer (with his certificate).
    """
    details = blockchain_client.get_auction_details(auction_id)
    print("\n=== AUCTION ENDED ===")

    if not details:
        print(f"Auction #{auction_id} ended or not found on-chain.")
        print("======================")
        return

    highest_bid = details.get("highest_bid", 0)
    seller_addr = (details.get("seller") or "").lower()

    # Winner's Pseudonym (off-chain, saved in the Peer_Server)
    leader_pseudonym = fetch_remote_auction_leader(str(auction_id)) or "(unknown)"

    print(f"Auction #{auction_id} has finished.")
    if highest_bid == 0:
        print("No valid bids were placed. No winner.")
    else:
        print(f"Winning bid:       {highest_bid} ETH")
        print(f"Winning pseudonym: {leader_pseudonym}")
    print("======================")

    # Am i the seller? (Verifies that comparing the wallet's adress)
    i_am_seller = wallet_address.lower() == seller_addr

    if not i_am_seller:
        # Im just a bidder/watcher – i can only see the winner's pseudonym
        return

    # Im the seller - I need to resolve P2P + Pseudonym so i can start CERT_REQUEST
    if not p2p_client or leader_pseudonym in ("(unknown)", None, ""):
        print("[INFO] Cannot resolve winner peer (no P2P or unknown pseudonym).")
        return

    # Reads the certificate
    try:
        cert_path = user_folder / "client_cert.pem"
        seller_cert_pem = cert_path.read_text()
    except Exception as e:
        print(f"[ERROR] Could not read seller certificate: {e}")
        return

    # Resolves pseudonym → peer_id via tracker (/resolve)
    winner_peer_id = p2p_client.resolve_winner(auction_id, leader_pseudonym)
    if not winner_peer_id:
        print("[INFO] Could not resolve winner peer_id from tracker.")
        return

    print(f"[P2P] Winner peer_id resolved: {winner_peer_id}")
    print("[P2P] Sending CERT_REQUEST to winner...")

    # Sends CERT_REQUEST via /direct (only seller ↔ winner)
    ok = p2p_client.send_direct(
        peer_id=winner_peer_id,
        payload={
            "type": "CERT_REQUEST",
            "auction_id": auction_id,
            "seller_cert": seller_cert_pem,
        },
    )

    if not ok:
        print("[P2P] Failed to send CERT_REQUEST.")
    else:
        print("[P2P] CERT_REQUEST sent to winner.")
