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
from .p2p_ws_client import P2PTrackerClient, set_global_token


def register_flow():
    """Handles full user registration and wallet creation."""
    print("\n--- REGISTER NEW ACCOUNT ---")

    while True:
        username = input("Choose a username: ").strip()
        if not username:
            print("Username cannot be empty.")
            continue

        user_folder = get_user_folder(username)

        # Prevent overwriting an existing identity
        if identity_exists(user_folder):
            print(f"Local identity for '{username}' already exists.")
            print("Use the LOGIN option instead.")
            return None

        try:
            # Create folder and generate RSA identity
            if not user_folder.exists():
                user_folder.mkdir(parents=True)

            private_key = generate_keypair()
            save_private_key(private_key, user_folder / "client_private_key.pem")
            csr_pem = generate_csr(private_key, username)

            # Fetch and store CA certificate
            ca_pem = fetch_ca_certificate()
            (user_folder / "ca_cert.pem").write_text(ca_pem)
            ca_cert = load_ca_cert(user_folder / "ca_cert.pem")

            # Request signed certificate
            client_cert_pem = request_certificate(csr_pem)

            # Validate certificate before saving
            if not validate_cert_with_ca(client_cert_pem, ca_cert):
                shutil.rmtree(user_folder)
                return None

            (user_folder / "client_cert.pem").write_text(client_cert_pem)

            # Wallet password setup
            while True:
                pw = input("Wallet Password: ").strip()
                pw_conf = input("Confirm Password: ").strip()
                if pw == pw_conf and pw:
                    break
                print("Passwords do not match or are empty.")

            # Create encrypted blockchain wallet
            eth_address, encrypted_data = create_encrypted_wallet(pw)
            save_wallet_file(user_folder, encrypted_data)
            (user_folder / "wallet_address.txt").write_text(eth_address)

            # Fund wallet with initial tokens
            blockchain_client.fund_new_user(eth_address)

            print("Registration complete. Please login.")
            return None

        except Exception as e:
            # Cleanup failed registration
            if user_folder.exists():
                shutil.rmtree(user_folder)

            if "exists" in str(e) or "duplicate" in str(e):
                print(f"Username '{username}' already exists on the server.")
                continue

            print(f"Registration failed: {e}")
            return None


def login_flow():
    """Handles user authentication and P2P WebSocket initialization."""
    print("\n--- LOGIN ---")

    username = input("Username: ").strip()
    if not username:
        return None, None

    user_folder = get_user_folder(username)
    cert_path = user_folder / "client_cert.pem"

    # Load certificate (local or custom path)
    if not cert_path.exists():
        custom_path = input("Enter full path to your certificate (.pem): ").strip()
        p = Path(custom_path)
        if not p.exists():
            print("Certificate not found.")
            return None, None
        cert_path = p

    private_key_path = cert_path.parent / "client_private_key.pem"
    if not private_key_path.exists():
        print("Private key not found.")
        return None, None

    try:
        # Challenge-response authentication
        token = login_secure(username, private_key_path)
        if not token:
            return None, None

        # Store token for P2P broadcast authorization
        set_global_token(token)

        # Start WebSocket P2P client
        p2p_port = random.randint(6000, 6999)
        client = P2PTrackerClient(username)

        if client.connect_and_auth(token, p2p_port):
            return username, client

        print("WebSocket authentication failed.")
        return None, None

    except Exception as e:
        print(f"Login failed: {e}")
        return None, None



def authentication_menu():
    """Main entry menu for registration and login."""
    while True:
        print("\n==============================")
        print("      SECURE AUCTION CLIENT   ")
        print("==============================")
        print("1. Register (New User)")
        print("2. Login (Existing User)")
        print("3. Exit")

        choice = input("\nSelect an option: ").strip()

        if choice == '1':
            register_flow()

        elif choice == '2':
            username, client = login_flow()
            if username:
                return username, client

        elif choice == '3':
            sys.exit(0)

        else:
            print("Invalid option.")


