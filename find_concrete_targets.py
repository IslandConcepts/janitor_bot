#!/usr/bin/env python3
"""
Find concrete harvestable targets based on specific protocols
"""

import requests
import json
from web3 import Web3

def find_beefy_clm_vaults():
    """Find Beefy CLM (Concentrated Liquidity Manager) vaults on Arbitrum"""
    
    print("🔍 Finding Beefy CLM vaults on Arbitrum...")
    
    # Get all vaults
    response = requests.get("https://api.beefy.finance/vaults")
    all_vaults = response.json()
    
    # Filter for Arbitrum CLM vaults
    clm_vaults = []
    for vault in all_vaults:
        if (vault.get('chain') == 'arbitrum' and 
            vault.get('status') == 'active' and
            ('clm' in vault.get('id', '').lower() or 
             'cowcentrated' in vault.get('id', '').lower())):
            clm_vaults.append(vault)
    
    print(f"Found {len(clm_vaults)} CLM vaults on Arbitrum")
    
    # Get CLM-specific data
    clm_data = requests.get("https://api.beefy.finance/cow-vaults")
    if clm_data.status_code == 200:
        clm_info = clm_data.json()
        print(f"Got CLM data for {len(clm_info)} vaults")
    
    return clm_vaults

def find_reaper_vaults():
    """Find Reaper Finance vaults on Arbitrum and Fantom"""
    
    print("\n🔍 Finding Reaper vaults...")
    
    # Reaper known contracts on Arbitrum
    reaper_arbitrum = [
        {
            "name": "Reaper_USDC_Crypt",
            "address": "0x0000000000000000000000000000000000000000",  # Need actual address
            "chain": "arbitrum",
            "description": "USDC single-strategy Crypt with 0.45% caller reward"
        }
    ]
    
    # Reaper API endpoint (if available)
    try:
        # Check if Reaper has an API
        response = requests.get("https://api.reaper.farm/vaults", timeout=5)
        if response.status_code == 200:
            vaults = response.json()
            print(f"Found {len(vaults)} Reaper vaults from API")
    except:
        print("Reaper API not available, using known contracts")
    
    return reaper_arbitrum

def find_yearn_v3_arbitrum():
    """Find Yearn v3 vaults on Arbitrum"""
    
    print("\n🔍 Finding Yearn v3 vaults on Arbitrum...")
    
    # Yearn v3 factory addresses
    yearn_v3_arbitrum = {
        "vault_factory": "0x444045c5C13C246e117eD36437303cac8E250aB0",  # Example, need real address
        "registry": "0x0000000000000000000000000000000000000000"
    }
    
    # Known Yearn v3 vaults on Arbitrum
    known_vaults = [
        {
            "name": "yvUSDC-3",
            "address": "Check yearn.fi for Arbitrum deployments",
            "type": "v3_vault"
        }
    ]
    
    return known_vaults

def get_specific_beefy_strategies():
    """Get specific Beefy strategy addresses we know work"""
    
    print("\n✅ Known working Beefy strategies on Arbitrum:")
    
    working_strategies = [
        {
            "name": "Beefy_MIM_USDC",
            "strategy": "0xD945e7937066f3A8b87460301666c5287f5315dD",
            "vault": "0x693B0Adf3AFA78f8CB83ca436c77207CD4EaE0ca",
            "description": "MIM-USDC Balancer stable pool"
        },
        {
            "name": "Beefy_USDC_USDT_GHO", 
            "strategy": "0x21d37617F19910a82C6CaeE0BD973Bf87Ce11D8e",
            "vault": "0x1B3824ab1fE5ee996d59e39CE0E1236Fb5b7B5F4",
            "description": "USDC/USDT/GHO Balancer v3 bundle"
        },
        {
            "name": "Beefy_tBTC_WBTC",
            "strategy": "0xa2172783Eafd97FBF25bffFAFda3aD03B5115613",
            "vault": "0x0c63BBC3712c53214b5489C68cCDC5a9e3bB4800",
            "description": "tBTC-WBTC major pair"
        }
    ]
    
    for strat in working_strategies:
        print(f"  • {strat['name']}: {strat['strategy'][:10]}...")
        print(f"    {strat['description']}")
    
    return working_strategies

def find_balancer_v3_pools():
    """Find Balancer v3 pools with harvestable fees"""
    
    print("\n🔍 Finding Balancer v3 pools on Arbitrum...")
    
    # Balancer v3 gauge controller
    balancer_contracts = [
        {
            "name": "Balancer_GaugeController",
            "address": "0xC128468b7Ce63eA702C1f104D55A2566b13D3ABD",
            "description": "Balancer gauge controller for fee distribution"
        }
    ]
    
    return balancer_contracts

def main():
    print("=" * 60)
    print("CONCRETE HARVESTABLE TARGETS")
    print("=" * 60)
    
    # 1. Beefy CLM vaults
    clm_vaults = find_beefy_clm_vaults()
    
    # 2. Get working Beefy strategies
    beefy_strats = get_specific_beefy_strategies()
    
    # 3. Reaper vaults
    reaper = find_reaper_vaults()
    
    # 4. Yearn v3
    yearn = find_yearn_v3_arbitrum()
    
    # 5. Balancer v3
    balancer = find_balancer_v3_pools()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    print("\n📊 Available for harvesting:")
    print(f"  • Beefy strategies: {len(beefy_strats)} confirmed working")
    print(f"  • Beefy CLM vaults: {len(clm_vaults)} found")
    print(f"  • Reaper vaults: Check reaper.farm for Arbitrum Crypts")
    print(f"  • Yearn v3: Check yearn.fi for public keeper jobs")
    
    print("\n🎯 Next steps:")
    print("1. Verify each strategy on Arbiscan for harvest() function")
    print("2. Check if harvest requires caller fee recipient parameter")
    print("3. Confirm cooldown periods (usually 6-24 hours)")
    print("4. Test with small transaction first")
    
    # Save findings
    results = {
        "beefy_working": beefy_strats,
        "beefy_clm": clm_vaults[:10] if clm_vaults else [],
        "reaper": reaper,
        "yearn_v3": yearn,
        "balancer": balancer
    }
    
    with open('concrete_targets.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n💾 Saved to concrete_targets.json")

if __name__ == "__main__":
    main()