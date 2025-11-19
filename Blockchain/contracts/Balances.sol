pragma solidity ^0.8.10;

import "./interfaces/IBalances.sol";



contract Balances is IBalances {
    mapping(address => uint) internal balances;

    function setInitialBalance(address user, uint amount) internal {
        balances[user] = amount;
    }

    function claimBalance() external {
    require(balances[msg.sender] == 0, "Already claimed");
    balances[msg.sender] = 100;
}


    function getBalance(address user) external view override returns(uint) {
        return balances[user];
    }
}
