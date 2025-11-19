pragma solidity ^0.8.10;

import "./interfaces/IAuction.sol";
import "./Balances.sol";


contract Auction is IAuction, Balances {

    struct AuctionInfo {
        address seller;
        uint highestBid;
        address highestBidder;
        bool active;
    }

    mapping(uint => AuctionInfo) public auctions;
    uint public auctionCount;

    constructor() {

        setInitialBalance(msg.sender, 100);
    }

    function createAuction() external override returns (uint) {
        auctionCount++;
        auctions[auctionCount] = AuctionInfo({
            seller: msg.sender,
            highestBid: 0,
            highestBidder: address(0),
            active: true
        });
        return auctionCount;
    }

    function placeBid(uint auctionId, uint bidAmount) external override {
        AuctionInfo storage auction = auctions[auctionId];

        require(auction.active, "Auction ended");
        require(bidAmount > auction.highestBid, "Bid too low");
        require(balances[msg.sender] >= bidAmount, "Insufficient balance");

        // refund the previous bidder
        if (auction.highestBidder != address(0)) {
            balances[auction.highestBidder] += auction.highestBid;
        }
        // deduct from the new bidder
        balances[msg.sender] -= bidAmount;

        // Update auction info
        auction.highestBid = bidAmount;
        auction.highestBidder = msg.sender;
    }
    // Ask Joao and Tiago about this function
    function endAuction(uint auctionId) external override {
        AuctionInfo storage auction = auctions[auctionId];

        require(auction.active, "Already closed");
        require(msg.sender == auction.seller, "Only seller can end");

        auction.active = false;

        balances[auction.seller] += auction.highestBid;
    }
}
