#!/usr/bin/env python3
"""
Analyze recent transactions to CLM strategies to discover actual callable functions
Pull last N successful txs and build stats on selectors, callers, and cadence
"""

import json
import time
import requests
from web3 import Web3
from typing import List, Dict, Set, Tuple
from collections import defaultdict
from datetime import datetime, timedelta

# Configuration
ARBITRUM_RPC = "https://arb-mainnet.g.alchemy.com/v2/5mlDO-31svMGY53J2Urqv"
w3 = Web3(Web3.HTTPProvider(ARBITRUM_RPC))

class CLMTransactionAnalyzer:
    """Deep analysis of CLM strategy transactions"""
    
    def __init__(self):
        self.w3 = w3
        self.selector_names = {
            '0x4641257d': 'harvest()',
            '0x018ee9b7': 'harvest(address)',
            '0x3208fab2': 'harvest(address,uint256)',
            '0xa0712d68': 'compound()',
            '0xf69e2046': 'compound(address)',
            '0x7d7c8c1e': 'rebalance()',
            '0x440368a4': 'tend()',
            '0xc0406226': 'run()',
            '0x61461954': 'execute()',
            '0xc3f909d4': 'report()',
            '0xe26b013b': 'work()',
            '0xd389800f': 'earn()',
            '0x845a4697': 'processRewards()',
            '0x3e2d86d1': 'doHarvest()',
            '0x99114df2': 'report(uint256)',
        }
    
    def is_contract(self, address: str) -> bool:
        """Check if address is a contract"""
        try:
            code = self.w3.eth.get_code(address)
            return len(code) > 2
        except:
            return False
    
    def get_recent_transactions(self, address: str, blocks_back: int = 50000) -> List[Dict]:
        """Get recent transactions using eth_getLogs"""
        print(f"\n📊 Fetching transactions for {address[:10]}...")
        
        current_block = self.w3.eth.block_number
        start_block = current_block - blocks_back
        
        # Use Alchemy's enhanced API to get transactions
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "alchemy_getAssetTransfers",
            "params": [{
                "fromBlock": hex(start_block),
                "toBlock": hex(current_block),
                "toAddress": address,
                "category": ["external"],
                "maxCount": "0x3e8"  # 1000 transactions
            }]
        }
        
        try:
            response = requests.post(ARBITRUM_RPC, json=payload)
            result = response.json()
            
            if 'result' in result and 'transfers' in result['result']:
                transfers = result['result']['transfers']
                print(f"  Found {len(transfers)} transfers")
                
                # Get full transaction details for each
                transactions = []
                for transfer in transfers[:100]:  # Limit to 100 for speed
                    tx_hash = transfer.get('hash')
                    if tx_hash:
                        try:
                            tx = self.w3.eth.get_transaction(tx_hash)
                            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
                            
                            transactions.append({
                                'hash': tx_hash,
                                'from': tx['from'],
                                'to': tx['to'],
                                'input': tx['input'],
                                'blockNumber': tx['blockNumber'],
                                'status': receipt['status'],
                                'gasUsed': receipt['gasUsed']
                            })
                        except:
                            continue
                
                return transactions
        except Exception as e:
            print(f"  Error fetching transfers: {e}")
        
        # Fallback: scan recent blocks
        transactions = []
        print(f"  Scanning blocks {start_block} to {current_block}...")
        
        # Sample blocks (every 1000th block)
        for block_num in range(current_block, start_block, -1000):
            try:
                block = self.w3.eth.get_block(block_num, True)
                
                for tx in block.transactions:
                    if tx.get('to') and tx['to'].lower() == address.lower():
                        # Get receipt for status
                        receipt = self.w3.eth.get_transaction_receipt(tx['hash'])
                        
                        transactions.append({
                            'hash': tx['hash'].hex(),
                            'from': tx['from'],
                            'to': tx['to'], 
                            'input': tx['input'],
                            'blockNumber': block_num,
                            'status': receipt['status'],
                            'gasUsed': receipt['gasUsed']
                        })
                        
                        if len(transactions) >= 100:
                            return transactions
            except:
                continue
        
        return transactions
    
    def analyze_strategy(self, address: str, vault_name: str = "") -> Dict:
        """Analyze a strategy's transaction patterns"""
        print(f"\n{'='*60}")
        print(f"Analyzing: {vault_name or address}")
        
        # Get transactions
        txs = self.get_recent_transactions(address)
        
        if not txs:
            print("  ❌ No transactions found")
            return {
                'address': address,
                'name': vault_name,
                'tx_count': 0,
                'selectors': {},
                'eoa_callers': [],
                'contract_callers': [],
                'publicness': 0,
                'cadence_hours': None,
                'likely_callable': []
            }
        
        # Analyze transactions
        selector_stats = defaultdict(lambda: {
            'count': 0,
            'success_count': 0,
            'eoa_callers': set(),
            'contract_callers': set(),
            'gas_used': [],
            'timestamps': []
        })
        
        all_eoa_callers = set()
        all_contract_callers = set()
        
        for tx in txs:
            # Skip failed transactions for selector analysis
            if tx['status'] != 1:
                continue
                
            # Extract selector
            input_data = tx.get('input', '')
            if len(input_data) < 10:
                continue
                
            selector = input_data[:10]
            caller = tx['from']
            
            # Check if caller is contract
            is_caller_contract = self.is_contract(caller)
            
            # Update stats
            stats = selector_stats[selector]
            stats['count'] += 1
            stats['success_count'] += 1
            stats['gas_used'].append(tx['gasUsed'])
            
            if is_caller_contract:
                stats['contract_callers'].add(caller.lower())
                all_contract_callers.add(caller.lower())
            else:
                stats['eoa_callers'].add(caller.lower())
                all_eoa_callers.add(caller.lower())
        
        # Calculate publicness (based on unique EOA callers)
        publicness = self.calculate_publicness(len(all_eoa_callers))
        
        # Find likely callable selectors
        likely_callable = []
        
        print(f"\n📈 Transaction Analysis:")
        print(f"  Total transactions: {len(txs)}")
        print(f"  Successful: {sum(1 for tx in txs if tx['status'] == 1)}")
        print(f"  Unique EOA callers: {len(all_eoa_callers)}")
        print(f"  Unique contract callers: {len(all_contract_callers)}")
        print(f"  Publicness score: {publicness:.1%}")
        
        if selector_stats:
            print(f"\n🔧 Selector Analysis:")
            
            # Sort by frequency
            sorted_selectors = sorted(
                selector_stats.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )
            
            for selector, stats in sorted_selectors[:5]:
                func_name = self.selector_names.get(selector, "Unknown")
                eoa_count = len(stats['eoa_callers'])
                contract_count = len(stats['contract_callers'])
                avg_gas = sum(stats['gas_used']) / len(stats['gas_used']) if stats['gas_used'] else 0
                
                print(f"\n  {selector}: {func_name}")
                print(f"    Calls: {stats['count']}")
                print(f"    EOA callers: {eoa_count}")
                print(f"    Contract callers: {contract_count}")
                print(f"    Avg gas: {avg_gas:,.0f}")
                
                # Mark as likely callable if has multiple EOA callers
                if eoa_count >= 2:
                    likely_callable.append({
                        'selector': selector,
                        'name': func_name,
                        'eoa_callers': eoa_count,
                        'total_calls': stats['count']
                    })
                    print(f"    ✅ Likely callable!")
                
                # Show sample callers
                if stats['eoa_callers']:
                    sample_eoas = list(stats['eoa_callers'])[:2]
                    print(f"    Sample EOAs: {', '.join(addr[:10] for addr in sample_eoas)}")
        
        # Calculate cadence (time between calls)
        if len(txs) >= 2:
            # Estimate based on block numbers
            block_diffs = []
            for i in range(1, len(txs)):
                diff = abs(txs[i]['blockNumber'] - txs[i-1]['blockNumber'])
                block_diffs.append(diff)
            
            if block_diffs:
                avg_blocks = sum(block_diffs) / len(block_diffs)
                # ~12 seconds per block on Arbitrum
                cadence_hours = (avg_blocks * 12) / 3600
                print(f"\n⏱️  Average cadence: {cadence_hours:.1f} hours between calls")
            else:
                cadence_hours = None
        else:
            cadence_hours = None
        
        return {
            'address': address,
            'name': vault_name,
            'tx_count': len(txs),
            'selectors': dict(selector_stats),
            'eoa_callers': list(all_eoa_callers)[:10],  # Sample
            'contract_callers': list(all_contract_callers)[:5],  # Sample
            'publicness': publicness,
            'cadence_hours': cadence_hours,
            'likely_callable': likely_callable
        }
    
    def calculate_publicness(self, unique_eoa_count: int) -> float:
        """Calculate publicness score"""
        if unique_eoa_count >= 10:
            return 1.0
        elif unique_eoa_count >= 5:
            return 0.8
        elif unique_eoa_count >= 3:
            return 0.6
        elif unique_eoa_count >= 2:
            return 0.4
        else:
            return 0.1

