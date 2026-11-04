import json, os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

w3 = Web3(Web3.HTTPProvider(os.getenv("SEPOLIA_RPC_URL")))

with open(os.path.join(BASE_DIR, "abi.json")) as f:
    data = json.load(f)

contract = w3.eth.contract(address=data["address"], abi=data["abi"])

count = contract.functions.getRecordCount().call()
print("Total records:", count)

for i in range(count):
    print(f"Record {i}:", contract.functions.getRecord(i).call())

print("\nSearch TXN1001:")
print(contract.functions.getByTxnId("TXN1001").call())