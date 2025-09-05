#!/usr/bin/env python3
"""
Test GMX compound function
"""

import os
import sys
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to Arbitrum
rpc_url = os.getenv('ARBITRUM_RPC_1')
if not rpc_url:
    print("Error: ARBITRUM_RPC_1 not set in .env")
    sys.exit(1)

w3 = Web3(Web3.HTTPProvider(rpc_url))

# Check connection
if not w3.is_connected():
    print("Failed to connect to Arbitrum RPC")
    sys.exit(1)

print(f"✅ Connected to Arbitrum")
print(f"Block number: {w3.eth.block_number}")

# Get our address
our_address = os.getenv('ARBITRUM_FROM_ADDRESS')
print(f"Our address: {our_address}")
print(f"ETH balance: {w3.eth.get_balance(our_address) / 1e18:.6f} ETH")

# GMX RewardRouterV2 contract
gmx_address = "0xA906F338CB21815cBc4Bc87ace9e68c87eF8d8F1"

# Simple ABI to check claimableRewards
abi = [
    {
        "inputs": [{"name": "_account", "type": "address"}],
        "name": "claimableRewards",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

contract = w3.eth.contract(address=gmx_address, abi=abi)

try:
    # Check claimable rewards for our address
    rewards = contract.functions.claimableRewards(our_address).call()
    print(f"\n📊 GMX Claimable Rewards: {rewards / 1e18:.6f} esGMX")
    
    if rewards > 0:
        print("✅ Has rewards to compound!")
    else:
        print("❌ No rewards available to compound")
        
except Exception as e:
    print(f"Error checking rewards: {e}")

print("\nNote: You need to stake GMX or GLP to earn rewards")