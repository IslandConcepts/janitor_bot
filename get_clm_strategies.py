#!/usr/bin/env python3
"""
Get CLM vault strategy addresses for harvesting
"""

import requests
import json

def get_clm_strategies():
    """Get CLM vault strategies with their contract addresses"""
    
    print("🔍 Getting Beefy CLM vault strategies on Arbitrum...")
    
    # Get CLM vaults
    clm_response = requests.get("https://api.beefy.finance/cow-vaults")
    clm_vaults = clm_response.json()
    
    # Get regular vault data for strategy addresses
    vault_response = requests.get("https://api.beefy.finance/vaults")
    all_vaults = vault_response.json()
    
    # Create mapping of vault ID to strategy
    vault_strategies = {}
    for vault in all_vaults:
        if vault.get('strategy'):
            vault_strategies[vault['id']] = vault['strategy']
    
    # Find Arbitrum CLM vaults with strategies
    arbitrum_clm = []
    for clm in clm_vaults:
        if clm.get('chain') == 'arbitrum' and clm.get('status') == 'active':
            vault_id = clm.get('vaultId') or clm.get('oracleId')
            
            # Look for strategy
            strategy = vault_strategies.get(vault_id)
            if not strategy and 'contractAddress' in clm:
                strategy = clm['contractAddress']
            
            if strategy:
                arbitrum_clm.append({
                    'id': vault_id,
                    'type': clm.get('type'),
                    'strategy': strategy,
                    'tvl': clm.get('tvl', 0),
                    'apy': clm.get('apy', 0),
                    'platform': clm.get('platformId', ''),
                    'assets': clm.get('assets', [])
                })
    
    # Sort by TVL
    arbitrum_clm.sort(key=lambda x: x.get('tvl', 0), reverse=True)
    
    print(f"\n✅ Found {len(arbitrum_clm)} CLM vaults with strategies")
    
    # Show top 10
    print("\nTop 10 CLM vaults by TVL:")
    print("-" * 60)
    for i, vault in enumerate(arbitrum_clm[:10]):
        print(f"\n{i+1}. {vault['id']}")
        print(f"   Strategy: {vault.get('strategy', 'Unknown')}")
        print(f"   TVL: ${vault['tvl']:,.0f}")
        print(f"   Platform: {vault['platform']}")
    
    return arbitrum_clm

def create_clm_targets(vaults):
    """Create target configurations for CLM vaults"""
    
    targets = []
    
    # Select top 3 CLM vaults with highest TVL
    for vault in vaults[:3]:
        if vault.get('strategy') and vault['tvl'] > 10000:  # Min $10k TVL
            target = {
                "name": f"Beefy_CLM_{vault['id'].replace('-', '_')}",
                "address": vault['strategy'],
                "abi": "abi/beefy_strategy.json",
                "type": "harvest",
                "enabled": True,
                "params": ["0x00823727Ec5800ae6f5068fABAEb39608dE8bf45"],
                "cooldownSec": 21600,  # 6 hours for CLM
                "fixedRewardUSD": 0.30,
                "read": {
                    "lastHarvest": "lastHarvest"
                },
                "write": {
                    "exec": "harvest"
                },
                "_vault_id": vault['id'],
                "_tvl": vault['tvl'],
                "_platform": vault['platform']
            }
            targets.append(target)
    
    return targets

if __name__ == "__main__":
    print("=" * 60)
    print("BEEFY CLM STRATEGIES ON ARBITRUM")
    print("=" * 60)
    
    # Get CLM strategies
    clm_vaults = get_clm_strategies()
    
    if clm_vaults:
        # Create targets
        targets = create_clm_targets(clm_vaults)
        
        if targets:
            print("\n" + "=" * 60)
            print("RECOMMENDED CLM TARGETS FOR HARVESTING:")
            print("=" * 60)
            
            for i, target in enumerate(targets):
                print(f"\n{i+1}. {target['name']}")
                print(f"   Address: {target['address']}")
                print(f"   TVL: ${target['_tvl']:,.0f}")
                print(f"   Platform: {target['_platform']}")
        
        # Save results
        results = {
            "clm_vaults": clm_vaults[:20],
            "recommended_targets": targets
        }
        
        with open('clm_strategies.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        print("\n💾 Saved to clm_strategies.json")
    else:
        print("\n⚠️  No CLM vaults found with strategy addresses")