pragma solidity ^0.8.10;

interface IBalances {
    function getBalance(address account) external view returns (uint);
}
