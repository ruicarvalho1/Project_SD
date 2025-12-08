from brownie import Auction, Balances, accounts, config


def main():

    PRIVATE_KEY = "0xbeab7222824d82f0f8b11ee2e46b62452086506d5ab8ed1aa87ff75a01e04ba9"

    deployer = accounts.add(PRIVATE_KEY)

    print(f"Deploying contracts with account: {deployer}")


    auction = Auction.deploy({'from': deployer})

    print(f"Auction deployed at: {auction.address}")
