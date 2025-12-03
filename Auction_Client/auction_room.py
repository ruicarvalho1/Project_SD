import time
from Blockchain import blockchain_client
from Login_Client.identity.wallet_manager import load_wallet
from .auction_input import input_with_timeout
from .auction_display import display_auction_header
from .auction_utils import broadcast_to_peers, signal_refresh, NEEDS_REFRESH


def enter_auction_room(user_folder, username, auction_id, p2p_client):
    """
    Live Auction Room.
    Displays ongoing updates and allows instant bidding.
    Runs until the user types 'EXIT'.
    """
    print("\n [SETUP] Wallet unlock required to join and bid without repeated prompts.")
    password = input(" Wallet Password: ").strip()

    try:
        account = load_wallet(user_folder, password)
        print(" Wallet unlocked. Ready to bid.")
    except Exception:
        print(" Invalid password. Returning to menu.")
        return

    wallet_address = account.address

    try:
        p2p_client.set_refresh_callback(signal_refresh)
    except AttributeError:
        print("[WARNING] Falha ao ligar o auto-refresh. O cliente P2P precisa da função set_refresh_callback.")


    while True:

        global NEEDS_REFRESH
        if NEEDS_REFRESH:
            print("\n" + "=" * 60)
            print(" [SINCRONIZAÇÃO] Recarregando dados após notificação...")
            NEEDS_REFRESH = False
            time.sleep(0.1)
            continue

        # 2. Redesenhar o Cabeçalho (CORREÇÃO DE CHAMADA AQUI)
        # Passamos o address para a função de display:
        if not display_auction_header(auction_id, wallet_address): # <--- ADICIONADO: wallet_address
            break

        # User input for bidding or refreshing
        bid_amount = input(
            " Enter bid amount ('R' refresh / 'EXIT' leave room): "
        ).strip().upper()

        if bid_amount == "EXIT":
            break
        elif bid_amount == "R":
            continue
        elif not bid_amount:
            continue

        try:

            tx_hash = blockchain_client.place_bid_on_chain(
                account, auction_id, bid_amount
            )
            print(f" Bid accepted. Tx: {tx_hash}")

            time.sleep(1)

        except ValueError as e:
            print(f" Invalid bid or insufficient balance: {e}")
            time.sleep(2)
        except Exception as e:
            print(f" [CONTRACT ERROR] {e}")
            time.sleep(3)
