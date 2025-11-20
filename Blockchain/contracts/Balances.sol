// SPDX-License-Identifier: MIT
pragma solidity ^0.8.10;

import "../interfaces/IBalances.sol";

contract Balances is IBalances {
    mapping(address => uint256) internal balances;
    mapping(address => bool) internal initialized;

    uint256 public constant INITIAL_BALANCE = 1000;

    function _ensureInit(address user) internal {
        if (!initialized[user]) {
            initialized[user] = true;
            balances[user] = INITIAL_BALANCE;
        }
    }

    function initUser() internal {
        _ensureInit(msg.sender);
    }


    function getBalance(address user) external view override returns (uint256) {

        if (!initialized[user]) {
            return INITIAL_BALANCE;
        }
        return balances[user];
    }
}
