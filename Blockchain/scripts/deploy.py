from brownie import Auction, accounts

def main():
    acct = accounts[0]
    auction = Auction.deploy({'from': acct})
    print("Auction deployed:", auction.address)
