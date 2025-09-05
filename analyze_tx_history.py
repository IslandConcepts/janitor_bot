#!/usr/bin/env python3
"""
Analyze transaction history of CLM strategies to find actually called functions
and determine publicness based on unique EOA callers.
"""

import json
import time
import requests
from web3 import Web3
from typing import List, Dict, Set, Optional
from collections import defaultdict

# Configuration
ARBITRUM_RPC = "https://arb-mainnet.g.alchemy.com/v2/5mlDO-31svMGY53J2Urqv"
BASE_RPC = "https://base-mainnet.g.alchemy.com/v2/3AvaLFHobnzEIToydrEiN"

# Arbiscan/Basescan API endpoints
ARBISCAN_API = "https://api.arbiscan.io/api"
BASESCAN_API = "https://api.basescan.org/api"

class TxHistoryAnalyzer:
    """Analyzes transaction history to find callable functions"""
    
    def __init__(self, chain: str = "arbitrum"):
        self.chain = chain
        if chain == "arbitrum":
            self.w3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC))
            self.api_url = ARBISCAN_API
        else:
            self.w3 = Web3(Web3.HTTPProvider(BASE_RPC))
            self.api_url = BASESCAN_API
    
    def get_recent_transactions(self, address: str, limit: int = 100) -> List[Dict]:
        """Get recent transactions to a contract"""
        # Using direct RPC call to get recent transactions
        print(f"  Fetching recent transactions for {address[:10]}...")
        
        current_block = self.w3.eth.block_number
        start_block = max(0, current_block - 10000)  # Look back ~10k blocks
        
        transactions = []
        
        # Get a sample of recent blocks and check for transactions
        for block_num in range(current_block, start_block, -100):
            try:
                block = self.w3.eth.get_block(block_num, True)
                for tx in block.transactions:
                    if tx.get('to') and tx['to'].lower() == address.lower():
                        transactions.append({
                            'hash': tx['hash'].hex(),
                            'from': tx['from'],
                            'input': tx['input'],
                            'blockNumber': block_num
                        })
                        if len(transactions) >= limit:
                            return transactions
            except:
                continue
        
        return transactions
    
    def extract_function_selectors(self, transactions: List[Dict]) -> Dict[str, int]:
        """Extract function selectors and count their usage"""
        selector_counts = defaultdict(int)
        
        for tx in transactions:
            input_data = tx.get('input', '')
            if len(input_data) >= 10:  # Has function selector
                selector = input_data[:10]
                selector_counts[selector] += 1
        
        return dict(selector_counts)
    
    def identify_unique_callers(self, transactions: List[Dict]) -> Set[str]:
        """Identify unique EOA callers"""
        callers = set()
        
        for tx in transactions:
            from_addr = tx.get('from', '')
            if from_addr:
                # Check if it's an EOA (not a contract)
                code = self.w3.eth.get_code(from_addr)
                if len(code) == 0:  # EOA has no code
                    callers.add(from_addr.lower())
        
        return callers
    
    def calculate_publicness_score(self, unique_eoa_count: int) -> float:
        """Calculate publicness score based on unique EOA callers"""
        if unique_eoa_count >= 10:
            return 1.0  # Highly public
        elif unique_eoa_count >= 5:
            return 0.7  # Moderately public  
        elif unique_eoa_count >= 2:
            return 0.4  # Some public access
        else:
            return 0.1  # Likely gated/private
    
    def analyze_strategy(self, strategy_addr: str) -> Dict:
        """Analyze a strategy's transaction history"""
        print(f"\n📊 Analyzing {strategy_addr}")
        
        # Get recent transactions
        txs = self.get_recent_transactions(strategy_addr, limit=50)
        
        if not txs:
            print(f"  No recent transactions found")
            return {
                'address': strategy_addr,
                'tx_count': 0,
                'selectors': {},
                'unique_eoas': 0,
                'publicness': 0,
                'likely_harvestable': False
            }
        
        # Extract function selectors
        selectors = self.extract_function_selectors(txs)
        
        # Identify unique callers
        unique_callers = self.identify_unique_callers(txs)
        
        # Calculate publicness
        publicness = self.calculate_publicness_score(len(unique_callers))
        
        # Check for harvest-like selectors
        harvest_selectors = {
            '0x4641257d': 'harvest()',
            '0x018ee9b7': 'harvest(address)',
            '0xa0712d68': 'compound()',
            '0x440368a4': 'tend()',
            '0x7d7c8c1e': 'rebalance()',
            '0xc3f909d4': 'report()',
            '0xe26b013b': 'work()',
            '0xd389800f': 'earn()'
        }
        
        found_harvest = False
        for selector in selectors:
            if selector in harvest_selectors:
                print(f"  ✅ Found {harvest_selectors[selector]} called {selectors[selector]} times")
                found_harvest = True
        
        print(f"  📈 {len(txs)} recent transactions")
        print(f"  👥 {len(unique_callers)} unique EOA callers")
        print(f"  📊 Publicness score: {publicness:.1%}")
        
        # Show most called functions
        if selectors:
            print(f"  🔧 Most called selectors:")
            sorted_selectors = sorted(selectors.items(), key=lambda x: x[1], reverse=True)
            for sel, count in sorted_selectors[:3]:
                print(f"     {sel}: {count} calls")
        
        return {
            'address': strategy_addr,
            'tx_count': len(txs),
            'selectors': selectors,
            'unique_eoas': len(unique_callers),
            'publicness': publicness,
            'likely_harvestable': found_harvest or publicness > 0.4,
            'callers': list(unique_callers)[:5]  # Sample of callers
        }

