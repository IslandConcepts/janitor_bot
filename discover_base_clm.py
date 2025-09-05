#!/usr/bin/env python3
"""
Discover Base network CLM vaults using the same approach that worked for Arbitrum
"""

from web3 import Web3
import json
import requests

# Setup
BASE_RPC = "https://base-mainnet.g.alchemy.com/v2/3AvaLFHobnzEIToydrEiN"
w3 = Web3(Web3.HTTPProvider(BASE_RPC))
BOT_ADDRESS = "0x00823727Ec5800ae6f5068fABAEb39608dE8bf45"

def discover_base_clm():
    """Discover harvestable CLM vaults on Base"""
    print("="*60)
    print("DISCOVERING BASE NETWORK CLM VAULTS")
    print("="*60)
    
    # Check connection
    if not w3.is_connected():
        print("❌ Failed to connect to Base RPC")
        return
    
    print(f"✅ Connected to Base")
    print(f"   Latest block: {w3.eth.block_number:,}")
    
    # Get Base CLM vaults
    print("\n📋 Fetching Base CLM vaults...")
    response = requests.get("https://api.beefy.finance/cow-vaults")
    all_vaults = response.json()
    
    # Filter for Base CLM vaults
    base_clm = []
    for vault in all_vaults:
        if (vault.get('chain') == 'base' and 
            vault.get('status') == 'active' and
            vault.get('earnContractAddress')):
            
            vault_addr = vault['earnContractAddress']
            vault_id = vault.get('id', '')
            tvl = vault.get('tvl', 0)
            
            # Try to get strategy address
            try:
                # Call strategy()
                result = w3.eth.call({
                    'to': vault_addr,
                    'data': '0xa8c62e76'  # strategy()
                })
                
                if result and len(result) == 32:
                    strategy = "0x" + result.hex()[-40:]
                    if strategy != "0x" + "0"*40:
                        base_clm.append({
                            'vault_id': vault_id,
                            'vault': vault_addr,
                            'strategy': Web3.to_checksum_address(strategy),
                            'tvl': tvl,
                            'platform': vault.get('tokenProviderId', '')
                        })
            except:
                # Try manager() as fallback
                try:
                    result = w3.eth.call({
                        'to': vault_addr,
                        'data': '0x481c6a75'  # manager()
                    })
                    
                    if result and len(result) == 32:
                        manager = "0x" + result.hex()[-40:]
                        if manager != "0x" + "0"*40:
                            base_clm.append({
                                'vault_id': vault_id,
                                'vault': vault_addr,
                                'strategy': Web3.to_checksum_address(manager),
                                'tvl': tvl,
                                'platform': vault.get('tokenProviderId', ''),
                                'is_manager': True
                            })
                except:
                    pass
    
    # Sort by TVL
    base_clm.sort(key=lambda x: x['tvl'], reverse=True)
    
    print(f"Found {len(base_clm)} Base CLM vaults with strategies")
    
    if not base_clm:
        print("❌ No CLM vaults found on Base")
        return []
    
    # Show top vaults
    print("\n📊 Top Base CLM vaults by TVL:")
    for i, vault in enumerate(base_clm[:10]):
        print(f"\n{i+1}. {vault['vault_id']}")
        print(f"   Strategy: {vault['strategy']}")
        print(f"   TVL: ${vault['tvl']:,.0f}")
        print(f"   Platform: {vault['platform']}")
        if vault.get('is_manager'):
            print(f"   Note: This is a manager address")
    
    # Test harvest() callability
    print("\n🧪 Testing harvest() callability...")
    harvestable = []
    
    for vault in base_clm[:30]:  # Test top 30
        try:
            # Test harvest()
            result = w3.eth.call({
                'from': BOT_ADDRESS,
                'to': vault['strategy'],
                'data': '0x4641257d'  # harvest()
            })
            
            print(f"\n✅ {vault['vault_id'][:30]}")
            print(f"   Strategy: {vault['strategy']}")
            print(f"   TVL: ${vault['tvl']:,.0f}")
            print(f"   harvest() CALLABLE!")
            
            harvestable.append(vault)
            
        except Exception as e:
            error = str(e)
            if 'revert' in error.lower() and '0x26c87876' not in error:
                # Function exists but reverted (not just cooldown)
                print(f"\n🔒 {vault['vault_id'][:30]} - harvest() reverted")
    
    # Also test alternative functions
    if len(harvestable) < 5:
        print("\n🔧 Testing alternative functions...")
        
        alt_functions = [
            ('compound()', '0xa0712d68'),
            ('tend()', '0x440368a4'),
            ('work()', '0xe26b013b'),
        ]
        
        for func_name, selector in alt_functions:
            print(f"\nTesting {func_name}...")
            
            for vault in base_clm[:20]:
                if vault in harvestable:
                    continue
                    
                try:
                    result = w3.eth.call({
                        'from': BOT_ADDRESS,
                        'to': vault['strategy'],
                        'data': selector
                    })
                    
                    print(f"  ✅ {vault['vault_id'][:30]} - {func_name} CALLABLE")
                    vault['alt_function'] = func_name
                    harvestable.append(vault)
                except:
                    pass
    
    # Summary
    print("\n" + "="*60)
    print(f"BASE NETWORK RESULTS")
    print("="*60)
    
    print(f"\n📊 Statistics:")
    print(f"  Total CLM vaults: {len(base_clm)}")
    print(f"  Harvestable: {len(harvestable)}")
    
    if harvestable:
        print(f"\n✅ Found {len(harvestable)} harvestable Base CLM vaults!")
        
        # Create target configs
        targets = []
        for h in harvestable[:10]:  # Top 10
            func_name = h.get('alt_function', 'harvest()')
            
            target = {
                "name": f"BASE_CLM_{h['vault_id'].replace('-', '_')[:20]}",
                "address": h['strategy'],
                "abi": "abi/clm_strategy.json",
                "type": "harvest",
                "enabled": False,
                "params": [],
                "cooldownSec": 21600,
                "fixedRewardUSD": 0.30,
                "read": {
                    "lastHarvest": "lastHarvest"
                },
                "write": {
                    "exec": func_name.split('(')[0]
                },
                "_vault_id": h['vault_id'],
                "_tvl": h['tvl'],
                "_platform": h['platform']
            }
            targets.append(target)
            
            print(f"\n📍 {h['vault_id']}")
            print(f"   Strategy: {h['strategy']}")
            print(f"   TVL: ${h['tvl']:,.0f}")
            print(f"   Function: {func_name}")
        
        # Save results
        with open('base_clm_harvestable.json', 'w') as f:
            json.dump({
                'chain': 'base',
                'found': len(harvestable),
                'targets': targets
            }, f, indent=2)
        
        print(f"\n💾 Saved {len(targets)} Base targets to base_clm_harvestable.json")
        
        return targets
    else:
        print("\n⚠️ No harvestable Base CLM vaults found")
        print("  Possible reasons:")
        print("  - Base CLM vaults use different patterns")
        print("  - They may be permission-gated")
        print("  - Different contract architecture than Arbitrum")
        
        return []

if __name__ == "__main__":
    discover_base_clm()