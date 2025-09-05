#!/usr/bin/env python3
"""
Evaluate all current janitor bot vaults using the scoring rubric
"""

import json
import sys
from vault_scoring import VaultEvaluator, VaultScore
from typing import List, Dict

def load_current_targets() -> Dict:
    """Load current targets from janitor config"""
    with open('janitor/targets.json', 'r') as f:
        config = json.load(f)
    
    all_targets = []
    for chain, chain_config in config['chains'].items():
        for target in chain_config['targets']:
            target['_chain'] = chain
            all_targets.append(target)
    
    return all_targets

def evaluate_current_vaults():
    """Evaluate all current vaults"""
    print("="*80)
    print("COMPREHENSIVE VAULT EVALUATION REPORT")
    print("="*80)
    
    targets = load_current_targets()
    print(f"\n📋 Evaluating {len(targets)} vaults across all chains...")
    
    # Group by chain
    by_chain = {}
    for target in targets:
        chain = target['_chain']
        if chain not in by_chain:
            by_chain[chain] = []
        by_chain[chain].append(target)
    
    all_scores = []
    
    for chain, chain_targets in by_chain.items():
        print(f"\n{'='*60}")
        print(f"CHAIN: {chain.upper()}")
        print(f"{'='*60}")
        
        evaluator = VaultEvaluator(chain)
        
        for target in chain_targets:
            # Skip non-harvest targets
            if target.get('type') != 'harvest':
                continue
            
            # Estimate values based on config
            tvl = target.get('_tvl', 1_000_000)  # Default 1M if not specified
            
            # Determine protocol
            protocol = 'unknown'
            if 'beefy' in target['name'].lower():
                protocol = 'beefy'
            elif 'clm' in target['name'].lower():
                protocol = 'beefy'  # CLM is Beefy's concentrated liquidity
            
            # Estimate frequency from cooldown
            cooldown_sec = target.get('cooldownSec', 43200)
            frequency_hours = cooldown_sec / 3600
            
            # Get expected reward
            expected_reward = target.get('fixedRewardUSD', 0.40)
            
            print(f"\n📊 Evaluating: {target['name']}")
            print(f"   Address: {target['address'][:10]}...{target['address'][-8:]}")
            
            score = evaluator.evaluate_vault(
                vault_name=target['name'],
                address=target['address'],
                tvl_usd=tvl,
                protocol=protocol,
                harvest_frequency_hours=frequency_hours,
                expected_reward_usd=expected_reward
            )
            
            # Add chain info
            score.chain = chain
            all_scores.append(score)
            
            # Print mini report
            print(f"   Score: {score.total_score}/24 - {score.recommendation}")
            print(f"   Enabled: {'✅' if target.get('enabled', True) else '❌'}")
    
    # Sort all scores
    all_scores.sort(key=lambda x: x.total_score, reverse=True)
    
    print("\n" + "="*80)
    print("TOP PERFORMERS (Score >= 20)")
    print("="*80)
    
    top_performers = [s for s in all_scores if s.total_score >= 20]
    if top_performers:
        for score in top_performers:
            print(f"\n🏆 {score.vault_name} ({score.chain})")
            print(f"   Score: {score.total_score}/24")
            print(f"   TVL: ${score.tvl_amount:,.0f}")
            print(f"   Address: {score.address[:10]}...{score.address[-8:]}")
    else:
        print("\n⚠️ No vaults scored 20+ points")
    
    print("\n" + "="*80)
    print("RECOMMENDED ACTIONS")
    print("="*80)
    
    # Group by recommendation
    highly_recommended = [s for s in all_scores if s.total_score >= 20]
    recommended = [s for s in all_scores if 16 <= s.total_score < 20]
    marginal = [s for s in all_scores if 12 <= s.total_score < 16]
    not_recommended = [s for s in all_scores if s.total_score < 12]
    
    print(f"\n✅ Highly Recommended ({len(highly_recommended)} vaults):")
    for s in highly_recommended:
        print(f"   - {s.vault_name} ({s.chain}): {s.total_score}/24")
    
    print(f"\n✅ Recommended ({len(recommended)} vaults):")
    for s in recommended:
        print(f"   - {s.vault_name} ({s.chain}): {s.total_score}/24")
    
    print(f"\n⚠️ Marginal ({len(marginal)} vaults):")
    for s in marginal:
        print(f"   - {s.vault_name} ({s.chain}): {s.total_score}/24")
    
    print(f"\n❌ Not Recommended ({len(not_recommended)} vaults):")
    for s in not_recommended:
        print(f"   - {s.vault_name} ({s.chain}): {s.total_score}/24")
    
    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    
    avg_score = sum(s.total_score for s in all_scores) / len(all_scores) if all_scores else 0
    
    print(f"\n📊 Total Vaults Evaluated: {len(all_scores)}")
    print(f"📊 Average Score: {avg_score:.1f}/24")
    print(f"📊 Distribution:")
    print(f"   - Highly Recommended (20-24): {len(highly_recommended)} vaults")
    print(f"   - Recommended (16-19): {len(recommended)} vaults")
    print(f"   - Marginal (12-15): {len(marginal)} vaults")
    print(f"   - Not Recommended (<12): {len(not_recommended)} vaults")
    
    # Save detailed report
    report = {
        'timestamp': __import__('datetime').datetime.now().isoformat(),
        'total_vaults': len(all_scores),
        'average_score': avg_score,
        'by_recommendation': {
            'highly_recommended': [s.vault_name for s in highly_recommended],
            'recommended': [s.vault_name for s in recommended],
            'marginal': [s.vault_name for s in marginal],
            'not_recommended': [s.vault_name for s in not_recommended]
        },
        'detailed_scores': [
            {
                'name': s.vault_name,
                'chain': s.chain,
                'address': s.address,
                'total_score': s.total_score,
                'recommendation': s.recommendation,
                'tvl': s.tvl_amount,
                'scores': {
                    'call_surface': s.call_surface.value[0],
                    'incentive_clarity': s.incentive_clarity.value[0],
                    'cadence': s.cadence.value[0],
                    'tvl': s.tvl.value[0],
                    'gas_headroom': s.gas_headroom.value[0],
                    'no_odd_roles': s.no_odd_roles.value[0]
                }
            }
            for s in all_scores
        ]
    }
    
    with open('vault_evaluation_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Detailed report saved to vault_evaluation_report.json")
    
    return all_scores

if __name__ == "__main__":
    evaluate_current_vaults()