#!/usr/bin/env python3
"""
Automated callability probe system for discovering harvestable functions
without manual inspection. Uses eth_call to probe common entrypoints and
analyzes transaction history to find callable functions.
"""

import json
import time
import requests
from web3 import Web3
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# Configuration
ARBITRUM_RPC = "https://arb-mainnet.g.alchemy.com/v2/5mlDO-31svMGY53J2Urqv"
BASE_RPC = "https://base-mainnet.g.alchemy.com/v2/3AvaLFHobnzEIToydrEiN"
BOT_ADDRESS = "0x00823727Ec5800ae6f5068fABAEb39608dE8bf45"

# Arbiscan/Basescan API keys (free tier is fine)
ARBISCAN_API_KEY = "YourArbiscanAPIKey"
BASESCAN_API_KEY = "YourBasescanAPIKey"

class CallableProber:
    """Probes contracts for callable harvest/compound functions"""
    
    def __init__(self, rpc_url: str, chain_name: str):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.chain = chain_name
        self.bot_addr = Web3.to_checksum_address(BOT_ADDRESS)
        
        # Common harvest-like function signatures
        self.PROBE_SIGNATURES = [
            # Standard harvest patterns
            ("harvest()", "0x4641257d", []),
            ("harvest(address)", "0x018ee9b7", [self.bot_addr]),
            ("harvest(address,uint256)", "0x3208fab2", [self.bot_addr, 0]),
            
            # Compound patterns  
            ("compound()", "0xa0712d68", []),
            ("compound(address)", "0xf69e2046", [self.bot_addr]),
            ("compound(uint256)", "0x9de5b6ae", [0]),
            
            # Rebalance/tend patterns
            ("rebalance()", "0x7d7c8c1e", []),
            ("tend()", "0x440368a4", []),
            ("run()", "0xc0406226", []),
            ("execute()", "0x61461954", []),
            
            # Report patterns (Yearn style)
            ("report()", "0xc3f909d4", []),
            ("report(uint256)", "0x99114df2", [0]),
            
            # Less common but worth checking
            ("doHarvest()", "0x3e2d86d1", []),
            ("work()", "0xe26b013b", []),
            ("earn()", "0xd389800f", []),
            ("processRewards()", "0x845a4697", []),
        ]
        
        # Role/permission error patterns
        self.PERMISSION_ERRORS = [
            "AccessControl",
            "Ownable",
            "onlyKeeper",
            "onlyManager", 
            "onlyAuthorized",
            "forbidden",
            "unauthorized",
            "!authorized",
            "caller is not"
        ]
    
    def probe_function(self, contract_addr: str, sig_name: str, 
                      selector: str, params: List) -> Dict[str, Any]:
        """Probe a single function using eth_call"""
        try:
            # Build call data
            call_data = selector
            
            # Encode parameters if any
            if params:
                # Simple encoding for common types
                for param in params:
                    if isinstance(param, str) and param.startswith("0x"):
                        # Address parameter
                        call_data += param[2:].lower().zfill(64)
                    elif isinstance(param, int):
                        # Uint256 parameter
                        call_data += hex(param)[2:].zfill(64)
            
            # Try eth_call with small gas limit
            result = self.w3.eth.call({
                'from': self.bot_addr,
                'to': contract_addr,
                'data': call_data,
                'gas': 100000  # Small gas limit for probe
            })
            
            return {
                'callable': True,
                'function': sig_name,
                'selector': selector,
                'params': params,
                'error': None,
                'permission_gated': False
            }
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check if it's a permission error
            permission_gated = any(err in error_str for err in 
                                  [e.lower() for e in self.PERMISSION_ERRORS])
            
            # Check if function doesn't exist (usually "execution reverted" with no reason)
            exists = "execution reverted" in error_str and len(error_str) > 50
            
            return {
                'callable': False,
                'function': sig_name,
                'selector': selector,
                'params': params,
                'error': str(e)[:200],
                'permission_gated': permission_gated,
                'exists': exists
            }
    
    def probe_all_functions(self, contract_addr: str) -> List[Dict]:
        """Probe all common harvest functions on a contract"""
        results = []
        
        for sig_name, selector, params in self.PROBE_SIGNATURES:
            result = self.probe_function(contract_addr, sig_name, selector, params)
            if result['callable'] or result.get('exists'):
                results.append(result)
        
        return results
    
    def analyze_tx_history(self, contract_addr: str, 
                           api_key: str = None) -> Dict[str, Any]:
        """Analyze transaction history to find commonly called functions"""
        # This would use Arbiscan/Basescan API to get recent transactions
        # For now, return placeholder
        return {
            'recent_functions': [],
            'unique_callers': 0,
            'publicness_score': 0
        }
    
    def calculate_publicness_score(self, contract_addr: str,
                                  tx_history: Dict) -> float:
        """Calculate publicness score based on unique EOA callers"""
        unique_callers = tx_history.get('unique_callers', 0)
        
        # Score based on number of unique callers
        if unique_callers >= 10:
            return 1.0  # Highly public
        elif unique_callers >= 5:
            return 0.7  # Moderately public
        elif unique_callers >= 2:
            return 0.4  # Low public access
        else:
            return 0.1  # Likely gated

