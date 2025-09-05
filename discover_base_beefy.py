#!/usr/bin/env python3
"""
Discover standard Beefy vaults on Base network (non-CLM)
"""

from web3 import Web3
import json
import requests

# Setup
BASE_RPC = "https://base-mainnet.g.alchemy.com/v2/3AvaLFHobnzEIToydrEiN"
w3 = Web3(Web3.HTTPProvider(BASE_RPC))
BOT_ADDRESS = "0x00823727Ec5800ae6f5068fABAEb39608dE8bf45"

def discover_base_beefy():
    """Discover standard Beefy vaults on Base"""
    print("="*60)
    print("DISCOVERING BASE NETWORK STANDARD BEEFY VAULTS")
    print("="*60)
    
    # Check connection
    if not w3.is_connected():
        print("❌ Failed to connect to Base RPC")
        return
    
    print(f"✅ Connected to Base")
    print(f"   Latest block: {w3.eth.block_number:,}")
    
    # Get Base vaults from Beefy API
    print("\n📋 Fetching Base Beefy vaults...")
    response = requests.get("https://api.beefy.finance/vaults")
    all_vaults = response.json()
    
    # Filter for Base standard vaults (not CLM)
    base_vaults = []
    for vault in all_vaults:
        if (vault.get('chain') == 'base' and 
            vault.get('status') == 'active' and
            vault.get('strategy') and
            'cow' not in vault.get('id', '').lower()):  # Exclude CLM vaults
            
            base_vaults.append({
                'id': vault.get('id', ''),
                'strategy': vault['strategy'],
                'tvl': vault.get('tvl', 0),
                'apy': vault.get('apy', 0),
                'platform': vault.get('platformId', ''),
                'earnContractAddress': vault.get('earnContractAddress', '')
            })
    
    # Sort by TVL
    base_vaults.sort(key=lambda x: x['tvl'], reverse=True)
    
    print(f"Found {len(base_vaults)} standard Beefy vaults on Base")
    
    if not base_vaults:
        print("❌ No standard Beefy vaults found on Base")
        return []
    
    # Show top vaults
    print("\n📊 Top Base Beefy vaults by TVL:")
    for i, vault in enumerate(base_vaults[:10]):
        print(f"\n{i+1}. {vault['id']}")
        print(f"   Strategy: {vault['strategy']}")
        print(f"   TVL: ${vault['tvl']:,.0f}")
        print(f"   Platform: {vault['platform']}")
        print(f"   APY: {vault['apy']:.2f}%")
    
    # Test harvest(address) callability - standard Beefy pattern
    print("\n🧪 Testing harvest(address) callability...")
    harvestable = []
    
    for vault in base_vaults[:30]:  # Test top 30
        strategy_addr = vault['strategy']
        
        # Test harvest(address) - standard Beefy pattern
        try:
            # Encode harvest(address) call
            # Function selector for harvest(address): 0x018ee9b7
            call_data = '0x018ee9b7' + BOT_ADDRESS[2:].lower().zfill(64)
            
            result = w3.eth.call({
                'from': BOT_ADDRESS,
                'to': strategy_addr,
                'data': call_data
            })
            
            print(f"\n✅ {vault['id'][:40]}")
            print(f"   Strategy: {strategy_addr}")
            print(f"   TVL: ${vault['tvl']:,.0f}")
            print(f"   harvest(address) CALLABLE!")
            
            harvestable.append(vault)
            
        except Exception as e:
            error = str(e)
            # Check if it's just a cooldown error (common)
            if '0x26c87876' in error:
                print(f"\n⏰ {vault['id'][:40]} - On cooldown but likely harvestable")
                harvestable.append(vault)
            elif 'revert' in error.lower():
                # Function exists but reverted for other reason
                pass
    
    # Also test harvest() without params
    if len(harvestable) < 5:
        print("\n🔧 Testing harvest() without params...")
        
        for vault in base_vaults[:20]:
            if vault in harvestable:
                continue
                
            try:
                result = w3.eth.call({
                    'from': BOT_ADDRESS,
                    'to': vault['strategy'],
                    'data': '0x4641257d'  # harvest()
                })
                
                print(f"  ✅ {vault['id'][:40]} - harvest() CALLABLE")
                vault['no_params'] = True
                harvestable.append(vault)
            except:
                pass
    
    # Summary
    print("\n" + "="*60)
    print(f"BASE NETWORK BEEFY RESULTS")
    print("="*60)
    
    print(f"\n📊 Statistics:")
    print(f"  Total standard vaults: {len(base_vaults)}")
    print(f"  Harvestable: {len(harvestable)}")
    
    if harvestable:
        print(f"\n✅ Found {len(harvestable)} harvestable Base Beefy vaults!")
        
        # Create target configs
        targets = []
        for h in harvestable[:10]:  # Top 10
            
            # Determine harvest pattern
            if h.get('no_params'):
                exec_func = "harvest"
                params = []
            else:
                exec_func = "harvest"
                params = [BOT_ADDRESS]
            
            target = {
                "name": f"BASE_Beefy_{h['id'].replace('-', '_')[:25]}",
                "address": h['strategy'],
                "abi": "abi/beefy_strategy.json",
                "type": "harvest",
                "enabled": False,  # Start disabled for testing
                "params": params,
                "cooldownSec": 43200,  # 12 hours for standard vaults
                "fixedRewardUSD": 0.50,
                "read": {
                    "lastHarvest": "lastHarvest"
                },
                "write": {
                    "exec": exec_func
                },
                "_vault_id": h['id'],
                "_tvl": h['tvl'],
                "_platform": h['platform'],
                "_apy": h['apy']
            }
            targets.append(target)
            
            print(f"\n📍 {h['id']}")
            print(f"   Strategy: {h['strategy']}")
            print(f"   TVL: ${h['tvl']:,.0f}")
            print(f"   APY: {h['apy']:.2f}%")
            print(f"   Params: {params}")
        
        # Save results
        with open('base_beefy_harvestable.json', 'w') as f:
            json.dump({
                'chain': 'base',
                'found': len(harvestable),
                'targets': targets
            }, f, indent=2)
        
        print(f"\n💾 Saved {len(targets)} Base Beefy targets to base_beefy_harvestable.json")
        
        return targets
    else:
        print("\n⚠️ No harvestable Base Beefy vaults found")
        print("  This is unusual - Base should have standard Beefy vaults")
        print("  They may be using different harvest patterns")
        
        return []

if __name__ == "__main__":
    discover_base_beefy()