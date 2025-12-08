import time
import os
import json
import requests
from threading import Lock

# -------------------------------------------------------------------
# Peers
# -------------------------------------------------------------------
PEERS = {}
PEER_SIDS = {}
SID_PEERS = {}
TIMEOUT_SECONDS = 30
STATE_LOCK = Lock()

# -------------------------------------------------------------------
# Leaders (auction_id -> leader_pseudonym)
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEADER_FILE = os.path.join(BASE_DIR, "auction_leaders.json")
AUCTION_LEADERS = {}

# Map of pseudonyms (auction_id:pseudonym -> peer_id)
MAP_FILE = os.path.join(BASE_DIR, "peer_pseudonym.json")

TRACKER = "http://127.0.0.1:5555"


# ===================== LEADERS =====================

def load_auction_leaders():
    """Load the auction leaders dictionary from disk into AUCTION_LEADERS."""
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


def save_auction_leaders():
    """Persist the auction leaders dictionary (AUCTION_LEADERS) to disk."""
    try:
        with open(LEADER_FILE, "w") as f:
            json.dump(AUCTION_LEADERS, f, indent=4)
    except Exception as e:
        print(f"[TRACKER] Failed to save auction leaders: {e}")


def update_auction_leader(auction_id: str, pseudonym_id: str):
    """
    Update the leader for a given auction and persist the change to disk.

    :param auction_id: ID of the auction
    :param pseudonym_id: pseudonym of the leader for this auction
    """
    global AUCTION_LEADERS
    auction_id = str(auction_id)
    with STATE_LOCK:
        AUCTION_LEADERS[auction_id] = {"leader_pseudonym": pseudonym_id}
        save_auction_leaders()
        print(f"[TRACKER] Auction {auction_id}: leader = {pseudonym_id}")


# ===================== PEERS / HEARTBEAT =====================

def update_peer_heartbeat(peer_id: str):
    """Update last_seen timestamp for a peer."""
    if peer_id in PEERS:
        PEERS[peer_id]["last_seen"] = time.time()


def get_active_peers():
    """Return a list of peers that are active (not timed out)."""
    now = time.time()
    return [
        {"peer_id": pid, "host": info["host"], "port": info["port"]}
        for pid, info in PEERS.items()
        if now - info["last_seen"] < TIMEOUT_SECONDS
    ]


# ===================== PSEUDONYM MAP =====================

def load_map() -> dict:
    """
    Load the pseudonym map (auction_id:pseudonym -> peer_id) from disk.

    If the file does not exist, is empty, or is invalid,
    this function always returns an empty dict instead of raising.
    """
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


def save_map(data: dict) -> None:
    """Persist the pseudonym map (auction_id:pseudonym -> peer_id) to disk."""
    try:
        with open(MAP_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[TRACKER] Failed to save pseudonym map: {e}")


# ===================== CLIENT-SIDE HELPERS =====================

def resolve_winner(auction_id, pseudonym):
    """
    Client helper: ask the tracker (HTTP) which peer_id corresponds to
    a given pseudonym in a given auction.

    Uses the /resolve endpoint (no seller_id).
    """
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


def direct_message(token, target_peer, message_type, message_body):
    """
    Client helper: send a private message to a single peer via /direct.
    """
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
