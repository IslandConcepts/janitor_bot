#!/usr/bin/env python3
"""
Check what the janitor bot is doing
"""

import time
from web3 import Web3
from janitor.config import load_config
from janitor.storage import Database
import os
from dotenv import load_dotenv

load_dotenv()

print("🔍 Checking Janitor Bot Status...")
print("=" * 60)

# Load config
config = load_config()

# Check targets
print("\n📋 Configured Targets:")
for chain_name, chain_config in config['chains'].items():
    for target in chain_config.get('targets', []):
        enabled = "✅" if target.get('enabled', False) else "❌"
        print(f"  {enabled} {target['name']}")

# Check database for recent activity
db = Database("data/janitor.db")

print("\n📊 Recent Activity:")
with db.get_conn() as conn:
    # Last 5 runs
    runs = conn.execute('''
        SELECT target, timestamp, status, net_usd
        FROM runs
        ORDER BY timestamp DESC
        LIMIT 5
    ''').fetchall()
    
    if runs:
        for run in runs:
            time_ago = int(time.time() - run['timestamp'])
            hours = time_ago // 3600
            mins = (time_ago % 3600) // 60
            print(f"  {run['target']}: {hours}h {mins}m ago - {run['status']}")
    else:
        print("  No runs recorded yet")

# Check current cooldowns
print("\n⏰ Cooldown Status:")
rpc = os.getenv('ARBITRUM_RPC_1')
w3 = Web3(Web3.HTTPProvider(rpc))

strategies = [
    ("Beefy_MIM_USDC", "0xE1fF230cFe84d3Aa6c6C821b499B620D17F45174"),
    ("Beefy_USDC_USDT_GHO", "0xCcA14Cac1aFD72bc6fb964850936B7a51AEa1E24"),
    ("Beefy_tBTC_WBTC", "0xa2172783Eafd97FBF25bffFAFda3aD03B5115613")
]

abi = [{'inputs': [], 'name': 'lastHarvest', 'outputs': [{'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]
current_time = int(time.time())

for name, addr in strategies:
    try:
        contract = w3.eth.contract(address=addr, abi=abi)
        last_harvest = contract.functions.lastHarvest().call()
        time_since = current_time - last_harvest
        hours = time_since / 3600
        
        if hours >= 12:
            print(f"  {name}: ✅ READY ({hours:.1f}h ago)")
        else:
            remaining = 12 - hours
            print(f"  {name}: ⏰ {remaining:.1f}h remaining")
    except Exception as e:
        print(f"  {name}: ❌ Error: {e}")

print("\n🤖 Bot should be:")
print("  1. Polling every 5 seconds")
print("  2. Checking cooldowns")
print("  3. Evaluating profit gates")
print("  4. Harvesting when ready")
print("\nIf stuck, try:")
print("  - Ctrl+C and restart")
print("  - Check logs/janitor.log for errors")
print("  - Run with --dry-run first")