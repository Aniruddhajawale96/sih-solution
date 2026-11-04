import json, os
from web3 import Web3
from solcx import compile_standard, install_solc
from dotenv import load_dotenv

# Load .env from project root
load_dotenv()

RPC = os.getenv("SEPOLIA_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

w3 = Web3(Web3.HTTPProvider(RPC))
account = w3.eth.account.from_key(PRIVATE_KEY)
print("Using wallet:", account.address)

install_solc("0.8.0")

# Read Solidity contract
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blockchain/
contract_path = os.path.join(BASE_DIR, "contracts", "SchemeAudit.sol")

with open(contract_path, "r") as f:
    source = f.read()

compiled = compile_standard(
    {
        "language": "Solidity",
        "sources": {"SchemeAudit.sol": {"content": source}},
        "settings": {"outputSelection": {"*": {"*": ["abi", "evm.bytecode"]}}},
    },
    solc_version="0.8.0",
)

abi = compiled["contracts"]["SchemeAudit.sol"]["SchemeAudit"]["abi"]
bytecode = compiled["contracts"]["SchemeAudit.sol"]["SchemeAudit"]["evm"]["bytecode"]["object"]

contract = w3.eth.contract(abi=abi, bytecode=bytecode)

nonce = w3.eth.get_transaction_count(account.address)

tx = contract.constructor().build_transaction({
    "from": account.address,
    "nonce": nonce,
    "gas": 3000000,
    "maxFeePerGas": w3.to_wei("30", "gwei"),
    "maxPriorityFeePerGas": w3.to_wei("2", "gwei"),
    "chainId": 11155111,  # Sepolia
})

signed = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)

print("Deploying... tx:", tx_hash.hex())
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

print("✅ Contract deployed at:", receipt.contractAddress)

# Save ABI + address in blockchain/abi.json
out_path = os.path.join(BASE_DIR, "abi.json")
with open(out_path, "w") as f:
    json.dump({
        "address": receipt.contractAddress,
        "abi": abi
    }, f, indent=2)

print("✅ Saved abi.json")
