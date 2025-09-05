#!/usr/bin/env python3
"""
Quick test of janitor bot with Beefy vaults
"""

import os
import sys
import json
import time
from web3 import Web3
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Connect to Arbitrum
rpc = os.getenv('ARBITRUM_RPC_1')
w3 = Web3(Web3.HTTPProvider(rpc))

if not w3.is_connected():
    print("❌ Failed to connect to Arbitrum")
    sys.exit(1)

print("🧹 Janitor Bot - Beefy Vault Test")
print("=" * 60)
print(f"✅ Connected to Arbitrum")
print(f"📦 Block: {w3.eth.block_number}")
print(f"👛 Address: {os.getenv('ARBITRUM_FROM_ADDRESS')}")
print(f"💰 Balance: {w3.eth.get_balance(os.getenv('ARBITRUM_FROM_ADDRESS')) / 1e18:.6f} ETH")

# Test strategies
strategies = [
    {
        "name": "Beefy MIM-USDC",
        "address": "0xE1fF230cFe84d3Aa6c6C821b499B620D17F45174",
        "tvl": "$5.3M"
    },
    {
        "name": "Beefy USDC/USDT/GHO",
        "address": "0xCcA14Cac1aFD72bc6fb964850936B7a51AEa1E24",
        "tvl": "$3.6M"
    },
    {
        "name": "Beefy tBTC-WBTC",
        "address": "0xa2172783Eafd97FBF25bffFAFda3aD03B5115613",
        "tvl": "$3.3M"
    }
]

# Simple ABI for lastHarvest
abi = [{
    "inputs": [],
    "name": "lastHarvest",
    "outputs": [{"name": "", "type": "uint256"}],
    "stateMutability": "view",
    "type": "function"
}]

print("\n📊 Harvest Status:")
print("-" * 60)

current_time = int(time.time())

for strategy in strategies:
    try:
        contract = w3.eth.contract(address=strategy['address'], abi=abi)
        last_harvest = contract.functions.lastHarvest().call()
        
        time_since = current_time - last_harvest
        hours_since = time_since / 3600
        
        # 12 hour cooldown
        ready = hours_since >= 12
        
        print(f"\n{strategy['name']} ({strategy['tvl']})")
        print(f"  Last harvest: {hours_since:.1f} hours ago")
        print(f"  Status: {'✅ READY FOR HARVEST!' if ready else f'⏰ Wait {12 - hours_since:.1f} more hours'}")
        
        if ready:
            # Estimate gas for harvest
            gas_price = w3.eth.gas_price
            gas_limit = 500000  # Conservative estimate
            gas_cost_eth = (gas_price * gas_limit) / 1e18
            gas_cost_usd = gas_cost_eth * 2500
            
            # Beefy pays 0.05% (5 bps) of harvested amount
            # Need to harvest at least gas_cost / 0.0005 to break even
            min_harvest_usd = gas_cost_usd / 0.0005
            
            print(f"  Gas cost: ${gas_cost_usd:.2f}")
            print(f"  Min harvest for profit: ${min_harvest_usd:.0f}")
            
    except Exception as e:
        print(f"\n{strategy['name']}")
        print(f"  Error: {e}")

print("\n" + "=" * 60)
print("🚀 Run with: python3 -m janitor.janitor")
print("💡 Dry run: python3 -m janitor.janitor --dry-run")