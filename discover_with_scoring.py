#!/usr/bin/env python3
"""
Enhanced discovery with integrated vault scoring
"""

import json
import time
from web3 import Web3
from typing import Dict, List, Optional, Tuple
from vault_scoring import VaultEvaluator, VaultScore

class ScoredDiscovery:
    """Discovery with integrated scoring"""
    
    def __init__(self, chain: str = "arbitrum"):
        self.chain = chain
        self.evaluator = VaultEvaluator(chain)
        
        # Setup RPC
        if chain == "arbitrum":
            self.rpc = "https://arb-mainnet.g.alchemy.com/v2/5mlDO-31svMGY53J2Urqv"
        elif chain == "base":
            self.rpc = "https://base-mainnet.g.alchemy.com/v2/3AvaLFHobnzEIToydrEiN"
        else:
            raise ValueError(f"Unsupported chain: {chain}")
        
        self.w3 = Web3(Web3.HTTPProvider(self.rpc))
        self.bot_address = "0x00823727Ec5800ae6f5068fABAEb39608dE8bf45"
    
    def discover_and_score(self, vault_addresses: List[str], vault_info: Dict) -> List[Tuple[VaultScore, Dict]]:
        """Discover and score vaults"""
        print(f"\n{'='*60}")
        print(f"DISCOVERING AND SCORING {self.chain.upper()} VAULTS")
        print(f"{'='*60}")
        
        scored_vaults = []
        
        for address in vault_addresses:
            info = vault_info.get(address, {})
            
            print(f"\n📋 Testing: {info.get('name', address[:10])}...")
            
            # Test callability
            call_score, harvest_func = self.evaluator.score_call_surface(address)
            
            # Skip if not callable
            if call_score.value[0] == 0:
                print(f"   ❌ Not callable: {harvest_func}")
                continue
            
            # Full evaluation
            score = self.evaluator.evaluate_vault(
                vault_name=info.get('name', f"Vault_{address[:8]}"),
                address=address,
                tvl_usd=info.get('tvl', 1_000_000),
                protocol=info.get('protocol', 'unknown'),
                harvest_frequency_hours=info.get('frequency_hours', 24),
                expected_reward_usd=info.get('expected_reward', 0.40)
            )
            
            print(f"   ✅ Score: {score.total_score}/24")
            print(f"   🎯 {score.recommendation}")
            
            # Only add if meets minimum score
            if score.total_score >= 16:  # Recommended or better
                config = score.to_config()
                scored_vaults.append((score, config))
                print(f"   💾 Added to targets")
            else:
                print(f"   ⚠️ Score too low, skipping")
        
        # Sort by score
        scored_vaults.sort(key=lambda x: x[0].total_score, reverse=True)
        
        return scored_vaults
    
    def generate_discovery_report(self, scored_vaults: List[Tuple[VaultScore, Dict]]):
        """Generate comprehensive discovery report"""
        print(f"\n{'='*60}")
        print(f"DISCOVERY REPORT - {self.chain.upper()}")
        print(f"{'='*60}")
        
        print(f"\n📊 Found {len(scored_vaults)} quality vaults")
        
        if not scored_vaults:
            print("   ❌ No vaults met the minimum score threshold")
            return
        
        # Group by score level
        highly_recommended = [v for v in scored_vaults if v[0].total_score >= 20]
        recommended = [v for v in scored_vaults if 16 <= v[0].total_score < 20]
        
        print(f"\n🏆 HIGHLY RECOMMENDED ({len(highly_recommended)} vaults):")
        for score, config in highly_recommended[:5]:  # Top 5
            print(f"   {score.vault_name}")
            print(f"   - Score: {score.total_score}/24")
            print(f"   - TVL: ${score.tvl_amount:,.0f}")
            print(f"   - Address: {score.address}")
        
        print(f"\n✅ RECOMMENDED ({len(recommended)} vaults):")
        for score, config in recommended[:5]:  # Top 5
            print(f"   {score.vault_name}")
            print(f"   - Score: {score.total_score}/24")
            print(f"   - TVL: ${score.tvl_amount:,.0f}")
        
        # Save targets
        targets = [config for _, config in scored_vaults]
        
        filename = f"{self.chain}_scored_targets.json"
        with open(filename, 'w') as f:
            json.dump({
                'chain': self.chain,
                'discovered': len(scored_vaults),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'targets': targets[:20]  # Top 20
            }, f, indent=2)
        
        print(f"\n💾 Saved top {min(20, len(targets))} targets to {filename}")
        
        # Show config snippets for top performers
        print(f"\n📝 TOP 3 CONFIGURATIONS:")
        for i, (score, config) in enumerate(scored_vaults[:3], 1):
            print(f"\n{i}. {score.vault_name} (Score: {score.total_score}/24)")
            print(json.dumps(config, indent=2))
    
    def quick_discover_beefy(self, limit: int = 50) -> List[Tuple[VaultScore, Dict]]:
        """Quick discovery of Beefy vaults"""
        import requests
        
        print(f"\n🔍 Quick discovering Beefy vaults on {self.chain}...")
        
        # Get vaults from API
        response = requests.get("https://api.beefy.finance/vaults")
        all_vaults = response.json()
        
        # Filter for chain
        chain_vaults = [v for v in all_vaults 
                       if v.get('chain') == self.chain 
                       and v.get('status') == 'active'
                       and v.get('strategy')]
        
        # Sort by TVL
        chain_vaults.sort(key=lambda x: x.get('tvl', 0), reverse=True)
        
        # Prepare vault info
        vault_info = {}
        addresses = []
        
        for vault in chain_vaults[:limit]:
            strategy = vault['strategy']
            addresses.append(strategy)
            vault_info[strategy] = {
                'name': vault.get('id', ''),
                'tvl': vault.get('tvl', 0),
                'protocol': 'beefy',
                'frequency_hours': 12,  # Conservative estimate
                'expected_reward': 0.40
            }
        
        # Discover and score
        scored = self.discover_and_score(addresses, vault_info)
        
        return scored

def main():
    """Run discovery with scoring"""
    import sys
    
    chain = sys.argv[1] if len(sys.argv) > 1 else "arbitrum"
    
    discoverer = ScoredDiscovery(chain)
    
    # Quick discover Beefy vaults
    scored_vaults = discoverer.quick_discover_beefy(limit=30)
    
    # Generate report
    discoverer.generate_discovery_report(scored_vaults)
    
    print(f"\n✨ Discovery with scoring complete!")

if __name__ == "__main__":
    main()