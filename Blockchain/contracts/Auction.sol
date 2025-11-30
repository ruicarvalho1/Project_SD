// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

import "../interfaces/IAuction.sol";
import "./Balances.sol";

contract Auction is IAuction, Balances {

    struct AuctionInfo {
        address seller;
        string description;
        uint minBid;
        uint closeDate;
        uint highestBid;
        address highestBidder;
        bool active;
    }

    mapping(uint => AuctionInfo) public auctions;
    uint public auctionCount;

    // EVENTS (Seller is not revealed at creation to keep public anonymity)
    event AuctionCreated(uint indexed auctionId, string description, uint closeDate, uint minBid);
    event NewBid(uint indexed auctionId, uint amount);
    event AuctionEnded(uint indexed auctionId, address winner, uint amount);

    function createAuction(string memory _desc, uint _duration, uint _minBid) external override returns (uint) {
        initUser(); // Ensures the user has initial balance
        auctionCount++;

        // Sets closing time based on the current block timestamp
        uint closingTime = block.timestamp + _duration;

        auctions[auctionCount] = AuctionInfo({
            seller: msg.sender,
            description: _desc,
            minBid: _minBid,
            closeDate: closingTime,
            highestBid: 0,
            highestBidder: address(0),
            active: true
        });

        emit AuctionCreated(auctionCount, _desc, closingTime, _minBid);
        return auctionCount;
    }

    function placeBid(uint auctionId, uint bidAmount) external override {
        initUser();

        AuctionInfo storage auction = auctions[auctionId];

        // 1. Time validations
        require(auction.active, "Auction already ended");
        require(block.timestamp < auction.closeDate, "Auction time expired");

        // 2. Bid validations
        require(bidAmount >= auction.minBid, "Bid below minimum price");
        require(bidAmount > auction.highestBid, "Bid below current highest");
        require(balances[msg.sender] >= bidAmount, "Insufficient balance");

        // 3. Refund previous highest bidder
        if (auction.highestBidder != address(0)) {
            balances[auction.highestBidder] += auction.highestBid;
        }

        // 4. Charge and update
        balances[msg.sender] -= bidAmount;
        auction.highestBid = bidAmount;
        auction.highestBidder = msg.sender;

        emit NewBid(auctionId, bidAmount);
    }

    function endAuction(uint auctionId) external override {
        AuctionInfo storage auction = auctions[auctionId];

        require(msg.sender == auction.seller, "Only the seller can close the auction");
        require(auction.active, "Auction already closed");

        auction.active = false;

        if (auction.highestBid > 0) {
            balances[auction.seller] += auction.highestBid;
        }

        emit AuctionEnded(auctionId, auction.highestBidder, auction.highestBid);
    }
}
