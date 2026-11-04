// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract SchemeAudit {

    address public owner;

    constructor() {
        owner = msg.sender;
    }

    struct PayoutRecord {
        address farmer;
        string schemeName;
        uint256 amount;
        string bankTxnId;
        uint256 timestamp;
    }

    PayoutRecord[] private records;

    mapping(string => uint256) private txnIdToIndex;
    mapping(string => bool) private txnExists;

    modifier onlyOwner() {
        require(msg.sender == owner, "Not authorized");
        _;
    }

    function recordPayout(
        address farmer,
        string memory schemeName,
        uint256 amount,
        string memory bankTxnId
    ) public onlyOwner {

        require(!txnExists[bankTxnId], "Txn already exists");

        records.push(PayoutRecord(
            farmer,
            schemeName,
            amount,
            bankTxnId,
            block.timestamp
        ));

        uint256 idx = records.length - 1;
        txnIdToIndex[bankTxnId] = idx;
        txnExists[bankTxnId] = true;
    }

    function getRecordCount() public view returns (uint256) {
        return records.length;
    }

    function getRecord(uint256 index) public view returns (
        address,
        string memory,
        uint256,
        string memory,
        uint256
    ) {
        PayoutRecord memory r = records[index];
        return (r.farmer, r.schemeName, r.amount, r.bankTxnId, r.timestamp);
    }

    function getByTxnId(string memory txnId) public view returns (
        address,
        string memory,
        uint256,
        string memory,
        uint256
    ) {
        require(txnExists[txnId], "Txn not found");
        uint256 idx = txnIdToIndex[txnId];
        return getRecord(idx);
    }
}