class CLMDiscovery:
    """Discovers and validates CLM vaults for harvesting"""
    
    def __init__(self):
        self.arb_prober = CallableProber(ARBITRUM_RPC, "arbitrum")
        self.base_prober = CallableProber(BASE_RPC, "base")
    
    def get_clm_vaults(self, chain: str = "arbitrum") -> List[Dict]:
        """Fetch CLM vaults from Beefy API"""
        print(f"📋 Fetching CLM vaults for {chain}...")
        
        response = requests.get("https://api.beefy.finance/cow-vaults")
        all_vaults = response.json()
        
        # Filter for chain and active status
        chain_vaults = []
        for vault in all_vaults:
            if (vault.get('chain') == chain and 
                vault.get('status') == 'active' and
                vault.get('earnContractAddress')):
                chain_vaults.append({
                    'id': vault.get('id', ''),
                    'vault': vault['earnContractAddress'],
                    'type': vault.get('type', 'cowcentrated'),
                    'tvl': vault.get('tvl', 0),
                    'platform': vault.get('tokenProviderId', '')
                })
        
        # Sort by TVL
        chain_vaults.sort(key=lambda x: x['tvl'], reverse=True)
        return chain_vaults[:50]  # Top 50 by TVL
    
    def resolve_strategy(self, vault_addr: str, prober: CallableProber) -> Optional[str]:
        """Resolve strategy address from vault"""
        try:
            # Try to get strategy address
            strategy_selector = "0xa8c62e76"  # strategy()
            result = prober.w3.eth.call({
                'to': vault_addr,
                'data': strategy_selector
            })
            
            if result and len(result) == 32:
                strategy = "0x" + result.hex()[-40:]
                if strategy != "0x" + "0"*40:
                    return Web3.to_checksum_address(strategy)
        except:
            pass
        
        # Try manager() as fallback
        try:
            manager_selector = "0x481c6a75"  # manager()
            result = prober.w3.eth.call({
                'to': vault_addr,
                'data': manager_selector
            })
            
            if result and len(result) == 32:
                manager = "0x" + result.hex()[-40:]
                if manager != "0x" + "0"*40:
                    return Web3.to_checksum_address(manager)
        except:
            pass
        
        return None
    
    def probe_vault(self, vault: Dict, prober: CallableProber) -> Dict:
        """Probe a single vault for callable functions"""
        print(f"\n🔍 Probing {vault['id'][:30]}...")
        
        # Resolve strategy address
        strategy_addr = self.resolve_strategy(vault['vault'], prober)
        
        if not strategy_addr:
            print(f"  ❌ No strategy found")
            return None
        
        print(f"  Strategy: {strategy_addr}")
        
        # Probe all functions
        results = prober.probe_all_functions(strategy_addr)
        
        # Find callable functions
        callable_funcs = [r for r in results if r['callable']]
        gated_funcs = [r for r in results if r.get('permission_gated')]
        
        if callable_funcs:
            print(f"  ✅ Found {len(callable_funcs)} callable functions:")
            for func in callable_funcs:
                print(f"     - {func['function']}")
        elif gated_funcs:
            print(f"  🔒 Found {len(gated_funcs)} gated functions")
        else:
            print(f"  ❌ No callable functions found")
        
        # Analyze transaction history (would be implemented with block explorer API)
        tx_history = prober.analyze_tx_history(strategy_addr)
        publicness = prober.calculate_publicness_score(strategy_addr, tx_history)
        
        return {
            'vault': vault,
            'strategy': strategy_addr,
            'callable_functions': callable_funcs,
            'gated_functions': gated_funcs,
            'publicness_score': publicness,
            'tx_history': tx_history
        }
    
    def discover_harvestable(self, chain: str = "arbitrum", 
                            max_vaults: int = 20) -> List[Dict]:
        """Discover harvestable vaults on a chain"""
        print(f"\n{'='*60}")
        print(f"DISCOVERING HARVESTABLE VAULTS ON {chain.upper()}")
        print(f"{'='*60}")
        
        # Get prober for chain
        prober = self.arb_prober if chain == "arbitrum" else self.base_prober
        
        # Get CLM vaults
        vaults = self.get_clm_vaults(chain)[:max_vaults]
        print(f"\n📊 Testing top {len(vaults)} vaults by TVL")
        
        # Probe each vault
        harvestable = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self.probe_vault, v, prober): v 
                      for v in vaults}
            
            for future in as_completed(futures):
                result = future.result()
                if result and result['callable_functions']:
                    harvestable.append(result)
        
        # Sort by TVL and publicness
        harvestable.sort(key=lambda x: (
            x['publicness_score'], 
            x['vault']['tvl']
        ), reverse=True)
        
        return harvestable
    
    def create_target_entries(self, discoveries: List[Dict]) -> List[Dict]:
        """Create target entries for discovered harvestable vaults"""
        targets = []
        
        for disc in discoveries:
            vault = disc['vault']
            
            # Pick best callable function
            best_func = None
            for func in disc['callable_functions']:
                if 'harvest' in func['function'].lower():
                    best_func = func
                    break
            
            if not best_func and disc['callable_functions']:
                best_func = disc['callable_functions'][0]
            
            if best_func:
                # Extract function name without parameters
                func_name = best_func['function'].split('(')[0]
                
                target = {
                    "name": f"CLM_{vault['id'].replace('-', '_')[:25]}",
                    "address": disc['strategy'],
                    "abi": "abi/beefy_strategy.json",
                    "type": "harvest",
                    "enabled": True,
                    "params": best_func['params'],
                    "cooldownSec": 21600,  # 6 hours
                    "fixedRewardUSD": 0.30,
                    "skipProfitGate": False,
                    "read": {
                        "lastHarvest": "lastHarvest"
                    },
                    "write": {
                        "exec": func_name
                    },
                    "_metadata": {
                        "vault": vault['vault'],
                        "tvl": vault['tvl'],
                        "platform": vault['platform'],
                        "publicness": disc['publicness_score'],
                        "function": best_func['function'],
                        "chain": "arbitrum"
                    }
                }
                targets.append(target)
        
        return targets

