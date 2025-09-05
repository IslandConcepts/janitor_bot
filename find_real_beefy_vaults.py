#!/usr/bin/env python3
"""
Find real Beefy Finance vaults on Arbitrum with actual TVL and harvest fees
Following Beefy's actual API structure
"""

import json
import requests
from typing import Dict, List
from datetime import datetime

ARBITRUM_CHAIN_ID = "42161"
MIN_TVL = 10000  # $10k minimum TVL
DEFAULT_CALLER_FEE_BPS = 5  # 0.05% default caller fee per Beefy policy

def fetch_data():
    """Fetch all required data from Beefy APIs"""
    print("🔍 Fetching Beefy data...")
    
    # Get all vaults
    vaults_response = requests.get("https://api.beefy.finance/vaults")
    vaults = vaults_response.json()
    
    # Get TVL data (keyed by chainId)
    tvl_response = requests.get("https://api.beefy.finance/tvl")
    tvl_data = tvl_response.json()
    
    # Get fees data
    fees_response = requests.get("https://api.beefy.finance/fees")
    fees_data = fees_response.json()
    
    # Get APY data
    apy_response = requests.get("https://api.beefy.finance/apy")
    apy_data = apy_response.json()
    
    print(f"✅ Fetched {len(vaults)} total vaults")
    
    return vaults, tvl_data, fees_data, apy_data

def process_arbitrum_vaults(vaults, tvl_data, fees_data, apy_data):
    """Process and filter Arbitrum vaults with TVL"""
    
    # Get Arbitrum TVL data
    arbitrum_tvl = tvl_data.get(ARBITRUM_CHAIN_ID, {})
    
    print(f"📊 Found {len(arbitrum_tvl)} Arbitrum vaults with TVL data")
    
    # Filter active Arbitrum vaults
    arbitrum_vaults = []
    
    for vault in vaults:
        # Check if it's an active Arbitrum vault
        if vault.get('chain') != 'arbitrum' or vault.get('status') != 'active':
            continue
        
        vault_id = vault['id']
        
        # Get TVL for this vault
        tvl = arbitrum_tvl.get(vault_id, 0)
        
        # Skip if TVL too low
        if tvl < MIN_TVL:
            continue
        
        # Get fees for this vault
        vault_fees = fees_data.get(vault_id, {})
        performance_fees = vault_fees.get('performance', {})
        
        # Get caller fee (harvest fee)
        # Beefy standard: caller gets 0.05% of performance fees
        caller_fee = performance_fees.get('call', 0)
        if caller_fee == 0:
            # Use default policy of 0.05% if not specified
            caller_fee = 0.0005  # 0.05%
        
        # Get APY
        apy = apy_data.get(vault_id, 0)
        
        # Build vault data
        vault_data = {
            'id': vault_id,
            'name': vault.get('name', ''),
            'earnContractAddress': vault.get('earnContractAddress'),
            'strategy': vault.get('strategy'),
            'tvl': tvl,
            'apy': apy,
            'caller_fee_pct': caller_fee * 100,
            'caller_fee_bps': int(caller_fee * 10000),
            'assets': vault.get('assets', []),
            'token': vault.get('token', ''),
            'tokenDecimals': vault.get('tokenDecimals', 18)
        }
        
        arbitrum_vaults.append(vault_data)
    
    # Sort by TVL
    arbitrum_vaults.sort(key=lambda x: x['tvl'], reverse=True)
    
    return arbitrum_vaults

def fetch_clm_harvests(vault_address: str):
    """Fetch CLM harvest history for a vault"""
    try:
        url = f"https://api.beefy.finance/cow-api/clm/{ARBITRUM_CHAIN_ID}/{vault_address}/harvests"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return []

