from brownie import Auction, accounts


def print_balances(auction, label=""):
    print(f"\n--- BALANCES {label} ---")
    for i in range(3):
        acc = accounts[i]
        bal = auction.getBalance(acc)
        print(f"Account {i} ({acc}): {bal}")


def test_auction_flow():
    seller = accounts[0]
    bidder1 = accounts[1]
    bidder2 = accounts[2]

    print("\n======= DEPLOY CONTRACT =======")
    auction = Auction.deploy({"from": seller})
    print("Auction contract deployed at:", auction.address)

    print_balances(auction, "INITIAL")

    print("\n======= CREATE AUCTION =======")
    tx = auction.createAuction({"from": seller})
    print("Auction created in block:", tx.block_number)
    print_balances(auction, "AFTER CREATE AUCTION")

    print("\n======= PLACE BID 1 (3 tokens) =======")
    tx = auction.placeBid(1, 3, {"from": bidder1})
    print("Bid 1 placed by:", bidder1)
    print("Block of bid:", tx.block_number)
    print_balances(auction, "AFTER BID 1")

    print("\n======= PLACE BID 2 (10 tokens, account 2) =======")
    tx = auction.placeBid(1, 10, {"from": bidder2})
    print("Bid 2 placed by:", bidder2)
    print("Block of bid:", tx.block_number)
    print_balances(auction, "AFTER BID 2")

    print("\n======= END AUCTION =======")
    tx = auction.endAuction(1, {"from": seller})
    print("Auction ended in block:", tx.block_number)
    print_balances(auction, "FINAL")

    print("\n======= TEST COMPLETED =======")
