import json
from pathlib import Path
import os
import base64
import requests
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

# ----------------------------------------------------------------------
# Global refresh flag used by the auction room
# ----------------------------------------------------------------------
NEEDS_REFRESH = False


def signal_refresh() -> None:
    """Mark that the auction room should refresh its view."""
    global NEEDS_REFRESH
    NEEDS_REFRESH = True


# ----------------------------------------------------------------------
# Tracker HTTP base URL (Peer_Server)
# ----------------------------------------------------------------------
TRACKER_HTTP_URL = "http://127.0.0.1:5555"


def fetch_remote_auction_leader(auction_id: str) -> Optional[str]:
    """
    Ask the Peer_Server who is the current leader pseudonym for this auction.

    Returns:
        pseudonym_id (str) if known, or None otherwise.
    """
    try:
        resp = requests.get(
            f"{TRACKER_HTTP_URL}/auction_leader/{auction_id}",
            timeout=2,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("leader_pseudonym")
    except Exception as e:
        print(f" [WARN] Failed to fetch remote leader: {e}")
    return None


# ==============================================================================
# 1. PSEUDONYM CACHE (PRIVATE & ENCRYPTED PER USER)
# ==============================================================================

PSEUDONYM_CACHE: dict[str, dict] = {}
CACHE_FILE_NAME = "pseudonym_cache.json"


def get_cache_path(user_folder: Path) -> Path:
    return user_folder / CACHE_FILE_NAME


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a symmetric key from a password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend(),
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_data(password: str, data: bytes) -> tuple[bytes, bytes]:
    """Encrypt data using a key derived from the given password."""
    salt = os.urandom(16)
    key = derive_key(password, salt)
    f = Fernet(key)
    return f.encrypt(data), salt


def decrypt_data(password: str, encrypted_data: bytes, salt: bytes) -> bytes:
    """Decrypt data using a key derived from the given password."""
    key = derive_key(password, salt)
    f = Fernet(key)
    return f.decrypt(encrypted_data)


def load_pseudonym_cache(user_folder: Path) -> None:
    """
    Load the encrypted pseudonym cache for the current user.

    IMPORTANT: we do NOT rebind PSEUDONYM_CACHE, we only clear() + update()
    so that modules that imported it keep seeing the updated contents.
    """
    global PSEUDONYM_CACHE
    cache_file = get_cache_path(user_folder)

    PSEUDONYM_CACHE.clear()

    if cache_file.exists():
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    PSEUDONYM_CACHE.update(data)
        except Exception:
            PSEUDONYM_CACHE.clear()


def save_pseudonym_cache(user_folder: Path) -> None:
    """Persist the pseudonym cache for the current user."""
    cache_file = get_cache_path(user_folder)
    try:
        with open(cache_file, "w") as f:
            json.dump(PSEUDONYM_CACHE, f, indent=4)
    except Exception as e:
        print(f" [CRITICAL] Failed to save pseudonym cache: {e}")


# ==============================================================================
# 2. PUBLIC BIDDER MAP (WALLET ADDRESS -> PSEUDONYM ID)
# ==============================================================================

BIDDER_PSEUDONYM_MAP: dict[str, str] = {}  # wallet_address (lowercase) -> pseudonym_id
MAP_FILE_NAME = "bidder_map.json"


def get_bidder_map_path(user_folder: Path) -> Path:
    return user_folder / MAP_FILE_NAME


def load_bidder_map(user_folder: Path) -> None:
    """Load the public mapping from wallet addresses to pseudonym IDs."""
    global BIDDER_PSEUDONYM_MAP
    path = get_bidder_map_path(user_folder)
    BIDDER_PSEUDONYM_MAP.clear()

    if path.exists():
        try:
            with open(path, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    BIDDER_PSEUDONYM_MAP.update(data)
        except Exception:
            BIDDER_PSEUDONYM_MAP.clear()


def save_bidder_map(user_folder: Path) -> None:
    """Persist the public mapping from wallet addresses to pseudonym IDs."""
    path = get_bidder_map_path(user_folder)
    try:
        with open(path, "w") as f:
            json.dump(BIDDER_PSEUDONYM_MAP, f, indent=4)
    except Exception as e:
        print(f" [ERROR] Failed to save bidder map: {e}")


def update_bidder_map(user_folder: Path, wallet_address: str, pseudo_id: str) -> None:
    """
    Associate a wallet address with a pseudonym ID.
    This is called when a new bid is observed over P2P.
    """
    global BIDDER_PSEUDONYM_MAP

    wallet_address = wallet_address.lower()
    if (
        wallet_address not in BIDDER_PSEUDONYM_MAP
        or BIDDER_PSEUDONYM_MAP[wallet_address] != pseudo_id
    ):
        BIDDER_PSEUDONYM_MAP[wallet_address] = pseudo_id
        save_bidder_map(user_folder)

