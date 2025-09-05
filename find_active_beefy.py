#!/usr/bin/env python3
"""
Find truly active Beefy vaults with TVL and fees
"""

import json
import requests

def main():
    print("🔍 Finding Active Beefy Vaults on Arbitrum...")
    
    # Get vaults
    vaults = requests.get("https://api.beefy.finance/vaults").json()
    
    # Get TVL data
    tvl_data = requests.get("https://api.beefy.finance/tvl").json()
    
    # Get APY data
    apy_data = requests.get("https://api.beefy.finance/apy").json()
    
    # Get fees
    fees_data = requests.get("https://api.beefy.finance/fees").json()
    
    # Filter for Arbitrum active vaults
    arbitrum_vaults = []
    
    for vault in vaults:
        if vault.get('chain') == 'arbitrum' and vault.get('status') == 'active':
            vault_id = vault['id']
            
            # Get TVL
            tvl = tvl_data.get(vault_id, 0)
            
            # Skip if no TVL
            if tvl < 10000:  # Less than $10k
                continue
            
            # Get fees
            vault_fees = fees_data.get(vault_id, {})
            perf_fees = vault_fees.get('performance', {})
            call_fee = perf_fees.get('call', 0)
            
            # Get APY
            apy = apy_data.get(vault_id, 0)
            
            arbitrum_vaults.append({
                'id': vault_id,
                'name': vault.get('name', ''),
                'address': vault.get('earnContractAddress'),
                'tvl': tvl,
                'apy': apy,
                'call_fee': call_fee,
                'call_fee_bps': int(call_fee * 10000),
                'strategy': vault.get('strategy'),
                'assets': vault.get('assets', [])
            })
    
    # Sort by TVL
    arbitrum_vaults.sort(key=lambda x: x['tvl'], reverse=True)
    
    print(f"\n✅ Found {len(arbitrum_vaults)} vaults with TVL > $10k")
    
    # Show top vaults with call fees
    vaults_with_fees = [v for v in arbitrum_vaults if v['call_fee'] > 0]
    
    print(f"\n💰 Vaults with harvest call fees: {len(vaults_with_fees)}")
    print("\n🎯 Top Harvestable Vaults:")
    print("-" * 90)
    
    for i, vault in enumerate(vaults_with_fees[:10], 1):
        print(f"\n{i}. {vault['name']}")
        print(f"   Address: {vault['address']}")
        print(f"   TVL: ${vault['tvl']:,.0f}")
        print(f"   APY: {vault['apy']:.2f}%")
        print(f"   Call Fee: {vault['call_fee_bps']/100:.2f}% ({vault['call_fee_bps']} bps)")
        print(f"   Verify: https://arbiscan.io/address/{vault['address']}")
    
    # Also show top TVL vaults regardless of fees
    print("\n📊 Top TVL Vaults (all):")
    print("-" * 90)
    
    for i, vault in enumerate(arbitrum_vaults[:5], 1):
        print(f"\n{i}. {vault['name']} - TVL: ${vault['tvl']:,.0f}")
        print(f"   Address: {vault['address']}")
        print(f"   Call Fee: {vault['call_fee_bps']/100:.2f}%")
    
    # Save results
    with open('active_beefy_vaults.json', 'w') as f:
        json.dump(vaults_with_fees[:10], f, indent=2)
    
    print(f"\n💾 Saved top vaults to active_beefy_vaults.json")

if __name__ == "__main__":
    main()