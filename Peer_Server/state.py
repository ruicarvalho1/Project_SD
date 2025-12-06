# state.py
import time
import os
import json
from threading import Lock

# Peers
PEERS = {}
PEER_SIDS = {}
SID_PEERS = {}
TIMEOUT_SECONDS = 30
STATE_LOCK = Lock()

# Leaders (auction_id -> leader_pseudonym)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADER_FILE = os.path.join(BASE_DIR, "auction_leaders.json")
AUCTION_LEADERS = {}


def load_auction_leaders():
    global AUCTION_LEADERS
    if not os.path.exists(LEADER_FILE):
        AUCTION_LEADERS = {}
        return
    try:
        with open(LEADER_FILE, "r") as f:
            AUCTION_LEADERS = json.load(f)
    except Exception as e:
        print(f"[TRACKER] Failed to load auction leaders: {e}")
        AUCTION_LEADERS = {}


def save_auction_leaders():
    try:
        with open(LEADER_FILE, "w") as f:
            json.dump(AUCTION_LEADERS, f, indent=4)
    except Exception as e:
        print(f"[TRACKER] Failed to save auction leaders: {e}")


def update_auction_leader(auction_id: str, pseudonym_id: str):
    global AUCTION_LEADERS
    auction_id = str(auction_id)
    with STATE_LOCK:
        AUCTION_LEADERS[auction_id] = {"leader_pseudonym": pseudonym_id}
        save_auction_leaders()
        print(f"[TRACKER] Auction {auction_id}: leader = {pseudonym_id}")


def update_peer_heartbeat(peer_id: str):
    if peer_id in PEERS:
        PEERS[peer_id]["last_seen"] = time.time()


def get_active_peers():
    now = time.time()
    return [
        {"peer_id": pid, "host": info["host"], "port": info["port"]}
        for pid, info in PEERS.items()
        if now - info["last_seen"] < TIMEOUT_SECONDS
    ]
