#!/usr/bin/env python3
"""
Find actual Base Beefy strategy addresses
"""

import requests
import json
from web3 import Web3

def find_base_beefy_strategies():
    """Get Base Beefy vaults with strategy addresses"""
    
    print("🔍 Fetching Base Beefy vaults...")
    
    # Get all vaults
    response = requests.get("https://api.beefy.finance/vaults")
    all_vaults = response.json()
    
    # Filter for Base vaults
    base_vaults = [v for v in all_vaults if v.get('chain') == 'base' and v.get('status') == 'active']
    
    print(f"Found {len(base_vaults)} active vaults on Base")
    
    # Get Base-specific vault details with strategies
    base_details = requests.get("https://api.beefy.finance/vaults/base")
    if base_details.status_code == 200:
        base_data = base_details.json()
    else:
        base_data = {}
    
    # Find vaults with good TVL and harvest potential
    harvestable = []
    
    for vault in base_vaults[:50]:  # Check top 50
        vault_id = vault.get('id')
        
        # Try to find strategy address
        if vault.get('strategy'):
            strategy = vault['strategy']
        elif vault.get('strategyAddress'):
            strategy = vault['strategyAddress']
        elif vault_id in base_data and 'strategy' in base_data[vault_id]:
            strategy = base_data[vault_id]['strategy']
        else:
            continue
            
        # Check if it has decent TVL
        tvl = vault.get('tvl', 0)
        if tvl < 50000:  # Skip if less than $50k TVL
            continue
            
        harvestable.append({
            'name': vault_id,
            'strategy': strategy,
            'tvl': tvl,
            'token': vault.get('token', ''),
            'earnedToken': vault.get('earnedToken', ''),
            'platform': vault.get('platformId', '')
        })
    
    # Sort by TVL
    harvestable.sort(key=lambda x: x.get('tvl', 0), reverse=True)
    
    print(f"\n✅ Found {len(harvestable)} harvestable vaults")
    print("\nTop 10 Base Beefy Vaults:")
    print("-" * 60)
    
    for i, vault in enumerate(harvestable[:10]):
        print(f"\n{i+1}. {vault['name']}")
        print(f"   Strategy: {vault['strategy']}")
        print(f"   TVL: ${vault['tvl']:,.0f}")
        print(f"   Platform: {vault['platform']}")
    
    return harvestable

def create_base_targets(vaults):
    """Create targets configuration for Base vaults"""
    
    targets = []
    
    # Select top 3 vaults with highest TVL
    for vault in vaults[:3]:
        target = {
            "name": f"Beefy_{vault['name'].replace('-', '_')}",
            "address": vault['strategy'],
            "abi": "abi/beefy_strategy.json",
            "type": "harvest",
            "enabled": True,
            "params": ["0x00823727Ec5800ae6f5068fABAEb39608dE8bf45"],
            "cooldownSec": 43200,  # 12 hours
            "fixedRewardUSD": 0.30,  # Conservative estimate for Base
            "read": {
                "lastHarvest": "lastHarvest"
            },
            "write": {
                "exec": "harvest"
            },
            "_vault": vault['name'],
            "_tvl": vault['tvl']
        }
        targets.append(target)
    
    return targets

if __name__ == "__main__":
    print("=" * 60)
    print("BASE NETWORK BEEFY STRATEGIES")
    print("=" * 60)
    
    # Find strategies
    vaults = find_base_beefy_strategies()
    
    # Create target configs
    if vaults:
        targets = create_base_targets(vaults)
        
        print("\n" + "=" * 60)
        print("SELECTED BASE TARGETS FOR HARVESTING:")
        print("=" * 60)
        
        for i, target in enumerate(targets):
            print(f"\n{i+1}. {target['name']}")
            print(f"   Address: {target['address']}")
            print(f"   TVL: ${target['_tvl']:,.0f}")
        
        # Save Base targets
        base_config = {
            "base_targets": targets,
            "top_vaults": vaults[:20]
        }
        
        with open('base_targets.json', 'w') as f:
            json.dump(base_config, f, indent=2)
        
        print("\n💾 Saved to base_targets.json")
        print("\n🎯 Ready to add to your janitor bot configuration!")