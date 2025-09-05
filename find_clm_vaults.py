#!/usr/bin/env python3
"""
Find Beefy CLM (Concentrated Liquidity Manager) vaults on Arbitrum
CLM vaults typically have more frequent harvests
"""

import json
import requests
from typing import Dict, List

ARBITRUM_CHAIN_ID = "42161"
MIN_TVL = 10000  # $10k minimum

def main():
    print("🔍 Finding CLM vaults on Arbitrum...")
    
    # Get CLM vaults
    clm_response = requests.get("https://api.beefy.finance/cow-vaults")
    clm_vaults = clm_response.json()
    
    # Get TVL data
    tvl_response = requests.get("https://api.beefy.finance/tvl")
    tvl_data = tvl_response.json()
    arbitrum_tvl = tvl_data.get(ARBITRUM_CHAIN_ID, {})
    
    # Get fees data
    fees_response = requests.get("https://api.beefy.finance/fees")
    fees_data = fees_response.json()
    
    # Filter Arbitrum CLM vaults
    arb_clm = []
    
    for vault in clm_vaults:
        if vault.get('chain') == 'arbitrum' and vault.get('status') == 'active':
            vault_id = vault['id']
            tvl = arbitrum_tvl.get(vault_id, 0)
            
            if tvl > MIN_TVL:
                # Get fees
                vault_fees = fees_data.get(vault_id, {})
                perf_fees = vault_fees.get('performance', {})
                call_fee = perf_fees.get('call', 0)
                
                # CLM vaults often have higher call fees
                if call_fee == 0:
                    call_fee = 0.005  # 0.5% default for CLM
                
                arb_clm.append({
                    'id': vault_id,
                    'name': vault.get('name', ''),
                    'address': vault.get('earnContractAddress'),
                    'strategy': vault.get('strategyAddress'),
                    'tvl': tvl,
                    'type': vault.get('type', 'clm'),
                    'call_fee': call_fee,
                    'call_fee_bps': int(call_fee * 10000)
                })
    
    # Sort by TVL
    arb_clm.sort(key=lambda x: x['tvl'], reverse=True)
    
    print(f"✅ Found {len(arb_clm)} CLM vaults with TVL > ${MIN_TVL:,}")
    
    if len(arb_clm) > 0:
        print("\n🎯 Top CLM Vaults:")
        print("-" * 90)
        
        for i, vault in enumerate(arb_clm[:10], 1):
            print(f"\n{i}. {vault['name']}")
            print(f"   Address: {vault['address']}")
            print(f"   Strategy: {vault['strategy']}")
            print(f"   TVL: ${vault['tvl']:,.0f}")
            print(f"   Call Fee: {vault['call_fee_bps']} bps")
            print(f"   Verify: https://arbiscan.io/address/{vault['address']}#code")
        
        # Save top CLM vaults
        with open('clm_vaults.json', 'w') as f:
            json.dump(arb_clm[:5], f, indent=2)
        
        print(f"\n💾 Saved top {min(5, len(arb_clm))} CLM vaults to clm_vaults.json")
    else:
        print("\n❌ No CLM vaults found on Arbitrum with sufficient TVL")

if __name__ == "__main__":
    main()