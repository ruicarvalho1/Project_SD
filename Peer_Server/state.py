import time
import os
import json
import requests
from threading import Lock

# Peer tracking state (in-memory)
PEERS = {}
PEER_SIDS = {}
SID_PEERS = {}
TIMEOUT_SECONDS = 30
STATE_LOCK = Lock()

# Auction leaders (auction_id -> leader_pseudonym) stored on disk
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADER_FILE = os.path.join(BASE_DIR, "auction_leaders.json")
AUCTION_LEADERS = {}

# Pseudonym map file (auction_id:pseudonym -> peer_id)
MAP_FILE = os.path.join(BASE_DIR, "peer_pseudonym.json")

TRACKER = "http://127.0.0.1:5555"


# Load auction leaders from disk into AUCTION_LEADERS.
def load_auction_leaders():
    print(f"[TRACKER] Loading auction leaders from: {LEADER_FILE}")

    global AUCTION_LEADERS
    AUCTION_LEADERS.clear()

    if not os.path.exists(LEADER_FILE):
        print("[TRACKER] Leader file does not exist, using empty dict")
        return

    try:
        with open(LEADER_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                print("[TRACKER] Leader file empty, using empty dict")
                return
            data = json.loads(content)
            if isinstance(data, dict):
                AUCTION_LEADERS.update(data)
                print(f"[TRACKER] Loaded leaders: {AUCTION_LEADERS}")
            else:
                print("[TRACKER] Leader file is not a dict, ignoring.")
    except Exception as e:
        print(f"[TRACKER] Failed to load auction leaders: {e}")
        AUCTION_LEADERS.clear()


# Persist AUCTION_LEADERS to disk.
def save_auction_leaders():
    try:
        with open(LEADER_FILE, "w") as f:
            json.dump(AUCTION_LEADERS, f, indent=4)
    except Exception as e:
        print(f"[TRACKER] Failed to save auction leaders: {e}")


# Update the leader for an auction and save to disk.
def update_auction_leader(auction_id: str, pseudonym_id: str):
    global AUCTION_LEADERS
    auction_id = str(auction_id)
    with STATE_LOCK:
        AUCTION_LEADERS[auction_id] = {"leader_pseudonym": pseudonym_id}
        save_auction_leaders()
        print(f"[TRACKER] Auction {auction_id}: leader = {pseudonym_id}")


# Update last_seen timestamp for a peer.
def update_peer_heartbeat(peer_id: str):
    if peer_id in PEERS:
        PEERS[peer_id]["last_seen"] = time.time()


# Return list of active peers (not timed out).
def get_active_peers():
    now = time.time()
    return [
        {"peer_id": pid, "host": info["host"], "port": info["port"]}
        for pid, info in PEERS.items()
        if now - info["last_seen"] < TIMEOUT_SECONDS
    ]


# Load pseudonym map (auction_id:pseudonym -> peer_id) from disk.
def load_map() -> dict:
    if not os.path.exists(MAP_FILE):
        return {}

    try:
        with open(MAP_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return {}
            data = json.loads(content)
            if isinstance(data, dict):
                return data
            return {}
    except Exception as e:
        print(f"[TRACKER] Failed to load pseudonym map: {e}")
        return {}


# Persist pseudonym map to disk.
def save_map(data: dict) -> None:
    try:
        with open(MAP_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[TRACKER] Failed to save pseudonym map: {e}")


# Client helper: resolve (auction_id, pseudonym) to peer_id via /resolve.
def resolve_winner(auction_id, pseudonym):
    try:
        r = requests.post(
            TRACKER + "/resolve",
            json={
                "auction_id": auction_id,
                "pseudonym": pseudonym,
            },
            timeout=3,
        )
        if r.status_code != 200:
            print(f"[RESOLVE] Tracker /resolve returned {r.status_code}: {r.text}")
            return None

        data = r.json()
        return data.get("peer_id")
    except Exception as e:
        print(f"[RESOLVE] Error contacting tracker: {e}")
        return None


# Client helper: send a direct message to a single peer via /direct.
def direct_message(token, target_peer, message_type, message_body):
    try:
        requests.post(
            TRACKER + "/direct",
            json={
                "token": token,
                "peer_id": target_peer,
                "payload": {
                    "type": message_type,
                    "data": message_body,
                },
            },
            timeout=3,
        )
    except Exception as e:
        print(f"[DIRECT] Error sending direct message: {e}")
