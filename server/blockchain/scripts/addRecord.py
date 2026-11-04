import json, os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # blockchain/

_w3 = None
_account = None
_contract = None


def _init():
    global _w3, _account, _contract
    if _w3 is not None:
        return

    rpc_url = os.getenv("SEPOLIA_RPC_URL")
    private_key = os.getenv("PRIVATE_KEY")

    if not rpc_url or not private_key:
        raise RuntimeError(
            "SEPOLIA_RPC_URL and PRIVATE_KEY must be set in the environment "
            "to use the blockchain payout feature."
        )

    _w3 = Web3(Web3.HTTPProvider(rpc_url))
    _account = _w3.eth.account.from_key(private_key)

    with open(os.path.join(BASE_DIR, "abi.json")) as f:
        data = json.load(f)

    _contract = _w3.eth.contract(address=data["address"], abi=data["abi"])


def add(farmer, scheme, amount, txnid):
    _init()

    nonce = _w3.eth.get_transaction_count(_account.address)

    tx = _contract.functions.recordPayout(
        farmer, scheme, amount, txnid
    ).build_transaction({
        "from": _account.address,
        "nonce": nonce,
        "gas": 300000,
        "maxFeePerGas": _w3.to_wei("30", "gwei"),
        "maxPriorityFeePerGas": _w3.to_wei("2", "gwei"),
        "chainId": 11155111,
    })

    signed = _w3.eth.account.sign_transaction(tx, os.getenv("PRIVATE_KEY"))
    tx_hash = _w3.eth.send_raw_transaction(signed.raw_transaction)

    print("Sent tx:", tx_hash.hex())
    _w3.eth.wait_for_transaction_receipt(tx_hash)
    print("✅ Added:", txnid)
