#!/usr/bin/env python3
"""
Direct analysis of CLM transactions using eth_getTransactionByHash
Focus on the known working CLM to understand the pattern
"""

from web3 import Web3
import json
import requests
from collections import defaultdict

# Setup
RPC = "https://arb-mainnet.g.alchemy.com/v2/5mlDO-31svMGY53J2Urqv"
w3 = Web3(Web3.HTTPProvider(RPC))

# Known working CLM that we already added
WORKING_CLM = "0x33a8B05CAf2853D724c18432762A6B7EbC1DCBec"

def get_arbiscan_transactions(address: str):
    """Get transactions from Arbiscan API (free tier)"""
    print(f"\n🔍 Fetching transactions from Arbiscan for {address[:10]}...")
    
    # Using Arbiscan API (you can get a free API key)
    # For now using without API key (limited to 1 req/5 sec)
    url = f"https://api.arbiscan.io/api"
    params = {
        'module': 'account',
        'action': 'txlist',
        'address': address,
        'startblock': 0,
        'endblock': 99999999,
        'page': 1,
        'offset': 100,
        'sort': 'desc'
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['status'] == '1' and data['result']:
            return data['result']
    except Exception as e:
        print(f"  Error: {e}")
    
    return []

def analyze_clm_patterns():
    """Analyze the known working CLM to understand patterns"""
    print("="*60)
    print("ANALYZING KNOWN WORKING CLM")
    print("="*60)
    
    print(f"\nTarget: {WORKING_CLM}")
    print("This CLM is successfully using harvest() with no params")
    
    # Get other top CLM strategies
    print("\n📋 Getting other CLM strategies...")
    
    response = requests.get("https://api.beefy.finance/cow-vaults")
    vaults = response.json()
    
    # Get strategies
    strategies = []
    for vault in vaults:
        if (vault.get('chain') == 'arbitrum' and 
            vault.get('status') == 'active' and
            vault.get('earnContractAddress')):
            
            vault_addr = vault['earnContractAddress']
            try:
                # Try strategy()
                result = w3.eth.call({
                    'to': vault_addr,
                    'data': '0xa8c62e76'
                })
                if result and len(result) == 32:
                    strategy = "0x" + result.hex()[-40:]
                    if strategy != "0x" + "0"*40:
                        strategies.append({
                            'vault_id': vault.get('id', ''),
                            'strategy': Web3.to_checksum_address(strategy),
                            'tvl': vault.get('tvl', 0)
                        })
            except:
                pass
    
    # Sort by TVL
    strategies.sort(key=lambda x: x['tvl'], reverse=True)
    
    print(f"Found {len(strategies)} CLM strategies")
    
    # Test each for harvest callability
    print("\n🧪 Testing harvest() callability on top strategies...")
    
    harvestable = []
    
    for i, strat in enumerate(strategies[:30]):
        # Test harvest()
        try:
            result = w3.eth.call({
                'from': "0x00823727Ec5800ae6f5068fABAEb39608dE8bf45",
                'to': strat['strategy'],
                'data': '0x4641257d'  # harvest()
            })
            
            print(f"\n✅ {strat['vault_id'][:30]}")
            print(f"   Strategy: {strat['strategy']}")
            print(f"   TVL: ${strat['tvl']:,.0f}")
            print(f"   harvest() CALLABLE!")
            
            harvestable.append(strat)
            
        except Exception as e:
            error = str(e)
            if 'revert' not in error.lower():
                # Function doesn't exist
                continue
            else:
                # Function exists but reverted - might need params or permissions
                print(f"\n🔒 {strat['vault_id'][:30]}")
                print(f"   Strategy: {strat['strategy']}")
                print(f"   harvest() exists but reverted: {error[:50]}")
    
    # Check alternative functions
    print("\n🔧 Testing alternative harvest functions...")
    
    alt_functions = [
        ('compound()', '0xa0712d68'),
        ('doHarvest()', '0x3e2d86d1'),
        ('tend()', '0x440368a4'),
        ('work()', '0xe26b013b'),
        ('run()', '0xc0406226'),
    ]
    
    for func_name, selector in alt_functions:
        print(f"\nTesting {func_name}...")
        callable_count = 0
        
        for strat in strategies[:20]:
            try:
                result = w3.eth.call({
                    'from': "0x00823727Ec5800ae6f5068fABAEb39608dE8bf45",
                    'to': strat['strategy'],
                    'data': selector
                })
                callable_count += 1
                print(f"  ✅ {strat['vault_id'][:20]} - CALLABLE")
                
                # Add to harvestable if not already there
                if strat not in harvestable:
                    strat['alt_function'] = func_name
                    harvestable.append(strat)
                    
            except:
                pass
        
        if callable_count > 0:
            print(f"  Found {callable_count} strategies with callable {func_name}")
    
    # Summary
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    if harvestable:
        print(f"\n✅ Found {len(harvestable)} harvestable CLM strategies!")
        
        # Create target configs
        targets = []
        for h in harvestable[:10]:  # Top 10
            func_name = h.get('alt_function', 'harvest()')
            
            target = {
                "name": f"CLM_{h['vault_id'].replace('-', '_')[:25]}",
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
                "_tvl": h['tvl']
            }
            targets.append(target)
            
            print(f"\n📍 {h['vault_id']}")
            print(f"   Strategy: {h['strategy']}")
            print(f"   TVL: ${h['tvl']:,.0f}")
            print(f"   Function: {func_name}")
        
        # Save results
        with open('clm_harvestable.json', 'w') as f:
            json.dump({
                'found': len(harvestable),
                'targets': targets
            }, f, indent=2)
        
        print(f"\n💾 Saved {len(targets)} targets to clm_harvestable.json")
        
        # Update the existing CLM ABI if needed
        if any('alt_function' in h for h in harvestable):
            print("\n⚠️ Some strategies use alternative functions")
            print("   You may need to add these to clm_strategy.json ABI")
    else:
        print("\n❌ No additional harvestable CLM strategies found")
        print("   The one we already have might be unique")

if __name__ == "__main__":
    analyze_clm_patterns()