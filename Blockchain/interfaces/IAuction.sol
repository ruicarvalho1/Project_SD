pragma solidity ^0.8.10;

interface IAuction {

    function createAuction(string memory _desc, uint _duration, uint _minBid) external returns (uint);
    function placeBid(uint256 auctionId,
        uint256 bidAmount,
        uint256 tsaTimestamp ) external;
    function endAuction(uint auctionId) external;
}
