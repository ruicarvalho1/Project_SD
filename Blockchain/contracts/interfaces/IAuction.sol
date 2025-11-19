pragma solidity ^0.8.10;

interface IAuction {
    function createAuction() external returns (uint);
    function placeBid(uint auctionId, uint bidAmount) external;
    function endAuction(uint auctionId) external;
}
