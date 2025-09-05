#!/usr/bin/env python3
"""
Find and verify Beefy Finance vaults on Arbitrum with harvest fees
"""

import json
import requests
from typing import Dict, List

def fetch_beefy_vaults():
    """Fetch all Beefy vaults and filter for Arbitrum active ones"""
    
    print("🔍 Fetching Beefy vaults...")
    
    # Get all vaults
    vaults_response = requests.get("https://api.beefy.finance/vaults")
    vaults = vaults_response.json()
    
    # Filter for Arbitrum active vaults
    arbitrum_vaults = [
        v for v in vaults 
        if v.get('chain') == 'arbitrum' and v.get('status') == 'active'
    ]
    
    print(f"✅ Found {len(arbitrum_vaults)} active Arbitrum vaults")
    
    return arbitrum_vaults

def fetch_beefy_fees():
    """Fetch call fees for all vaults"""
    
    print("💰 Fetching Beefy fees...")
    
    fees_response = requests.get("https://api.beefy.finance/fees")
    fees = fees_response.json()
    
    return fees

def find_harvestable_vaults(vaults: List[Dict], fees: Dict) -> List[Dict]:
    """Find vaults with non-zero call fees"""
    
    harvestable = []
    
    for vault in vaults:
        vault_id = vault.get('id')
        
        # Check if vault has fees data
        if vault_id in fees:
            vault_fees = fees[vault_id]
            
            # Check for call fee (harvest fee for callers)
            call_fee = vault_fees.get('performance', {}).get('call', 0)
            
            if call_fee > 0:
                harvestable.append({
                    'id': vault_id,
                    'name': vault.get('name', ''),
                    'earnContractAddress': vault.get('earnContractAddress'),
                    'strategy': vault.get('strategy'),
                    'assets': vault.get('assets', []),
                    'callFeeBps': int(call_fee * 10000),  # Convert to basis points
                    'tvl': vault.get('tvl', 0),
                    'apy': vault.get('apy', 0)
                })
    
    return harvestable

def main():
    """Find best Beefy vaults for harvesting"""
    
    print("🧹 Janitor Bot - Beefy Vault Finder")
    print("=" * 50)
    
    # Fetch data
    vaults = fetch_beefy_vaults()
    fees = fetch_beefy_fees()
    
    # Find harvestable vaults
    harvestable = find_harvestable_vaults(vaults, fees)
    
    print(f"\n📊 Found {len(harvestable)} harvestable vaults")
    
    # Sort by TVL for best opportunities
    harvestable.sort(key=lambda x: x.get('tvl', 0), reverse=True)
    
    # Show top 10 candidates
    print("\n🎯 Top 10 Harvest Candidates (by TVL):")
    print("-" * 80)
    
    for i, vault in enumerate(harvestable[:10], 1):
        print(f"\n{i}. {vault['name']}")
        print(f"   Vault Address: {vault['earnContractAddress']}")
        print(f"   Call Fee: {vault['callFeeBps']/100:.2f}% ({vault['callFeeBps']} bps)")
        print(f"   TVL: ${vault['tvl']:,.0f}")
        print(f"   APY: {vault['apy']:.2f}%")
        print(f"   Assets: {', '.join(vault['assets'])}")
        print(f"   Arbiscan: https://arbiscan.io/address/{vault['earnContractAddress']}")
    
    # Save top candidates to file
    top_vaults = harvestable[:5]
    
    with open('beefy_candidates.json', 'w') as f:
        json.dump(top_vaults, f, indent=2)
    
    print(f"\n💾 Saved top {len(top_vaults)} vaults to beefy_candidates.json")
    
    # Generate config snippet
    print("\n📝 Config snippet for targets.json:")
    print("-" * 80)
    
    for vault in top_vaults[:3]:
        config = {
            "name": f"Beefy_{vault['id'].replace('arbitrum-', '')}",
            "address": vault['earnContractAddress'],
            "abi": "abi/beefy_vault.json",
            "type": "harvest",
            "read": {
                "pendingRewards": "balance",
                "lastHarvest": "lastHarvest"
            },
            "write": {
                "exec": "harvest"
            },
            "params": [],
            "rewardToken": vault['earnContractAddress'],
            "rewardTokenDecimals": 18,
            "rewardPriceUSD": 1.0,
            "callFeeBps": vault['callFeeBps'],
            "cooldownSec": 3600,
            "minPendingRewardTokens": "auto",
            "enabled": False,
            "_note": f"{vault['name']} - Verify on Arbiscan first!"
        }
        
        print(json.dumps(config, indent=2))
        print(",")
    
    print("\n⚠️  IMPORTANT: Verify each vault on Arbiscan before enabling!")
    print("   1. Check contract is verified")
    print("   2. Look for harvest() or earn() function")
    print("   3. Check recent harvest transactions")
    print("   4. Update ABI if needed")

if __name__ == "__main__":
    main()