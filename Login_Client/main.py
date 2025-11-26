from login_menu import login
from auction_menu import handle_bid
from identity.paths import get_user_folder

def main():
    username=login()

    user_folder = get_user_folder(username)

    handle_bid(user_folder)

if __name__ == "__main__":
    main()