def get_top_clm_strategies(chain: str = "arbitrum", limit: int = 10) -> List[str]:
    """Get top CLM strategy addresses to analyze"""
    print(f"📋 Fetching top CLM vaults for {chain}...")
    
    # Get CLM vaults from API
    response = requests.get("https://api.beefy.finance/cow-vaults")
    vaults = response.json()
    
    # Filter for chain
    chain_vaults = [v for v in vaults if v.get('chain') == chain 
                   and v.get('status') == 'active']
    
    # Sort by TVL
    chain_vaults.sort(key=lambda x: x.get('tvl', 0), reverse=True)
    
    # Get strategy addresses
    strategies = []
    w3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC if chain == "arbitrum" else BASE_RPC))
    
    for vault in chain_vaults[:limit*2]:  # Get more to account for failures
        vault_addr = vault.get('earnContractAddress')
        if not vault_addr:
            continue
            
        # Try to get strategy address
        try:
            strategy_selector = "0xa8c62e76"  # strategy()
            result = w3.eth.call({
                'to': vault_addr,
                'data': strategy_selector
            })
            
            if result and len(result) == 32:
                strategy = "0x" + result.hex()[-40:]
                if strategy != "0x" + "0"*40:
                    strategies.append({
                        'vault_id': vault.get('id', ''),
                        'strategy': Web3.to_checksum_address(strategy),
                        'tvl': vault.get('tvl', 0)
                    })
                    if len(strategies) >= limit:
                        break
        except:
            continue
    
    return strategies

def main():
    print("="*60)
    print("CLM STRATEGY TRANSACTION HISTORY ANALYSIS")
    print("="*60)
    
    # Analyze Arbitrum strategies
    analyzer = TxHistoryAnalyzer("arbitrum")
    strategies = get_top_clm_strategies("arbitrum", limit=10)
    
    print(f"\n✅ Found {len(strategies)} strategies to analyze")
    
    harvestable = []
    
    for strat_info in strategies:
        result = analyzer.analyze_strategy(strat_info['strategy'])
        
        if result['likely_harvestable']:
            harvestable.append({
                **strat_info,
                **result
            })
    
    # Results summary
    print("\n" + "="*60)
    print("ANALYSIS RESULTS")
    print("="*60)
    
    if harvestable:
        print(f"\n✅ Found {len(harvestable)} likely harvestable strategies:")
        
        for h in harvestable:
            print(f"\n📍 {h['vault_id']}")
            print(f"   Strategy: {h['strategy']}")
            print(f"   TVL: ${h['tvl']:,.0f}")
            print(f"   Publicness: {h['publicness']:.1%}")
            print(f"   Unique EOAs: {h['unique_eoas']}")
            
            # Show most called selector
            if h['selectors']:
                top_sel = max(h['selectors'].items(), key=lambda x: x[1])
                print(f"   Most called: {top_sel[0]} ({top_sel[1]} times)")
        
        # Save results
        output = {
            'analyzed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'chain': 'arbitrum',
            'harvestable_strategies': harvestable
        }
        
        with open('tx_history_analysis.json', 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Saved analysis to tx_history_analysis.json")
    else:
        print("\n⚠️ No clearly harvestable strategies found")
        print("  This might indicate:")
        print("  - Strategies use non-standard functions")
        print("  - They're permission-gated")
        print("  - Low transaction activity")
    
    print("\n🎯 Next steps:")
    print("  1. Manually verify promising strategies on Arbiscan")
    print("  2. Test identified selectors with eth_call")
    print("  3. Monitor successful callers for patterns")

if __name__ == "__main__":
    main()