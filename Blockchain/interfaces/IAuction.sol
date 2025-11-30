pragma solidity ^0.8.10;

interface IAuction {

    function createAuction(string memory _desc, uint _duration, uint _minBid) external returns (uint);
    function placeBid(uint auctionId, uint bidAmount) external;
    function endAuction(uint auctionId) external;
}
