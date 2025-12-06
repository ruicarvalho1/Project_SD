# Auction_Client/auction_display.py
import datetime

from Blockchain import blockchain_client
from .auction_utils import fetch_remote_auction_leader


def display_auction_header(auction_id, wallet_address, pseudonym_id):
    """
    Prints auction header information.

    - Reads current auction info (highest bid, close_date, etc.) from the blockchain.
    - Reads current leader pseudonym from the Peer_Server (via fetch_remote_auction_leader).
    """

    try:

        all_auctions = blockchain_client.get_all_auctions()
        target_auction = next(
            (a for a in all_auctions if str(a["id"]) == str(auction_id)),
            None,
        )

        if not target_auction or not target_auction.get("active"):
            print(" [INFO] Auction ended or does not exist.")
            return False

        now = datetime.datetime.now().timestamp()
        time_left = target_auction["close_date"] - now
        time_str = f"{int(time_left / 60)} min" if time_left > 0 else "ENDED"


        balance = blockchain_client.get_internal_balance(wallet_address)

        leader_pseudonym = fetch_remote_auction_leader(str(auction_id))
        if not leader_pseudonym:
            leader_pseudonym = "(unknown)"

        print("\n" + "=" * 60)
        print(f"         LIVE AUCTION ROOM #{auction_id}          ")
        print("=" * 60)
        print(f" ITEM:        {target_auction.get('description', 'N/A')}")
        print(f" CURRENT BID: {target_auction.get('highest_bid', 0)} ETH")
        print(f" HIGH BID:    {leader_pseudonym}")
        print(f" TIME LEFT:   {time_str}")
        print(f" BALANCE:     {balance} ETH")
        print("-" * 60)
        print(" Auto-refresh enabled | Type bid amount or 'EXIT' to leave")
        print("-" * 60)

        return True

    except Exception as e:
        print(f" [SYNC ERROR] {e}")
        return False
