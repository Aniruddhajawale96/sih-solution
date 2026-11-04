import os
from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC_URL = os.getenv("SEPOLIA_RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

print("RPC URL:", RPC_URL[:40] + "..." if RPC_URL else "❌ NOT SET")
print("Private key loaded:", "✅ YES" if PRIVATE_KEY else "❌ NO")

# Connect to Sepolia
w3 = Web3(Web3.HTTPProvider(RPC_URL))

print("Connected to network:", w3.is_connected())

if not w3.is_connected():
    print("❌ Could not connect to Sepolia. Check RPC URL.")
    exit(1)

# Get chain id
chain_id = w3.eth.chain_id
print("Chain ID:", chain_id, "(Should be 11155111 for Sepolia)")

# Get latest block
latest_block = w3.eth.block_number
print("Latest block number:", latest_block)

# Load account from private key
account = w3.eth.account.from_key(PRIVATE_KEY)
print("Backend wallet address:", account.address)

# Get balance
balance_wei = w3.eth.get_balance(account.address)
balance_eth = w3.from_wei(balance_wei, "ether")

print("Wallet balance:", balance_eth, "Sepolia ETH")

if balance_wei == 0:
    print("⚠️ WARNING: Wallet has 0 ETH. You need faucet funds to send transactions.")
else:
    print("✅ Wallet has funds, ready to send transactions.")