def get_top_clm_strategies() -> List[Dict]:
    """Get top CLM strategies to analyze"""
    print("📋 Fetching top CLM vaults...")
    
    response = requests.get("https://api.beefy.finance/cow-vaults")
    vaults = response.json()
    
    # Filter for Arbitrum active CLM vaults
    arb_clm = []
    for vault in vaults:
        if (vault.get('chain') == 'arbitrum' and 
            vault.get('status') == 'active' and
            vault.get('earnContractAddress')):
            
            # Try to get strategy address
            vault_addr = vault['earnContractAddress']
            try:
                strategy_selector = "0xa8c62e76"  # strategy()
                result = w3.eth.call({
                    'to': vault_addr,
                    'data': strategy_selector
                })
                
                if result and len(result) == 32:
                    strategy = "0x" + result.hex()[-40:]
                    if strategy != "0x" + "0"*40:
                        arb_clm.append({
                            'id': vault.get('id', ''),
                            'vault': vault_addr,
                            'strategy': Web3.to_checksum_address(strategy),
                            'tvl': vault.get('tvl', 0)
                        })
            except:
                continue
    
    # Sort by TVL
    arb_clm.sort(key=lambda x: x['tvl'], reverse=True)
    return arb_clm[:20]  # Top 20

def main():
    print("="*60)
    print("CLM STRATEGY DEEP TRANSACTION ANALYSIS")
    print("="*60)
    
    analyzer = CLMTransactionAnalyzer()
    
    # Get top CLM strategies
    strategies = get_top_clm_strategies()
    print(f"\n✅ Found {len(strategies)} CLM strategies to analyze")
    
    # Analyze each
    harvestable = []
    
    for i, strat in enumerate(strategies[:10]):  # Analyze top 10
        result = analyzer.analyze_strategy(
            strat['strategy'],
            strat['id']
        )
        
        if result['likely_callable']:
            harvestable.append(result)
    
    # Summary
    print("\n" + "="*60)
    print("HARVESTABLE CLM STRATEGIES FOUND")
    print("="*60)
    
    if harvestable:
        print(f"\n✅ Found {len(harvestable)} potentially harvestable strategies:\n")
        
        for h in harvestable:
            print(f"\n📍 {h['name']}")
            print(f"   Address: {h['address']}")
            print(f"   Publicness: {h['publicness']:.1%}")
            print(f"   Likely callable functions:")
            
            for func in h['likely_callable']:
                print(f"     - {func['selector']}: {func['name']}")
                print(f"       EOA callers: {func['eoa_callers']}, Total calls: {func['total_calls']}")
        
        # Generate target configs
        targets = []
        for h in harvestable:
            if h['likely_callable']:
                best_func = h['likely_callable'][0]  # Use most popular
                
                # Determine function name and params
                func_name = best_func['name']
                if 'address' in func_name:
                    params = ["0x00823727Ec5800ae6f5068fABAEb39608dE8bf45"]
                else:
                    params = []
                
                target = {
                    "name": f"CLM_{h['name'].replace('-', '_')[:25]}",
                    "address": h['address'],
                    "abi": "abi/clm_strategy.json",
                    "type": "harvest",
                    "enabled": False,  # Start disabled for testing
                    "params": params,
                    "cooldownSec": 21600,
                    "fixedRewardUSD": 0.30,
                    "read": {
                        "lastHarvest": "lastHarvest"
                    },
                    "write": {
                        "exec": func_name.split('(')[0]
                    },
                    "_metadata": {
                        "selector": best_func['selector'],
                        "eoa_callers": best_func['eoa_callers'],
                        "publicness": h['publicness'],
                        "cadence_hours": h['cadence_hours']
                    }
                }
                targets.append(target)
        
        # Save results
        output = {
            'analyzed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'harvestable': harvestable,
            'targets': targets
        }
        
        with open('clm_tx_analysis.json', 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Saved {len(targets)} potential targets to clm_tx_analysis.json")
        print("\n🎯 Next steps:")
        print("  1. Test each function with eth_call")
        print("  2. Verify parameters needed")
        print("  3. Add working ones to targets.json")
    else:
        print("\n⚠️ No clearly harvestable strategies found")
        print("  Strategies may be using:")
        print("  - Non-standard function names")
        print("  - Complex access control")
        print("  - Proxy implementations")

if __name__ == "__main__":
    main()