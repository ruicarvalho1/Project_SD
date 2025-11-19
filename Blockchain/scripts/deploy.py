from brownie import Auction, accounts

def main():
    account = accounts[0];

    auction_contract = Auction.deploy({"from": account})

    print(f"Auction contract deployed at: {auction_contract.address}")
    print(auction_contract)

    return auction_contract