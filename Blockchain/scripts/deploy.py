from brownie import Auction, Balances, accounts, config


def main():

    PRIVATE_KEY = "0x250f690e0017bd5d2e3a6b49e11df741852040c67df45afb8fd449ca902e124c"

    deployer = accounts.add(PRIVATE_KEY)

    print(f"Deploying contracts with account: {deployer}")


    auction = Auction.deploy({'from': deployer})

    print(f"Auction deployed at: {auction.address}")
