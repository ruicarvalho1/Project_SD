pragma solidity ^0.8.10;

import "../interfaces/IAuction.sol";
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

    function createAuction() external override returns (uint) {
        initUser();

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
        initUser();

        AuctionInfo storage auction = auctions[auctionId];

        require(auction.active, "Auction ended");
        require(bidAmount > auction.highestBid, "Bid too low");
        require(balances[msg.sender] >= bidAmount, "Insufficient balance");


        if (auction.highestBidder != address(0)) {
            balances[auction.highestBidder] += auction.highestBid;
        }

        balances[msg.sender] -= bidAmount;

        auction.highestBid = bidAmount;
        auction.highestBidder = msg.sender;
    }

    function endAuction(uint auctionId) external override {
        initUser();

        AuctionInfo storage auction = auctions[auctionId];

        require(auction.active, "Already closed");
        require(msg.sender == auction.seller, "Only seller can end");

        auction.active = false;

        balances[auction.seller] += auction.highestBid;
    }
}
