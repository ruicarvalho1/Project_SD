
import base64
import json
from datetime import datetime, timezone
from pathlib import Path

from Blockchain import blockchain_client
from Login_Client.identity.wallet_manager import load_wallet
from cryptography.hazmat.primitives import serialization
from cryptography.x509 import load_pem_x509_certificate

from .auction_room import enter_auction_room
from .auction_utils import (
    encrypt_data,
    decrypt_data,
    save_pseudonym_cache,
    load_pseudonym_cache,
    PSEUDONYM_CACHE,
)
from .pseudonyms import (
    generate_pseudonym,
    generate_pseudonym_keypair,
    build_pseudonym_token,
)


def global_notification_handler(event_data=None):
   
    if event_data:
        msg_type = event_data.get("type")
        details = event_data.get("data", {})

        if msg_type == "NEW_BID":
            print(
                f"\n [P2P] New bid of {details.get('amount')} ETH "
                f"in Auction #{details.get('auction_id')}"
            )
        elif msg_type == "NEW_AUCTION":
            print(
                f"\n [P2P] New auction created: "
                f"{details.get('description')} (min {details.get('min_bid')} ETH)"
            )
        else:
            print("\n [P2P] Network activity detected.")
    else:
        print("\n [P2P] Network activity detected.")

    print("Option: ", end="", flush=True)


def auction_menu(user_folder: Path, username: str, p2p_client):
    """Main auction menu loop."""

    # Callback for broadcast (NEW_BID, NEW_AUCTION, ...)
    if p2p_client is not None:
        try:
            p2p_client.set_refresh_callback(global_notification_handler)
        except Exception:
            pass

        # 2) Handles direct messages (CERT_REQUEST / CERT_RESPONSE)
        def direct_handler(msg):
            sender = msg.get("sender")
            payload = (msg.get("payload") or {})
            ptype = payload.get("type")

            # Folder to hold the received certificates
            exchanged_dir = user_folder / "exchanged_certs"
            exchanged_dir.mkdir(exist_ok=True)

            if ptype == "CERT_REQUEST":
                auction_id = payload.get("auction_id")
                seller_cert_pem = payload.get("seller_cert", "")

                # Saves seller's certificate
                if auction_id is not None and seller_cert_pem:
                    path = exchanged_dir / f"auction_{auction_id}_seller_cert.pem"
                    path.write_text(seller_cert_pem)
                    print(f"\n[P2P] Received seller certificate for auction #{auction_id} from {sender}")

                # Send to the seller the winner's certificate
                try:
                    my_cert_path = user_folder / "client_cert.pem"
                    my_cert_pem = my_cert_path.read_text()
                    if p2p_client is not None:
                        p2p_client.send_direct(
                            peer_id=sender,
                            payload={
                                "type": "CERT_RESPONSE",
                                "auction_id": auction_id,
                                "winner_cert": my_cert_pem,
                            },
                        )
                        print("[P2P] Sent my certificate back to seller.")
                except Exception as e:
                    print(f"[P2P] Failed to send CERT_RESPONSE: {e}")

                print("Option: ", end="", flush=True)

            elif ptype == "CERT_RESPONSE":
                auction_id = payload.get("auction_id")
                winner_cert_pem = payload.get("winner_cert", "")

                if auction_id is not None and winner_cert_pem:
                    path = exchanged_dir / f"auction_{auction_id}_winner_cert.pem"
                    path.write_text(winner_cert_pem)
                    print(f"\n[P2P] Received winner certificate for auction #{auction_id} from {sender}")

                print("Option: ", end="", flush=True)

            else:
                
                print(f"\n[P2P] Direct message from {sender}: {payload}")
                print("Option: ", end="", flush=True)

        try:
            p2p_client.set_direct_handler(direct_handler)
        except Exception:
            pass

    # 
    # Main Menu
    # 
    while True:
        print("\n=====================================")
        print("              AUCTION MENU           ")
        print("=====================================")
        print(f"User: {username}")

        try:
            addr = (user_folder / "wallet_address.txt").read_text().strip()
            balance = blockchain_client.get_internal_balance(addr)
            print(f"Wallet:  {addr}")
            print(f"Balance: {balance} ETH")
        except Exception:
            pass

        print("-------------------------------------")
        print("1. Join Live Auction (Room Mode)")
        print("2. Create New Auction")
        print("3. Exit")
        print("-------------------------------------")

        choice = input("Option: ").strip().upper()

        if choice == "1":
            select_and_enter_room(user_folder, username, p2p_client)
        elif choice == "2":
            create_auction(user_folder, username, p2p_client)
        elif choice == "3":
            return
        else:
            print("Invalid option.")


