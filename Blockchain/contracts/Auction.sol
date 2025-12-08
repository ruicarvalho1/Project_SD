// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

import "../interfaces/IAuction.sol";
import "./Balances.sol";

contract Auction is IAuction, Balances {

    struct AuctionInfo {
        address seller;
        string description;
        uint256 minBid;
        uint256 closeDate;
        uint256 highestBid;
        address highestBidder;
        bool active;
        uint256 createdAt;
        uint256 highestBidTimestamp;
        uint256 endedAt;
    }

    mapping(uint256 => AuctionInfo) public auctions;
    uint256 public auctionCount;

    event AuctionCreated(
        uint256 indexed auctionId,
        string description,
        uint256 closeDate,
        uint256 minBid
    );

    event NewBid(
        uint256 indexed auctionId,
        uint256 amount,
        uint256 bidTimestamp
    );

    event AuctionEnded(
        uint256 indexed auctionId,
        address winner,
        uint256 amount
    );


    // CREATE AUCTION
    function createAuction(
        string memory _desc,
        uint256 _duration,
        uint256 _minBid
    )
        external
        override
        returns (uint256)
    {
        initUser();

        auctionCount++;

        uint256 nowTs = block.timestamp;
        uint256 closingTime = nowTs + _duration;

        auctions[auctionCount] = AuctionInfo({
            seller: msg.sender,
            description: _desc,
            minBid: _minBid,
            closeDate: closingTime,
            highestBid: 0,
            highestBidder: address(0),
            active: true,
            createdAt: nowTs,
            highestBidTimestamp: 0,
            endedAt: 0
        });

        emit AuctionCreated(auctionCount, _desc, closingTime, _minBid);
        return auctionCount;
    }

    // INTERNAL: APPLY NEW HIGHEST BID (USED ALSO IN TIE-BREAK)
    function _applyNewHighestBid(
        AuctionInfo storage auction,
        uint256 bidAmount,
        uint256 tsaTimestamp
    ) internal {
        // Refund the previous highest bidder if exists
        if (auction.highestBidder != address(0)) {
            balances[auction.highestBidder] += auction.highestBid;
        }

        // Charge the new bidder
        balances[msg.sender] -= bidAmount;

        // Update auction state
        auction.highestBid = bidAmount;
        auction.highestBidder = msg.sender;
        auction.highestBidTimestamp = tsaTimestamp;
    }

    // PLACE BID (VALUE + TSA TIMESTAMP FOR TIE-BREAK)
    function placeBid(
        uint256 auctionId,
        uint256 bidAmount,
        uint256 tsaTimestamp
    )
        external
        override
    {
        initUser();

        AuctionInfo storage auction = auctions[auctionId];

        // Auction validations
        require(auction.active, "Auction already ended");
        require(block.timestamp < auction.closeDate, "Auction time expired");
        require(msg.sender != auction.seller, "Seller cannot bid on own auction.");

        // Bid validations
        require(bidAmount >= auction.minBid, "Bid below minimum price");
        require(balances[msg.sender] >= bidAmount, "Insufficient balance");

        if (auction.highestBidder == address(0)) {
            _applyNewHighestBid(auction, bidAmount, tsaTimestamp);
        } else {

            if (bidAmount > auction.highestBid) {

                _applyNewHighestBid(auction, bidAmount, tsaTimestamp);
            } else if (bidAmount == auction.highestBid) {

                require(
                    tsaTimestamp < auction.highestBidTimestamp,
                    "Bid loses time tie-break"
                );
                _applyNewHighestBid(auction, bidAmount, tsaTimestamp);
            } else {
                revert("Bid below current highest");
            }
        }

        emit NewBid(auctionId, bidAmount, tsaTimestamp);
    }


    function endAuction(uint256 auctionId) external override {
        AuctionInfo storage auction = auctions[auctionId];

        require(msg.sender == auction.seller, "Only the seller can close the auction");
        require(auction.active, "Auction already closed");

        auction.active = false;
        auction.endedAt = block.timestamp;

        if (auction.highestBid > 0) {
            balances[auction.seller] += auction.highestBid;
        }

        emit AuctionEnded(auctionId, auction.highestBidder, auction.highestBid);
    }


    function getAuctionDuration(uint256 auctionId) external view returns (uint256) {
        AuctionInfo storage auction = auctions[auctionId];
        require(auction.createdAt != 0, "Auction does not exist");
        return auction.closeDate - auction.createdAt;
    }

    function getRealAuctionDuration(uint256 auctionId) external view returns (uint256) {
        AuctionInfo storage auction = auctions[auctionId];
        require(auction.createdAt != 0, "Auction does not exist");

        uint256 endTs = auction.endedAt != 0 ? auction.endedAt : block.timestamp;
        return endTs - auction.createdAt;
    }


    function getAuctionTimes(
        uint256 auctionId
    )
        external
        view
        returns (
            uint256 createdAt,
            uint256 closeDate,
            uint256 highestBidTimestamp,
            uint256 endedAt
        )
    {
        AuctionInfo storage auction = auctions[auctionId];
        require(auction.createdAt != 0, "Auction does not exist");

        return (
            auction.createdAt,
            auction.closeDate,
            auction.highestBidTimestamp,
            auction.endedAt
        );
    }
}
