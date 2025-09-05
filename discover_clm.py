#!/usr/bin/env python3
"""
Discover CLM strategy addresses on-chain via multicall
"""

import json
import requests
from web3 import Web3
from typing import List, Dict, Any, Optional
import time

# Configuration
RPC = "https://arb-mainnet.g.alchemy.com/v2/5mlDO-31svMGY53J2Urqv"
w3 = Web3(Web3.HTTPProvider(RPC))

# Multicall3 contract on Arbitrum
MULTICALL3 = Web3.to_checksum_address("0xcA11bde05977b3631167028862bE2a173976CA11")

# Minimal ABIs
VAULT_ABI = json.loads("""[
    {"inputs":[],"name":"strategy","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"manager","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"clmManager","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"want","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"lastHarvest","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
]""")

STRATEGY_ABI = json.loads("""[
    {"inputs":[],"name":"harvest","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[{"internalType":"address","name":"callFeeRecipient","type":"address"}],"name":"harvest","outputs":[],"stateMutability":"nonpayable","type":"function"},
    {"inputs":[],"name":"lastHarvest","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[],"name":"harvestOnDeposit","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"}
]""")

MULTICALL_ABI = json.loads("""[{
    "inputs":[
        {"components":[
            {"internalType":"address","name":"target","type":"address"},
            {"internalType":"bytes","name":"callData","type":"bytes"}
        ],
        "internalType":"struct Multicall3.Call[]","name":"calls","type":"tuple[]"}
    ],
    "name":"aggregate",
    "outputs":[
        {"internalType":"uint256","name":"blockNumber","type":"uint256"},
        {"internalType":"bytes[]","name":"returnData","type":"bytes[]"}
    ],
    "stateMutability":"nonpayable","type":"function"
}]""")

def get_clm_vaults() -> List[Dict]:
    """Fetch CLM vault addresses from Beefy API"""
    print("📋 Fetching CLM vaults from API...")
    
    # Get CLM vaults
    response = requests.get("https://api.beefy.finance/cow-vaults")
    clm_vaults = response.json()
    
    # Filter for Arbitrum active CLM vaults
    arb_clm = []
    for vault in clm_vaults:
        if (vault.get('chain') == 'arbitrum' and 
            vault.get('status') == 'active' and
            vault.get('earnContractAddress')):  # This is the vault address
            arb_clm.append({
                'id': vault.get('id', ''),
                'address': vault['earnContractAddress'],
                'type': vault.get('type', 'cowcentrated'),
                'tvl': vault.get('tvl', 0),
                'platform': vault.get('tokenProviderId', '')
            })
    
    print(f"  Found {len(arb_clm)} Arbitrum CLM vaults")
    return arb_clm

def fetch_strategies_multicall(vault_addrs: List[str]) -> List[Dict]:
    """Fetch strategy addresses via multicall"""
    print(f"\n🔍 Resolving strategies for {len(vault_addrs)} vaults via multicall...")
    
    if not vault_addrs:
        return []
    
    mc = w3.eth.contract(MULTICALL3, abi=MULTICALL_ABI)
    calls = []
    
    # Build calls for each vault - try multiple getters
    for v in vault_addrs:
        vault_addr = Web3.to_checksum_address(v)
        vault = w3.eth.contract(vault_addr, abi=VAULT_ABI)
        
        # Try strategy() first
        calls.append((vault_addr, vault.functions.strategy().build_transaction()['data']))
    
    # Execute multicall
    try:
        _, return_data = mc.functions.aggregate(calls).call()
    except Exception as e:
        print(f"  ❌ Multicall failed: {e}")
        return []
    
    # Parse results
    results = []
    for i, (vault_addr, ret_bytes) in enumerate(zip(vault_addrs, return_data)):
        if ret_bytes and len(ret_bytes) >= 32:
            # Extract address from bytes32
            strategy_addr = "0x" + ret_bytes.hex()[-40:]
            if strategy_addr != "0x" + "0"*40:  # Not zero address
                results.append({
                    'vault': vault_addr,
                    'strategy': Web3.to_checksum_address(strategy_addr)
                })
            else:
                # Try manager as fallback
                results.append({
                    'vault': vault_addr,
                    'strategy': None
                })
        else:
            results.append({
                'vault': vault_addr,
                'strategy': None
            })
    
    success_count = sum(1 for r in results if r['strategy'])
    print(f"  ✅ Resolved {success_count}/{len(vault_addrs)} strategies")
    
    return results

def check_harvest_signature(strategy_addr: str) -> Dict:
    """Check which harvest signature the strategy uses"""
    print(f"  Checking harvest signature for {strategy_addr[:10]}...")
    
    contract = w3.eth.contract(Web3.to_checksum_address(strategy_addr), abi=STRATEGY_ABI)
    
    # Check for harvest() with no params
    try:
        # Try to encode harvest() - if it works, the function exists
        contract.functions.harvest().build_transaction()
        has_simple = True
    except:
        has_simple = False
    
    # Check for harvest(address)
    try:
        contract.functions.harvest("0x0000000000000000000000000000000000000000").build_transaction()
        has_address = True
    except:
        has_address = False
    
    # Check lastHarvest
    try:
        last_harvest = contract.functions.lastHarvest().call()
        has_last_harvest = True
    except:
        last_harvest = 0
        has_last_harvest = False
    
    return {
        'has_harvest': has_simple,
        'has_harvest_address': has_address,
        'has_lastHarvest': has_last_harvest,
        'lastHarvest': last_harvest
    }