def select_and_enter_room(user_folder: Path, username: str, p2p_client):
    """Select an auction from the blockchain and enter the live auction room."""
    print("\n--- LOADING AUCTIONS ---")
    try:
        auctions = blockchain_client.get_all_auctions()
        if not auctions:
            print(" No active auctions.")
            input("Press Enter to return...")
            return

        print(f"{'ID':<4} | {'Item':<20} | {'Highest Bid':<12} | {'Time Left'}")
        print("-" * 60)

        # Use blockchain time if available, otherwise local system time
        try:
            now = blockchain_client.get_current_blockchain_timestamp()
        except AttributeError:
            now = datetime.now().timestamp()

        for auc in auctions:
            if not auc["active"]:
                continue

            time_left = auc["close_date"] - now
            time_str = f"{int(time_left / 60)} min" if time_left > 0 else "ENDED"

            print(
                f"{auc['id']:<4} | {auc['description']:<20} | "
                f"{auc['highest_bid']:<12} | {time_str}"
            )

        print("-" * 60)
        auction_id = input("Enter auction ID to join (or 'B' to return): ").strip()

        if auction_id.upper() == "B":
            return

    
        # Load pseudonym cache and ask for password
         
        load_pseudonym_cache(user_folder)  

        print("\n[SECURITY] Enter your wallet password to unlock/create the pseudonym.")
        password = input("Password: ").strip()

        cache_key = f"{username}_{auction_id}"
        pseudo_data_ram = {}  

        
        # CASE A: Pseudonym already exists in cache
    
        if cache_key in PSEUDONYM_CACHE:
            print(" -> Encrypted pseudonym found. Unlocking...")
            cached_entry = PSEUDONYM_CACHE[cache_key]

            try:
                # Decrypt pseudonym private key
                encrypted_bytes = eval(cached_entry["pseudo_priv_encrypted"])
                salt_bytes = base64.b64decode(cached_entry["salt"])

                decrypted_pem = decrypt_data(password, encrypted_bytes, salt_bytes)

                pseudo_priv_obj = serialization.load_pem_private_key(
                    decrypted_pem, password=None
                )

                # Load delegation token from JSON
                token_dict = json.loads(cached_entry["token"])

                # Check if delegation token is expired and refresh if needed
                needs_refresh = False
                not_after_str = token_dict.get("not_after")

                if not_after_str:
                    try:
                        not_after = datetime.fromisoformat(
                            not_after_str.replace("Z", "+00:00")
                        )
                        if datetime.now(timezone.utc) > not_after:
                            needs_refresh = True
                    except Exception:
                        needs_refresh = True

                if needs_refresh:
                    print(" -> Delegation token expired. Regenerating...")

                    # Load the real identity (client private key + certificate)
                    user_priv_pem = (user_folder / "client_private_key.pem").read_bytes()
                    user_priv_key = serialization.load_pem_private_key(
                        user_priv_pem, password=None
                    )

                    user_cert_pem = (user_folder / "client_cert.pem").read_bytes()
                    user_cert = load_pem_x509_certificate(user_cert_pem)
                    user_cert_serial = str(user_cert.serial_number)

                    # Reuse the same pseudonym id and public key
                    pseudo_id = cached_entry["pseudo_id"]
                    pseudo_pub_pem = pseudo_priv_obj.public_key().public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo,
                    )

                    # Build a new delegation token
                    new_token = build_pseudonym_token(
                        user_priv_key,
                        user_cert_serial,
                        auction_id,
                        pseudo_id,
                        pseudo_pub_pem,
                    )

                    # Update cache in memory and on disk
                    cached_entry["token"] = json.dumps(new_token)
                    PSEUDONYM_CACHE[cache_key] = cached_entry
                    save_pseudonym_cache(user_folder)

                    token_dict = new_token  # start using the refreshed token

                # Data ready to be used in the auction room
                pseudo_data_ram = {
                    "pseudo_id": cached_entry["pseudo_id"],
                    "pseudo_priv": pseudo_priv_obj,
                    "token": token_dict,
                }
                print(f" -> Success: identity {pseudo_data_ram['pseudo_id']} loaded.")

            except Exception as e:
                print(f" [CRYPTO ERROR] Wrong password or corrupted data: {e}")
                return

       
        # CASE B: First time in this auction – create a new pseudonym
       
        else:
            print(" -> Generating new anonymous identity for this auction...")

            # Load real identity to sign the delegation
            try:
                _ = load_wallet(user_folder, password)
            except Exception:
                print(" [ERROR] Invalid wallet password.")
                return

            user_priv_pem = (user_folder / "client_private_key.pem").read_bytes()
            user_priv_key = serialization.load_pem_private_key(
                user_priv_pem, password=None
            )

            user_cert_pem = (user_folder / "client_cert.pem").read_bytes()
            user_cert = load_pem_x509_certificate(user_cert_pem)
            user_cert_serial = str(user_cert.serial_number)

            # Generate pseudonym key pair
            pseudo_id = generate_pseudonym()
            pseudo_priv, _, pseudo_pub_pem = generate_pseudonym_keypair()

            # Build delegation token 
            delegation_token = build_pseudonym_token(
                user_priv_key, user_cert_serial, auction_id, pseudo_id, pseudo_pub_pem
            )

            # Encrypt and store the pseudonym private key
            pseudo_priv_bytes = pseudo_priv.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

            encrypted_key, salt = encrypt_data(password, pseudo_priv_bytes)

            pseudo_data_to_save = {
                "pseudo_id": pseudo_id,
                "pseudo_priv_encrypted": str(encrypted_key),
                "salt": base64.b64encode(salt).decode("utf-8"),
                "token": json.dumps(delegation_token),
            }

            PSEUDONYM_CACHE[cache_key] = pseudo_data_to_save
            save_pseudonym_cache(user_folder)

            pseudo_data_ram = {
                "pseudo_id": pseudo_id,
                "pseudo_priv": pseudo_priv,
                "token": delegation_token,
            }
            print(f" -> New pseudonym {pseudo_id} created, encrypted, and saved.")

       
        # Mapping pseudonym - peer id at the tracker
    
        if p2p_client is not None:
            try:
                p2p_client.associate_pseudonym(int(auction_id), pseudo_data_ram["pseudo_id"])
            except Exception:
                pass

        # Enters the live auction room
        enter_auction_room(
            user_folder,
            username,
            int(auction_id),
            p2p_client,
            pseudo_data_ram["pseudo_id"],
            pseudo_data_ram["pseudo_priv"],
            pseudo_data_ram["token"],
        )

    except Exception as e:
        print(f" [ERROR] {e}")


def create_auction(user_folder: Path, username: str, p2p_client):
    """Create a new auction on the blockchain and broadcast the announcement."""
    print("\n=== CREATE AUCTION ===")

    desc = input("Item Description: ").strip()
    duration = input("Duration (minutes): ").strip()
    min_bid = input("Min Bid (Tokens): ").strip()

    if not desc or not duration or not min_bid:
        return

    password = input("Wallet Password: ").strip()

    try:
        account = load_wallet(user_folder, password)
        print(" Sending transaction...")
        tx = blockchain_client.create_auction(account, desc, duration, min_bid)
        print(f" Auction created. Tx: {tx}")

        payload = {
            "description": desc,
            "min_bid": min_bid,
            "tx_hash": str(tx),
        }

        if p2p_client is not None:
            try:
                p2p_client.broadcast_event("NEW_AUCTION", payload)
            except Exception as e:
                print(f" [P2P WARNING] Failed to broadcast NEW_AUCTION: {e}")

    except Exception as e:
        print(f" [ERROR] {e}")

    input("Press Enter to return...")
