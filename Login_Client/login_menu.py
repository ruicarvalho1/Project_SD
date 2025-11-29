import sys
import shutil
from pathlib import Path

# Project imports
from Login_Client.identity.paths import get_user_folder
from Login_Client.identity.manager import (
    identity_exists,
    generate_keypair,
    save_private_key,
    generate_csr
)
from identity.validation import load_ca_cert, validate_cert_with_ca
from ca.client import fetch_ca_certificate, request_certificate

from auth.login import login_secure


def register_flow():
    """Handles the REGISTRATION of new users."""
    print("\n--- REGISTER NEW ACCOUNT ---")

    while True:
        username = input("Choose a username: ").strip()
        if not username:
            print("Username cannot be empty.")
            continue

        user_folder = get_user_folder(username)

        # 1. Protection: Check if local identity already exists
        if identity_exists(user_folder):
            print(f" [!] Local identity for '{username}' already exists.")
            print("     Please use the LOGIN option in the main menu.")
            return None

        print(f" -> Checking availability for '{username}'...")

        try:
            # 2. Generate temporary keys
            if not user_folder.exists():
                user_folder.mkdir(parents=True)

            private_key = generate_keypair()
            save_private_key(private_key, user_folder / "client_private_key.pem")
            csr_pem = generate_csr(private_key, username)

            # 3. Fetch CA Certificate
            ca_pem = fetch_ca_certificate()
            (user_folder / "ca_cert.pem").write_text(ca_pem)
            ca_cert = load_ca_cert(user_folder / "ca_cert.pem")

            # 4. Request Certificate from Server
            client_cert_pem = request_certificate(csr_pem)

            # 5. Validate Integrity
            if not validate_cert_with_ca(client_cert_pem, ca_cert):
                print(" [FATAL] Server returned an invalid certificate!")
                shutil.rmtree(user_folder)
                return None

            # 6. Success - Save
            (user_folder / "client_cert.pem").write_text(client_cert_pem)
            print(f" [SUCCESS] Account '{username}' registered and keys saved.")
            return username  # Return username to auto-login or exit

        except Exception as e:
            error_msg = str(e)
            if user_folder.exists():
                shutil.rmtree(user_folder)

            if "already exists" in error_msg or "duplicate" in error_msg:
                print(f" [ERROR] Username '{username}' is already taken on the server.")
                print(" -> Please try a different name.\n")
            else:
                print(f" [ERROR] Registration failed: {e}")
                return None


def login_flow():
    """Handles LOGIN with Challenge-Response (requires Private Key)."""
    print("\n--- LOGIN ---")

    username = input("Username: ").strip()
    if not username:
        return None

    user_folder = get_user_folder(username)
    default_cert_path = user_folder / "client_cert.pem"
    cert_path = None

    # 1. Try to find certificate in the default folder
    if default_cert_path.exists():
        cert_path = default_cert_path
        print(f" -> Certificate found at: {cert_path}")
    else:
        # 2. If not found, ASK FOR THE DIRECTORY/FILE
        print(f" [!] Certificate not found in {user_folder}")
        custom_path = input("Enter the full path to the .pem file: ").strip()

        if custom_path:
            p = Path(custom_path)
            if p.exists() and p.is_file():
                cert_path = p
            else:
                print(" [ERROR] File not found.")
                return None
        else:
            return None

    private_key_path = cert_path.parent / "client_private_key.pem"

    if not private_key_path.exists():
        print(f" [ERROR] Private Key not found at: {private_key_path}")
        print("         You cannot prove your identity without the private key.")
        return None

    # 3. Authentication (Secure Handshake)
    try:
        print(" -> Initiating Secure Challenge-Response...")


        if login_secure(username, private_key_path):
            print(f" [SUCCESS] Logged in as: {username}")
            return username

    except Exception as e:
        print(f" [ERROR] Login failed: {e}")
        return None


def authentication_menu():
    """Main Entry Menu."""
    while True:
        print("\n==============================")
        print("      SECURE AUCTION CLIENT    ")
        print("==============================")
        print("1. Register (New User)")
        print("2. Login (Existing User)")
        print("3. Exit")

        choice = input("\nSelect an option (1-3): ").strip()

        if choice == '1':
            user = register_flow()
            if user:
                return user  # Successful registration -> Enter App
        elif choice == '2':
            user = login_flow()
            if user:
                return user  # Successful login -> Enter App
        elif choice == '3':
            print("Exiting...")
            sys.exit(0)
        else:
            print("Invalid option.")