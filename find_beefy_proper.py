#!/usr/bin/env python3
"""
Find real harvestable Beefy vaults on Arbitrum using proper API approach
"""

import json
import requests
from typing import Dict, List

ARBITRUM_CHAIN_ID = "42161"
MIN_TVL = 50000  # $50k minimum for good activity

def main():
    print("🧹 Finding Real Beefy Vaults on Arbitrum")
    print("=" * 80)
    
    # 1. Get all vaults
    print("\n1️⃣ Fetching vault metadata...")
    vaults_response = requests.get("https://api.beefy.finance/vaults")
    all_vaults = vaults_response.json()
    
    # Filter Arbitrum active vaults
    arb_vaults = [v for v in all_vaults 
                  if v.get('chain') == 'arbitrum' 
                  and v.get('status') == 'active'
                  and v.get('strategy')  # Must have a strategy (non-CLM)
                  and 'clm' not in v.get('id', '').lower()]  # Skip CLM for now
    
    print(f"   Found {len(arb_vaults)} active standard vaults on Arbitrum")
    
    # 2. Get fee policies
    print("\n2️⃣ Fetching fee policies...")
    fees_response = requests.get("https://api.beefy.finance/fees")
    fees_data = fees_response.json()
    
    # 3. Get TVL data (proper way - by chainId)
    print("\n3️⃣ Fetching TVL data...")
    tvl_response = requests.get("https://api.beefy.finance/tvl")
    tvl_data = tvl_response.json()
    arbitrum_tvl = tvl_data.get(ARBITRUM_CHAIN_ID, {})
    
    # 4. Get APY data
    apy_response = requests.get("https://api.beefy.finance/apy")
    apy_data = apy_response.json()
    
    # Process vaults
    candidates = []
    for vault in arb_vaults:
        vault_id = vault['id']
        tvl = arbitrum_tvl.get(vault_id, 0)
        
        # Skip low TVL
        if tvl < MIN_TVL:
            continue
            
        # Get fees
        vault_fees = fees_data.get(vault_id, {})
        performance_fees = vault_fees.get('performance', {})
        call_fee = performance_fees.get('call', 0)
        
        # If no explicit call fee, use Beefy standard
        if call_fee == 0:
            call_fee = 0.0005  # 0.05% standard
        
        # Get APY
        apy = apy_data.get(vault_id, 0)
        
        candidates.append({
            'id': vault_id,
            'name': vault.get('name', ''),
            'vault_address': vault.get('earnContractAddress'),
            'strategy': vault.get('strategy'),
            'tvl': tvl,
            'apy': apy,
            'call_fee': call_fee,
            'call_fee_bps': int(call_fee * 10000),
            'token': vault.get('token', ''),
            'token_decimals': vault.get('tokenDecimals', 18),
            'assets': vault.get('assets', [])
        })
    
    # Sort by TVL
    candidates.sort(key=lambda x: x['tvl'], reverse=True)
    
    print(f"\n✅ Found {len(candidates)} vaults with TVL > ${MIN_TVL:,}")
    
    # Show top candidates
    print("\n🎯 Top 10 Standard Vaults (non-CLM) with Strategies:")
    print("-" * 100)
    print(f"{'#':<3} {'Name':<30} {'TVL':<15} {'APY':<8} {'Fee':<8} {'Strategy'}")
    print("-" * 100)
    
    top_10 = candidates[:10]
    for i, vault in enumerate(top_10, 1):
        print(f"{i:<3} {vault['name'][:30]:<30} ${vault['tvl']:>13,.0f} {vault['apy']:>6.1f}% {vault['call_fee_bps']:>4} bps  {vault['strategy'][:30]}...")
    
    # Pick diverse top 3
    print("\n📋 Recommended 3 Starter Targets:")
    print("-" * 100)
    
    # Try to get different types
    selected = []
    
    # 1. Highest TVL vault
    if len(candidates) > 0:
        selected.append(candidates[0])
    
    # 2. A stablecoin vault if available
    stable_vaults = [v for v in candidates if any(asset in ['USDC', 'USDT', 'DAI'] for asset in v.get('assets', []))]
    if stable_vaults and stable_vaults[0] not in selected:
        selected.append(stable_vaults[0])
    elif len(candidates) > 1:
        selected.append(candidates[1])
    
    # 3. Another high TVL
    for v in candidates:
        if v not in selected and len(selected) < 3:
            selected.append(v)
            break
    
    for i, vault in enumerate(selected, 1):
        print(f"\n{i}. {vault['name']}")
        print(f"   Vault ID: {vault['id']}")
        print(f"   Vault: {vault['vault_address']}")
        print(f"   Strategy: {vault['strategy'][:50]}...")
        print(f"   TVL: ${vault['tvl']:,.0f}")
        print(f"   APY: {vault['apy']:.2f}%")
        print(f"   Call Fee: {vault['call_fee_bps']} bps ({vault['call_fee']:.3%})")
        print(f"   Verify Vault: https://arbiscan.io/address/{vault['vault_address']}#readProxyContract")
        print(f"   Verify Strategy: https://arbiscan.io/address/{vault['strategy'][:42]}#code")
    
    # Save selected vaults
    with open('selected_beefy_vaults.json', 'w') as f:
        json.dump(selected, f, indent=2)
    
    print(f"\n💾 Saved {len(selected)} selected vaults to selected_beefy_vaults.json")
    
    print("\n⚠️  Next Steps:")
    print("1. Open each vault on Arbiscan using 'Read as Proxy' tab")
    print("2. Call strategy() function to get the strategy address")
    print("3. Open strategy contract and find harvest() function")
    print("4. Check recent transactions for harvest frequency")
    
    # Return the vault IDs for easy reference
    print("\n🔑 Selected Vault IDs for targets.json:")
    for vault in selected:
        print(f"   - {vault['id']}")

if __name__ == "__main__":
    main()