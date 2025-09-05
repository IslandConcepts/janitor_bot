#!/usr/bin/env python3
"""
Debug why harvest isn't triggering
"""

import os
import time
from web3 import Web3
from dotenv import load_dotenv
from janitor.config import load_config
# from janitor.profit import estimate_profit  # Not needed for debug

load_dotenv()

print("🔍 Debugging Harvest Decision...")
print("=" * 60)

# Connect to Arbitrum
rpc = os.getenv('ARBITRUM_RPC_1')
w3 = Web3(Web3.HTTPProvider(rpc))

# Load config
config = load_config()

# Get tBTC_WBTC target
target = None
for t in config['chains']['arbitrum']['targets']:
    if t['name'] == 'Beefy_tBTC_WBTC':
        target = t
        break

if not target:
    print("❌ tBTC_WBTC not found in config!")
    exit(1)

print(f"📋 Target: {target['name']}")
print(f"   Address: {target['address']}")
print(f"   Enabled: {target.get('enabled', False)}")
print(f"   Type: {target['type']}")
print(f"   Cooldown: {target.get('cooldownSec', 0)}s")

# Check last harvest
abi = [{'inputs': [], 'name': 'lastHarvest', 'outputs': [{'type': 'uint256'}], 'stateMutability': 'view', 'type': 'function'}]
contract = w3.eth.contract(address=target['address'], abi=abi)

try:
    last_harvest = contract.functions.lastHarvest().call()
    current_time = int(time.time())
    time_since = current_time - last_harvest
    
    print(f"\n⏰ Cooldown Check:")
    print(f"   Last harvest: {time_since / 3600:.1f} hours ago")
    print(f"   Required cooldown: {target.get('cooldownSec', 0) / 3600:.1f} hours")
    print(f"   Ready: {'✅ YES' if time_since >= target.get('cooldownSec', 0) else '❌ NO'}")
    
except Exception as e:
    print(f"❌ Error reading lastHarvest: {e}")

# Check profit gate
print(f"\n💰 Profit Gate Check:")

# Gas estimate
gas_price = w3.eth.gas_price
gas_limit = 500000  # Conservative
gas_cost_wei = gas_price * gas_limit
gas_cost_eth = gas_cost_wei / 1e18
gas_cost_usd = gas_cost_eth * 2500  # ETH price

print(f"   Gas price: {gas_price / 1e9:.2f} gwei")
print(f"   Gas limit: {gas_limit:,}")
print(f"   Gas cost: ${gas_cost_usd:.2f}")

# Profit calculation
# With 0.05% fee (5 bps), need to harvest at least:
min_harvest_value = gas_cost_usd / 0.0005
print(f"   Min harvest value for profit: ${min_harvest_value:.0f}")

# Profit multiplier check
profit_multiplier = config.get('global', {}).get('profitMultiplier', 1.5)
min_required = gas_cost_usd * profit_multiplier
print(f"   Profit multiplier: {profit_multiplier}x")
print(f"   Min reward needed: ${min_required:.2f}")
print(f"   Min harvest for {profit_multiplier}x: ${min_required / 0.0005:.0f}")

# Check if profit gate is preventing harvest
if target.get('type') == 'harvest':
    # For harvest type, check if we're using fixedRewardUSD
    if 'fixedRewardUSD' in target:
        fixed_reward = target['fixedRewardUSD']
        print(f"\n📌 Using fixedRewardUSD: ${fixed_reward}")
        print(f"   Passes profit gate: {'✅ YES' if fixed_reward >= min_required else '❌ NO'}")
        if fixed_reward < min_required:
            print(f"   ⚠️  Fixed reward ${fixed_reward} < required ${min_required:.2f}")
            print(f"   Solution: Increase fixedRewardUSD in targets.json or wait for lower gas")

print("\n🔧 Troubleshooting:")
print("1. If cooldown ready but not harvesting:")
print("   - Check profit gate settings")
print("   - Try increasing fixedRewardUSD in targets.json")
print("   - Or set minPendingRewardTokens to 0")
print("2. Run with --dry-run to see detailed output")
print("3. Check if bot is actually running (ps aux | grep janitor)")