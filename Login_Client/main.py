# Login_Client/main.py

from Login_Client.login_menu import authentication_menu
from Login_Client.auction_menu import handle_bid
from Login_Client.identity.paths import get_user_folder


def main():

    username = authentication_menu()

    if username:
        print("\n" + "=" * 40)
        print(f" Starting auction session for: {username}")
        print("=" * 40 + "\n")

        user_folder = get_user_folder(username)

        handle_bid(user_folder)


if __name__ == "__main__":
    main()