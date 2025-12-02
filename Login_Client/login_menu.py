import sys
import shutil
import requests
import random
from pathlib import Path

from Login_Client.identity.paths import get_user_folder
from Login_Client.identity.manager import (
    identity_exists,
    generate_keypair,
    save_private_key,
    generate_csr
)
from Login_Client.identity.validation import load_ca_cert, validate_cert_with_ca
from Login_Client.ca.client import fetch_ca_certificate, request_certificate
from Login_Client.auth.login import login_secure

from Login_Client.identity.wallet_manager import create_encrypted_wallet, save_wallet_file
from Blockchain import blockchain_client


def register_flow():
    """Handles the registration of a new user identity and wallet creation."""
    print("\n--- REGISTER NEW ACCOUNT ---")

    while True:
        username = input("Choose a username: ").strip()
        if not username:
            print("Username cannot be empty.")
            continue

        user_folder = get_user_folder(username)

        # Ensure local identity does not already exist
        if identity_exists(user_folder):
            print(f" Local identity for '{username}' already exists.")
            print(" Use the LOGIN option instead.")
            return None

        print(f" Checking availability for '{username}'...")

        try:
            # Create user directory
            if not user_folder.exists():
                user_folder.mkdir(parents=True)

            # Generate RSA keypair and CSR
            print(" Generating RSA identity...")
            private_key = generate_keypair()
            save_private_key(private_key, user_folder / "client_private_key.pem")
            csr_pem = generate_csr(private_key, username)

            # Fetch Certificate Authority certificate
            ca_pem = fetch_ca_certificate()
            (user_folder / "ca_cert.pem").write_text(ca_pem)
            ca_cert = load_ca_cert(user_folder / "ca_cert.pem")

            # Request signed certificate from the server
            client_cert_pem = request_certificate(csr_pem)

            # Validate certificate returned by server
            if not validate_cert_with_ca(client_cert_pem, ca_cert):
                print(" Server returned an invalid certificate.")
                shutil.rmtree(user_folder)
                return None

            # Save valid client certificate
            (user_folder / "client_cert.pem").write_text(client_cert_pem)
            print(f" Account '{username}' successfully registered.")

            # Web3 wallet setup
            print("\n--- ETHEREUM WALLET SETUP ---")
            print("Choose a password to encrypt your wallet.")

            while True:
                pw = input("Wallet Password: ").strip()
                pw_conf = input("Confirm Password: ").strip()
                if pw == pw_conf and pw:
                    break
                print(" Passwords do not match or are empty.")

            # Create encrypted Ethereum wallet
            print(" Creating encrypted wallet...")
            eth_address, encrypted_data = create_encrypted_wallet(pw)
            save_wallet_file(user_folder, encrypted_data)
            (user_folder / "wallet_address.txt").write_text(eth_address)

            print(f" Wallet created: {eth_address}")

            # Request initial blockchain funds for the new wallet
            print(" Requesting initial blockchain funds...")
            blockchain_client.fund_new_user(eth_address)

            print(" Registration complete. Please choose LOGIN in the main menu.")
            return None

        except Exception as e:
            error_msg = str(e)

            # Cleanup invalid folder
            if user_folder.exists():
                shutil.rmtree(user_folder)

            if "already exists" in error_msg or "duplicate" in error_msg:
                print(f" Username '{username}' is already taken on the server.")
                print(" Try a different name.\n")
            else:
                print(f" Registration failed: {e}")
                return None


def login_flow():
    """Handles login through challenge-response authentication and P2P registration."""
    print("\n--- LOGIN ---")

    username = input("Username: ").strip()
    if not username:
        return None

    user_folder = get_user_folder(username)
    default_cert_path = user_folder / "client_cert.pem"
    cert_path = None

    # Load user certificate
    if default_cert_path.exists():
        cert_path = default_cert_path
        print(f" Certificate found at: {cert_path}")
    else:
        print(f" Certificate not found in {user_folder}")
        custom_path = input("Enter full path to your certificate (.pem): ").strip()

        if custom_path:
            p = Path(custom_path)
            if p.exists() and p.is_file():
                cert_path = p
            else:
                print(" Certificate file not found.")
                return None
        else:
            return None

    private_key_path = cert_path.parent / "client_private_key.pem"

    if not private_key_path.exists():
        print(f" Private key not found at: {private_key_path}")
        print(" Login is not possible without the private key.")
        return None

    # Authentication
    try:
        token = login_secure(username, private_key_path)

        if token:
            print(f" Logged in as: {username}")

            # Random port for P2P node
            MY_P2P_PORT = random.randint(6000, 6999)
            print(f" Starting P2P listener on port {MY_P2P_PORT}...")

            # Start P2P background node
            try:
                from p2p_node import start_background_node
                start_background_node(MY_P2P_PORT)
            except ImportError:
                print(" p2p_node.py not found. Peer will operate passively.")
            except Exception as e:
                print(f" Failed to start P2P listener: {e}")
                return None

            # Register peer in tracker
            print(" Connecting to P2P Tracker...")
            try:
                tracker_response = requests.post(
                    "http://127.0.0.1:5555/register",
                    json={"token": token, "port": MY_P2P_PORT}
                )

                if tracker_response.status_code == 200:
                    ip = tracker_response.json().get('your_ip')
                    print(f" Connected to P2P Network at {ip}:{MY_P2P_PORT}")
                    return username
                else:
                    print(f" Tracker rejected registration: {tracker_response.text}")
                    return None

            except requests.exceptions.ConnectionError:
                print(" Tracker is offline. Ensure Tracker.py is running.")
                return None

    except Exception as e:
        print(f" Login failed: {e}")
        return None


def authentication_menu():
    """Main entry menu for user authentication."""
    while True:
        print("\n==============================")
        print("      SECURE AUCTION CLIENT   ")
        print("==============================")
        print("1. Register (New User)")
        print("2. Login (Existing User)")
        print("3. Exit")

        choice = input("\nSelect an option (1-3): ").strip()

        if choice == '1':
            register_flow()

        elif choice == '2':
            user = login_flow()
            if user:
                return user

        elif choice == '3':
            print("Exiting...")
            sys.exit(0)

        else:
            print("Invalid option.")
