#!/usr/bin/env python3
"""
Test Base connection and find some known harvestable contracts
"""

import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

# Connect to Base
base_rpc = os.getenv('BASE_RPC_1')
if not base_rpc:
    print("❌ BASE_RPC_1 not found in .env")
    exit(1)

w3 = Web3(Web3.HTTPProvider(base_rpc))

print("🔗 Connecting to Base...")
print(f"   RPC: {base_rpc[:50]}...")

if w3.is_connected():
    print("✅ Connected to Base!")
    print(f"   Chain ID: {w3.eth.chain_id}")
    print(f"   Latest block: {w3.eth.block_number:,}")
    print(f"   Gas price: {w3.eth.gas_price / 1e9:.4f} gwei")
else:
    print("❌ Failed to connect to Base")
    exit(1)

# Check wallet balance
wallet = os.getenv('BASE_FROM_ADDRESS')
if wallet:
    balance = w3.eth.get_balance(wallet)
    eth_balance = w3.from_wei(balance, 'ether')
    print(f"\n💰 Wallet Balance:")
    print(f"   Address: {wallet}")
    print(f"   Balance: {eth_balance:.6f} ETH")

# Known harvestable contracts on Base
print("\n📋 Known Base protocols with harvesting:")
print("-" * 50)

known_contracts = [
    {
        "name": "Aerodrome Finance",
        "description": "Base's main DEX",
        "contracts": [
            ("Voter", "0x16613524e02ad97eDfeF371bC883F2F5d6C480A5"),
            ("Gauge Factory", "0x2B6e9d5be2f04b7dE25E7b7a1cD8F3e7b2c5B456")
        ]
    },
    {
        "name": "BaseSwap",
        "description": "Another Base DEX",
        "contracts": [
            ("MasterChef", "0x2B0A43DCcBD7d42c18F6A83F86D1a19fA58d541A")
        ]
    },
    {
        "name": "Moonwell",
        "description": "Lending protocol",
        "contracts": [
            ("Comptroller", "0xfBb21d0380beE3312B33c4353c8936a0F13EF26C")
        ]
    }
]

for protocol in known_contracts:
    print(f"\n{protocol['name']} - {protocol['description']}")
    for name, address in protocol['contracts']:
        print(f"   {name}: {address}")

print("\n" + "=" * 50)
print("✅ Base network is ready for harvesting!")
print("\nNext: We need to find specific Beefy strategy addresses on Base")
print("      These are usually deployed contracts, not in the API")