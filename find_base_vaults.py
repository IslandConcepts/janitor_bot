#!/usr/bin/env python3
"""
Find harvestable vaults on Base network
"""

import requests
import json

def find_beefy_base_vaults():
    """Find Beefy vaults on Base"""
    print("🔍 Searching for Beefy vaults on Base network...")
    
    # Beefy API for Base
    response = requests.get("https://api.beefy.finance/vaults/base")
    vaults = response.json()
    
    # Filter for active vaults with good TVL
    active_vaults = []
    for vault in vaults:
        if (vault.get('status') == 'active' and 
            vault.get('tvl', 0) > 100000 and  # $100k+ TVL
            'strategy' in vault):
            active_vaults.append({
                'name': vault['id'],
                'earnedToken': vault.get('earnedToken'),
                'tvl': vault.get('tvl', 0),
                'apy': vault.get('apy', 0),
                'strategy': vault['strategy']
            })
    
    # Sort by TVL
    active_vaults.sort(key=lambda x: x['tvl'], reverse=True)
    
    print(f"\n✅ Found {len(active_vaults)} active Beefy vaults on Base")
    print("\nTop 10 by TVL:")
    for i, vault in enumerate(active_vaults[:10]):
        print(f"{i+1}. {vault['name']}")
        print(f"   TVL: ${vault['tvl']:,.0f}")
        print(f"   APY: {vault['apy']:.1f}%")
        print(f"   Strategy: {vault['strategy'][:42]}...")
    
    return active_vaults

def find_aerodrome_pools():
    """Find Aerodrome (Base's main DEX) pools"""
    print("\n🔍 Checking Aerodrome Finance on Base...")
    
    # Known Aerodrome contracts
    aerodrome_contracts = [
        {
            'name': 'Aerodrome_Voter',
            'address': '0x16613524e02ad97eDfeF371bC883F2F5d6C480A5',
            'description': 'Aerodrome voter - distributes emissions'
        },
        {
            'name': 'Aerodrome_RewardsDistributor',
            'address': '0x227f65131A261548b057215bB1D5Ab2997964C7d',
            'description': 'Distributes AERO rewards'
        }
    ]
    
    print(f"Found {len(aerodrome_contracts)} Aerodrome contracts")
    for contract in aerodrome_contracts:
        print(f"  • {contract['name']}: {contract['address']}")
    
    return aerodrome_contracts

def check_base_protocols():
    """Check other Base protocols"""
    print("\n📊 Other Base protocols to explore:")
    
    protocols = [
        "Synthetix (SNX staking)",
        "Extra Finance (leveraged yield)",
        "Stargate (bridge liquidity)",
        "BaseSwap (DEX)",
        "Moonwell (lending)",
        "Compound v3 (lending)",
    ]
    
    for protocol in protocols:
        print(f"  • {protocol}")
    
    return protocols

if __name__ == "__main__":
    print("=" * 60)
    print("BASE NETWORK HARVESTING OPPORTUNITIES")
    print("=" * 60)
    
    # Find Beefy vaults
    beefy_vaults = find_beefy_base_vaults()
    
    # Find Aerodrome
    aerodrome = find_aerodrome_pools()
    
    # List other protocols
    other = check_base_protocols()
    
    # Save results
    results = {
        'beefy_vaults': beefy_vaults[:20],  # Top 20
        'aerodrome': aerodrome,
        'other_protocols': other
    }
    
    with open('base_opportunities.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n💾 Results saved to base_opportunities.json")
    print("\n🎯 Next steps:")
    print("1. Get Base RPC endpoint (Alchemy, Infura, etc)")
    print("2. Add Base configuration to targets.json")
    print("3. Select specific vaults to harvest")