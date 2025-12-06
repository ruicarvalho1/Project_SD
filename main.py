import sys
from Login_Client.login_menu import authentication_menu
from Auction_Client.auction_menu import auction_menu
from Login_Client.identity.paths import get_user_folder


def main():
    print("\n--- STARTING CLIENT (ROOT CONTEXT) ---")

    username, p2p_client = authentication_menu()

    if username:
        print("\n" + "=" * 50)
        print(f" SESSION STARTED: {username}")
        print("=" * 50 + "\n")

        user_folder = get_user_folder(username)

        auction_menu(user_folder, username, p2p_client)

    else:
        print("\n [INFO] Operation cancelled or login failed.")


if __name__ == "__main__":
    main()