def main():
    print("🧹 Janitor Bot - Real Beefy Vault Finder")
    print("=" * 80)
    
    # Fetch all data
    vaults, tvl_data, fees_data, apy_data = fetch_data()
    
    # Process Arbitrum vaults
    arbitrum_vaults = process_arbitrum_vaults(vaults, tvl_data, fees_data, apy_data)
    
    print(f"\n✅ Found {len(arbitrum_vaults)} Arbitrum vaults with TVL > ${MIN_TVL:,}")
    
    # Show top vaults
    print("\n🎯 Top 20 Arbitrum Vaults by TVL:")
    print("-" * 100)
    print(f"{'#':<3} {'Name':<30} {'TVL':<15} {'APY':<8} {'Fee':<6} {'Type'}")
    print("-" * 100)
    
    top_vaults = []
    for i, vault in enumerate(arbitrum_vaults[:20], 1):
        # Check if it's a CLM vault
        vault_type = "CLM" if "clm" in vault['id'].lower() else "Standard"
        
        print(f"{i:<3} {vault['name'][:30]:<30} ${vault['tvl']:>13,.0f} {vault['apy']:>6.1f}% {vault['caller_fee_bps']:>4}bp {vault_type}")
        
        # Try to get CLM harvest data for top 10
        if i <= 10:
            harvests = fetch_clm_harvests(vault['earnContractAddress'])
            if harvests:
                vault['harvest_count'] = len(harvests)
                vault['last_harvest'] = harvests[0].get('timestamp') if harvests else None
            top_vaults.append(vault)
    
    # Show detailed info for top candidates
    print("\n📋 Top Harvest Candidates:")
    print("-" * 100)
    
    for i, vault in enumerate(top_vaults[:5], 1):
        print(f"\n{i}. {vault['name']}")
        print(f"   Contract: {vault['earnContractAddress']}")
        print(f"   TVL: ${vault['tvl']:,.0f}")
        print(f"   APY: {vault['apy']:.2f}%")
        print(f"   Caller Fee: {vault['caller_fee_pct']:.3f}% ({vault['caller_fee_bps']} bps)")
        print(f"   Token: {vault['token']}")
        print(f"   Strategy: {vault['strategy'][:50]}...")
        if vault.get('harvest_count'):
            print(f"   Recent Harvests: {vault['harvest_count']} found")
        print(f"   Verify: https://arbiscan.io/address/{vault['earnContractAddress']}#code")
    
    # Generate config for targets.json
    print("\n💾 Config for targets.json:")
    print("-" * 100)
    
    configs = []
    for vault in top_vaults[:3]:
        config = {
            "name": f"Beefy_{vault['id'].replace('arbitrum-', '')[:20]}",
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
            "rewardToken": vault.get('earnedToken', vault['earnContractAddress']),
            "rewardTokenDecimals": vault.get('tokenDecimals', 18),
            "rewardPriceUSD": 1.0,
            "callFeeBps": vault['caller_fee_bps'],
            "cooldownSec": 3600,
            "minPendingRewardTokens": "auto",
            "tvl": vault['tvl'],
            "apy": vault['apy'],
            "enabled": False,
            "_note": f"{vault['name']} - TVL: ${vault['tvl']:,.0f}",
            "_verify": f"https://arbiscan.io/address/{vault['earnContractAddress']}#code"
        }
        configs.append(config)
    
    # Save to file
    output = {
        "timestamp": datetime.now().isoformat(),
        "vaults": configs,
        "summary": {
            "total_vaults": len(arbitrum_vaults),
            "total_tvl": sum(v['tvl'] for v in arbitrum_vaults),
            "avg_apy": sum(v['apy'] for v in arbitrum_vaults) / len(arbitrum_vaults) if arbitrum_vaults else 0
        }
    }
    
    with open('real_beefy_targets.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(json.dumps(configs[0], indent=2))
    
    print(f"\n✅ Saved {len(configs)} vault configs to real_beefy_targets.json")
    print("\n⚠️  Next Steps:")
    print("1. Verify each vault on Arbiscan")
    print("2. Check for harvest() or earn() function")
    print("3. Look at recent transactions for harvest frequency")
    print("4. Download and add the correct ABI if needed")
    print("5. Enable vaults one by one after verification")

if __name__ == "__main__":
    main()