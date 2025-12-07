import json
import os
from web3 import Web3
from pathlib import Path
import time

# Blockchain connection
RPC_URL = "http://127.0.0.1:7545"
web3 = Web3(Web3.HTTPProvider(RPC_URL))

BASE_DIR = Path(__file__).parent.parent
ABI_PATH = BASE_DIR / "Blockchain" / "build" / "contracts" / "Auction.json"
CONTRACT_ADDRESS = "0xC2aB968B17FBcC30D3ACf40f66F08Cc1A96350FF"

contract = None
BANK_ACCOUNT = web3.eth.accounts[0] if web3.is_connected() else None


def load_contract():
    """Load contract using ABI and deployed address."""
    global contract
    if not web3.is_connected():
        return None
    try:
        if not os.path.exists(ABI_PATH):
            print(f"ABI not found at: {ABI_PATH}")
            return None

        with open(ABI_PATH) as f:
            data = json.load(f)
            abi = data["abi"]

        contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)

    except Exception as e:
        print(f"Contract load failed: {e}")


load_contract()


def get_internal_balance(address):
    """Returns token balance."""
    if not contract:
        return 0
    try:
        return contract.functions.getBalance(address).call()
    except:
        return 0


def _send_signed_transaction(tx, private_key):
    """
    Signs a transaction and sends it.
    Handles multiple Web3/Brownie return formats safely.
    """
    try:
        signed_tx = web3.eth.account.sign_transaction(tx, private_key)

        # Extract rawTransaction from different possible structures
        if hasattr(signed_tx, 'rawTransaction'):
            raw_tx = signed_tx.rawTransaction
        elif hasattr(signed_tx, 'raw_transaction'):
            raw_tx = signed_tx.raw_transaction
        else:
            try:
                raw_tx = signed_tx['rawTransaction']
            except:
                raw_tx = signed_tx[0]

        tx_hash = web3.eth.send_raw_transaction(raw_tx)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.transactionHash.hex()

    except Exception as e:
        print(f"Transaction failed: {e}")
        raise e


def create_auction(account, description, duration_minutes, min_bid):
    """Creates a new auction on-chain."""
    if not contract:
        raise Exception("Contract offline")

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

    return _send_signed_transaction(tx, account.key)


def place_bid_on_chain(account, auction_id, amount, tsa_timestamp):
    """Places a bid on an auction (with TSA timestamp)."""
    if not contract:
        raise Exception("Contract offline")

    tx = contract.functions.placeBid(
        int(auction_id),
        int(amount),
        int(tsa_timestamp),
    ).build_transaction({
        'from': account.address,
        'nonce': web3.eth.get_transaction_count(account.address),
        'gas': 3000000,
        'gasPrice': web3.to_wei('20', 'gwei'),
        'value': 0
    })

    return _send_signed_transaction(tx, account.key)




def get_all_auctions():
    """Returns all auction structs."""
    if not contract:
        return []
    try:
        count = contract.functions.auctionCount().call()
        auctions = []

        for i in range(1, count + 1):
            data = contract.functions.auctions(i).call()
            auctions.append({
                "id": i,
                "description": data[1],
                "min_bid": data[2],
                "close_date": data[3],
                "highest_bid": data[4],
                "active": data[6],
            })
        return auctions

    except Exception as e:
        print(f"Error fetching auctions: {e}")
        return []


def fund_new_user(target_address, amount_eth=10):
    """Sends ETH from the bank account to bootstrap new users."""
    if not web3.is_connected():
        return False
    try:
        tx = web3.eth.send_transaction({
            'from': BANK_ACCOUNT,
            'to': target_address,
            'value': web3.to_wei(amount_eth, 'ether')
        })
        web3.eth.wait_for_transaction_receipt(tx)
        return True
    except:
        return False


def get_current_blockchain_timestamp():
    """
    Returns the current blockchain time as given by the timestamp
    of the latest mined block.
    """
    if not web3.is_connected():
        raise RuntimeError("Web3 not connected")

    latest_block = web3.eth.get_block("latest")

    return latest_block["timestamp"]


def get_auction_details(auction_id):
    """Returns full info for a single auction, including active flag and highestBid."""
    if not contract:
        return None
    try:
        data = contract.functions.auctions(int(auction_id)).call()

        return {
            "id": int(auction_id),
            "seller": data[0],
            "description": data[1],
            "min_bid": data[2],
            "close_date": data[3],
            "highest_bid": data[4],
            "highest_bidder": data[5],
            "active": data[6],
            "created_at": data[7],
            "highest_bid_timestamp": data[8],
        }
    except Exception as e:
        print(f"Error fetching auction details for {auction_id}: {e}")
        return None