def build_target_entry(vault_data: Dict, strategy_data: Dict, sig_data: Dict) -> Dict:
    """Build a target entry for targets.json"""
    
    # Determine harvest function and params
    if sig_data['has_harvest_address']:
        exec_func = "harvest"
        params = ["0x00823727Ec5800ae6f5068fABAEb39608dE8bf45"]  # Your bot address
    elif sig_data['has_harvest']:
        exec_func = "harvest"
        params = []
    else:
        # Unknown harvest method
        return None
    
    # Check if recently harvested (within 24 hours)
    now = int(time.time())
    if sig_data['lastHarvest'] > 0:
        hours_since = (now - sig_data['lastHarvest']) / 3600
        recently_harvested = hours_since < 24
    else:
        recently_harvested = False
    
    target = {
        "name": f"CLM_{vault_data['id'].replace('-', '_')[:30]}",
        "address": strategy_data['strategy'],
        "abi": "abi/beefy_strategy.json",
        "type": "harvest",
        "enabled": True,
        "params": params,
        "cooldownSec": 21600,  # 6 hours for CLM
        "fixedRewardUSD": 0.30,
        "skipProfitGate": False,
        "read": {},
        "write": {
            "exec": exec_func
        },
        "_vault": vault_data['address'],
        "_tvl": vault_data['tvl'],
        "_platform": vault_data['platform'],
        "_recently_harvested": recently_harvested
    }
    
    # Add lastHarvest read if available
    if sig_data['has_lastHarvest']:
        target['read']['lastHarvest'] = 'lastHarvest'
    
    return target

def main():
    print("=" * 60)
    print("CLM STRATEGY DISCOVERY VIA ON-CHAIN MULTICALL")
    print("=" * 60)
    
    # Step 1: Get CLM vaults
    clm_vaults = get_clm_vaults()
    
    # Sort by TVL and take top 20
    clm_vaults.sort(key=lambda x: x['tvl'], reverse=True)
    top_vaults = clm_vaults[:20]
    
    if not top_vaults:
        print("❌ No CLM vaults found")
        return
    
    print(f"\n📊 Top {len(top_vaults)} CLM vaults by TVL:")
    for i, v in enumerate(top_vaults[:5]):
        print(f"  {i+1}. {v['id']}: ${v['tvl']:,.0f}")
    
    # Step 2: Resolve strategies via multicall
    vault_addresses = [v['address'] for v in top_vaults]
    strategy_results = fetch_strategies_multicall(vault_addresses)
    
    # Step 3: Check harvest signatures for resolved strategies
    valid_targets = []
    
    print("\n🔎 Checking harvest signatures...")
    for vault, strat_data in zip(top_vaults, strategy_results):
        if not strat_data['strategy']:
            continue
        
        # Check harvest signature
        sig_data = check_harvest_signature(strat_data['strategy'])
        
        # Build target if valid
        if sig_data['has_harvest'] or sig_data['has_harvest_address']:
            target = build_target_entry(vault, strat_data, sig_data)
            if target:
                valid_targets.append(target)
                print(f"  ✅ {vault['id']}: Valid harvest found")
                if sig_data['lastHarvest'] > 0:
                    hours_ago = (time.time() - sig_data['lastHarvest']) / 3600
                    print(f"      Last harvest: {hours_ago:.1f} hours ago")
    
    # Step 4: Output results
    print("\n" + "=" * 60)
    print(f"RESULTS: {len(valid_targets)} HARVESTABLE CLM VAULTS FOUND")
    print("=" * 60)
    
    if valid_targets:
        # Sort by TVL
        valid_targets.sort(key=lambda x: x['_tvl'], reverse=True)
        
        print("\n📝 Ready to add to targets.json:")
        for i, target in enumerate(valid_targets[:5]):  # Show top 5
            print(f"\n{i+1}. {target['name']}")
            print(f"   Strategy: {target['address']}")
            print(f"   TVL: ${target['_tvl']:,.0f}")
            print(f"   Platform: {target['_platform']}")
            print(f"   Params: {target['params']}")
            print(f"   Recently harvested: {target['_recently_harvested']}")
        
        # Save to file
        output = {
            'discovered_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'chain': 'arbitrum',
            'valid_targets': valid_targets,
            'total_found': len(valid_targets)
        }
        
        with open('clm_targets_discovered.json', 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Saved {len(valid_targets)} targets to clm_targets_discovered.json")
        print("\n🎯 Next steps:")
        print("  1. Review the targets in clm_targets_discovered.json")
        print("  2. Add top performing ones to your targets.json")
        print("  3. Restart the bot to begin harvesting CLM vaults")
    else:
        print("\n⚠️ No valid harvestable CLM vaults found")
        print("   This could mean:")
        print("   - Strategies use different function names")
        print("   - They require special permissions")
        print("   - Need to check manager contracts instead")

if __name__ == "__main__":
    main()