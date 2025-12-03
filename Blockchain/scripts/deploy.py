from brownie import Auction, Balances, accounts, config


def main():

    PRIVATE_KEY = "0x1ebc4c70046e6cd8d2266306bba14f40fec6dec092c3e7a4f8ac24e88ca817ad"

    deployer = accounts.add(PRIVATE_KEY)

    print(f"Deploying contracts with account: {deployer}")


    auction = Auction.deploy({'from': deployer})

    print(f"Auction deployed at: {auction.address}")