def main():
    discovery = CLMDiscovery()
    
    # Discover on Arbitrum
    arb_harvestable = discovery.discover_harvestable("arbitrum", max_vaults=30)
    
    print(f"\n{'='*60}")
    print(f"ARBITRUM RESULTS: {len(arb_harvestable)} HARVESTABLE VAULTS")
    print(f"{'='*60}")
    
    if arb_harvestable:
        # Create target entries
        arb_targets = discovery.create_target_entries(arb_harvestable)
        
        print("\n📝 Top harvestable targets:")
        for i, target in enumerate(arb_targets[:5]):
            meta = target['_metadata']
            print(f"\n{i+1}. {target['name']}")
            print(f"   Strategy: {target['address']}")
            print(f"   Function: {meta['function']}")
            print(f"   TVL: ${meta['tvl']:,.0f}")
            print(f"   Publicness: {meta['publicness']:.1%}")
        
        # Save results
        output = {
            'discovered_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'chain': 'arbitrum',
            'harvestable_count': len(arb_harvestable),
            'targets': arb_targets
        }
        
        with open('clm_auto_discovered.json', 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Saved {len(arb_targets)} targets to clm_auto_discovered.json")
    
    # Discover on Base
    print(f"\n{'='*60}")
    print("DISCOVERING ON BASE NETWORK")
    print(f"{'='*60}")
    
    base_harvestable = discovery.discover_harvestable("base", max_vaults=20)
    
    if base_harvestable:
        base_targets = discovery.create_target_entries(base_harvestable)
        
        print(f"\n📝 Found {len(base_targets)} harvestable targets on Base")
        
        # Save Base results
        base_output = {
            'discovered_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'chain': 'base',
            'harvestable_count': len(base_harvestable),
            'targets': base_targets
        }
        
        with open('base_auto_discovered.json', 'w') as f:
            json.dump(base_output, f, indent=2)
        
        print(f"💾 Saved {len(base_targets)} Base targets to base_auto_discovered.json")
    
    print("\n🎯 Next steps:")
    print("  1. Review discovered targets in clm_auto_discovered.json")
    print("  2. Add high-confidence targets to janitor/targets.json")
    print("  3. Monitor harvest success rates")
    print("  4. Iterate on discovery parameters")

if __name__ == "__main__":
    main()