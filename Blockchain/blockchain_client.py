import json
import os
from web3 import Web3
from pathlib import Path

# --- CONFIGURATION ---
# Check if using Port 8545 (CLI) or 7545 (GUI)
RPC_URL = "http://127.0.0.1:7545"
web3 = Web3(Web3.HTTPProvider(RPC_URL))

BASE_DIR = Path(__file__).parent.parent
ABI_PATH = BASE_DIR / "Blockchain" / "build" / "contracts" / "Auction.json"

CONTRACT_ADDRESS = "0x3683E1814b071A9411F79eF9ca16fe30d49613fD"

contract = None
BANK_ACCOUNT = web3.eth.accounts[0] if web3.is_connected() else None


def load_contract():
    global contract
    if not web3.is_connected(): return None
    try:
        if not os.path.exists(ABI_PATH):
            print(f" [WARN] ABI not found at: {ABI_PATH}")
            return None

        with open(ABI_PATH) as f:
            data = json.load(f)
            abi = data["abi"]
        contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)
    except Exception as e:
        print(f" [ERROR] Contract load failed: {e}")


load_contract()


def get_internal_balance(address):
    """Reads game token balance (Balances.sol)."""
    if not contract: return 0
    try:
        return contract.functions.getBalance(address).call()
    except:
        return 0


def _send_signed_transaction(tx, private_key):
    """
    Helper to handle version conflicts between Brownie/Web3.py.
    Extracts rawTransaction safely regardless of object type.
    """
    try:
        # Sign the transaction
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)

        # VERSION COMPATIBILITY FIX:
        # Depending on libraries, signed_tx can be an Object, a Dict, or an AttributeDict.
        raw_tx = None

        # Tentativa 1: Atributo padrão (Web3 moderno)
        if hasattr(signed_tx, 'rawTransaction'):
            raw_tx = signed_tx.rawTransaction
        # Tentativa 2: Snake case (Algumas versões específicas)
        elif hasattr(signed_tx, 'raw_transaction'):
            raw_tx = signed_tx.raw_transaction
        # Tentativa 3: Dicionário (Web3 antigo / Compatibilidade Brownie)
        else:
            try:
                raw_tx = signed_tx['rawTransaction']
            except:
                # Tentativa 4: Acesso por índice (se for tupla/lista)
                raw_tx = signed_tx[0]

                # Send raw bytes
        tx_hash = web3.eth.send_raw_transaction(raw_tx)

        # Wait for receipt
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.transactionHash.hex()

    except Exception as e:
        # Print debug info to help you if it still fails
        print(f" [DEBUG ERROR] Transaction failed. Signed Object Type: {type(signed_tx)}")
        # print(f" [DEBUG] Object Dir: {dir(signed_tx)}")
        raise e


# ---------------------------------------

def create_auction(account, description, duration_minutes, min_bid):
    if not contract: raise Exception("Contract offline")
    print(f" -> Creating Auction: '{description}'...")

    duration_seconds = int(duration_minutes) * 60

    tx = contract.functions.createAuction(
        description,
        duration_seconds,
        int(min_bid)
    ).build_transaction({
        'from': account.address,
        'nonce': web3.eth.get_transaction_count(account.address),
        'gas': 3000000,
        'gasPrice': web3.to_wei('20', 'gwei')
    })

    # Use the safe helper
    return _send_signed_transaction(tx, account.key)


def place_bid_on_chain(account, auction_id, amount):
    if not contract: raise Exception("Contract offline")
    print(f" -> Placing Bid of {amount} on ID {auction_id}...")

    tx = contract.functions.placeBid(
        int(auction_id),
        int(amount)
    ).build_transaction({
        'from': account.address,
        'nonce': web3.eth.get_transaction_count(account.address),
        'gas': 3000000,
        'gasPrice': web3.to_wei('20', 'gwei')
    })

    # Use the safe helper
    return _send_signed_transaction(tx, account.key)


def get_all_auctions():
    if not contract: return []
    try:
        count = contract.functions.auctionCount().call()
        auctions = []
        for i in range(1, count + 1):
            data = contract.functions.auctions(i).call()
            # Struct: (seller, desc, minBid, closeDate, highestBid, bidder, active)
            auctions.append({
                "id": i,
                "description": data[1],
                "min_bid": data[2],
                "close_date": data[3],
                "highest_bid": data[4],
                "active": data[6]
            })
        return auctions
    except Exception as e:
        print(f"Error fetching auctions: {e}")
        return []


def fund_new_user(target_address, amount_eth=10):
    if not web3.is_connected(): return False
    try:
        tx = web3.eth.send_transaction({
            'from': BANK_ACCOUNT, 'to': target_address, 'value': web3.to_wei(amount_eth, 'ether')
        })
        web3.eth.wait_for_transaction_receipt(tx)
        return True
    except:
        return False