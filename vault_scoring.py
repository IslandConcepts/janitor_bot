#!/usr/bin/env python3
"""
Vault Scoring System - Evaluates whether a vault is worth adding to the janitor bot
Based on: call surface, incentive clarity, cadence, TVL, gas headroom, and role restrictions
"""

import json
import time
from web3 import Web3
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class ScoreLevel(Enum):
    EXCELLENT = (4, "✅✅✅✅", "Excellent - Add immediately")
    GOOD = (3, "✅✅✅", "Good - Worth adding")
    MODERATE = (2, "✅✅", "Moderate - Consider with caution")
    POOR = (1, "✅", "Poor - Likely not worth it")
    FAIL = (0, "❌", "Fail - Do not add")

@dataclass
class VaultScore:
    """Detailed scoring for a vault"""
    vault_name: str
    address: str
    chain: str
    
    # Individual scores
    call_surface: ScoreLevel
    incentive_clarity: ScoreLevel
    cadence: ScoreLevel
    tvl: ScoreLevel
    gas_headroom: ScoreLevel
    no_odd_roles: ScoreLevel
    
    # Metadata
    tvl_amount: float
    harvest_frequency_hours: Optional[float]
    expected_reward_usd: Optional[float]
    gas_cost_usd: Optional[float]
    harvest_function: Optional[str]
    
    @property
    def total_score(self) -> int:
        """Calculate total score out of 24"""
        return (self.call_surface.value[0] + 
                self.incentive_clarity.value[0] + 
                self.cadence.value[0] + 
                self.tvl.value[0] + 
                self.gas_headroom.value[0] + 
                self.no_odd_roles.value[0])
    
    @property
    def recommendation(self) -> str:
        """Get recommendation based on total score"""
        score = self.total_score
        if score >= 20:
            return "🏆 HIGHLY RECOMMENDED - Add with high priority"
        elif score >= 16:
            return "✅ RECOMMENDED - Good candidate for harvesting"
        elif score >= 12:
            return "⚠️ MARGINAL - Add only if other metrics are strong"
        elif score >= 8:
            return "❌ NOT RECOMMENDED - Poor risk/reward"
        else:
            return "🚫 AVOID - Multiple red flags"
    
    def to_config(self) -> Dict:
        """Generate safe default config for targets.json"""
        # Determine parameters based on harvest function
        if self.harvest_function and "address" in self.harvest_function:
            params = ["0x00823727Ec5800ae6f5068fABAEb39608dE8bf45"]  # Your bot address
        else:
            params = []
        
        # Conservative cooldown based on cadence
        if self.harvest_frequency_hours and self.harvest_frequency_hours <= 6:
            cooldown_sec = 21600  # 6 hours for frequent harvests
        else:
            cooldown_sec = 43200  # 12 hours default
        
        # Conservative reward estimate
        if self.expected_reward_usd:
            fixed_reward = min(self.expected_reward_usd, 0.60)  # Cap at $0.60
        elif self.tvl_amount > 5_000_000:
            fixed_reward = 0.60
        elif self.tvl_amount > 1_000_000:
            fixed_reward = 0.40
        else:
            fixed_reward = 0.25
        
        return {
            "name": self.vault_name.replace("-", "_")[:30],
            "address": self.address,
            "abi": "abi/beefy_strategy.json",
            "type": "harvest",
            "enabled": self.total_score >= 16,  # Auto-enable good vaults
            "params": params,
            "cooldownSec": cooldown_sec,
            "fixedRewardUSD": fixed_reward,
            "read": {
                "lastHarvest": "lastHarvest"
            },
            "write": {
                "exec": "harvest"
            },
            "_score": self.total_score,
            "_recommendation": self.recommendation,
            "_tvl": self.tvl_amount
        }
    
    def print_report(self):
        """Print detailed scoring report"""
        print(f"\n{'='*60}")
        print(f"VAULT SCORING REPORT: {self.vault_name}")
        print(f"{'='*60}")
        print(f"Address: {self.address}")
        print(f"Chain: {self.chain}")
        print(f"TVL: ${self.tvl_amount:,.0f}")
        
        print(f"\n📊 SCORING BREAKDOWN:")
        print(f"  Call Surface:      {self.call_surface.value[1]} {self.call_surface.value[2]}")
        print(f"  Incentive Clarity: {self.incentive_clarity.value[1]} {self.incentive_clarity.value[2]}")
        print(f"  Cadence:          {self.cadence.value[1]} {self.cadence.value[2]}")
        print(f"  TVL Score:        {self.tvl.value[1]} {self.tvl.value[2]}")
        print(f"  Gas Headroom:     {self.gas_headroom.value[1]} {self.gas_headroom.value[2]}")
        print(f"  No Odd Roles:     {self.no_odd_roles.value[1]} {self.no_odd_roles.value[2]}")
        
        print(f"\n📈 TOTAL SCORE: {self.total_score}/24")
        print(f"🎯 {self.recommendation}")
        
        if self.harvest_frequency_hours:
            print(f"\n⏰ Harvest Frequency: Every {self.harvest_frequency_hours:.1f} hours")
        if self.expected_reward_usd and self.gas_cost_usd:
            net = self.expected_reward_usd - self.gas_cost_usd
            ratio = self.expected_reward_usd / self.gas_cost_usd if self.gas_cost_usd > 0 else 999
            print(f"💰 Economics: ${self.expected_reward_usd:.2f} reward - ${self.gas_cost_usd:.2f} gas = ${net:.2f} net")
            print(f"   Reward/Gas Ratio: {ratio:.1f}x")

class VaultEvaluator:
    """Evaluates vaults based on scoring rubric"""
    
    def __init__(self, chain: str = "arbitrum"):
        self.chain = chain
        if chain == "arbitrum":
            self.rpc = "https://arb-mainnet.g.alchemy.com/v2/5mlDO-31svMGY53J2Urqv"
            self.gas_price_gwei = 0.1
        elif chain == "base":
            self.rpc = "https://base-mainnet.g.alchemy.com/v2/3AvaLFHobnzEIToydrEiN"
            self.gas_price_gwei = 0.05
        else:
            raise ValueError(f"Unsupported chain: {chain}")
        
        self.w3 = Web3(Web3.HTTPProvider(self.rpc))
    
    def score_call_surface(self, address: str, bot_address: str = "0x00823727Ec5800ae6f5068fABAEb39608dE8bf45") -> Tuple[ScoreLevel, str]:
        """Score based on whether harvest is publicly callable"""
        # Test common harvest functions
        test_functions = [
            ("harvest()", "0x4641257d", []),
            ("harvest(address)", "0x018ee9b7", [bot_address]),
            ("compound()", "0xa0712d68", []),
            ("tend()", "0x440368a4", []),
        ]
        
        for func_name, selector, params in test_functions:
            try:
                # Build call data
                call_data = selector
                for param in params:
                    if isinstance(param, str) and param.startswith("0x"):
                        call_data += param[2:].lower().zfill(64)
                
                # Try calling
                self.w3.eth.call({
                    'from': bot_address,
                    'to': address,
                    'data': call_data
                })
                return ScoreLevel.EXCELLENT, func_name
            except Exception as e:
                error = str(e).lower()
                if "onlykeeper" in error or "restricted" in error or "forbidden" in error:
                    return ScoreLevel.FAIL, "Restricted to keeper role"
                elif "revert" in error:
                    # Function exists but reverted (might just be cooldown)
                    return ScoreLevel.GOOD, f"{func_name} (reverted - check cooldown)"
        
        return ScoreLevel.FAIL, "No callable harvest function found"
    
    def score_incentive_clarity(self, protocol: str, has_documented_fees: bool = False) -> ScoreLevel:
        """Score based on incentive documentation"""
        # Known good protocols
        if protocol.lower() in ["beefy", "reaper", "yearn"]:
            return ScoreLevel.EXCELLENT
        elif has_documented_fees:
            return ScoreLevel.GOOD
        else:
            return ScoreLevel.MODERATE  # Unknown but might work
    
    def score_cadence(self, harvest_frequency_hours: Optional[float]) -> ScoreLevel:
        """Score based on harvest frequency"""
        if not harvest_frequency_hours:
            return ScoreLevel.MODERATE
        
        if harvest_frequency_hours <= 6:
            return ScoreLevel.EXCELLENT  # Multiple daily harvests
        elif harvest_frequency_hours <= 12:
            return ScoreLevel.GOOD  # Twice daily
        elif harvest_frequency_hours <= 24:
            return ScoreLevel.MODERATE  # Daily
        elif harvest_frequency_hours <= 48:
            return ScoreLevel.POOR  # Every 2 days
        else:
            return ScoreLevel.FAIL  # Too infrequent
    
    def score_tvl(self, tvl_usd: float) -> ScoreLevel:
        """Score based on Total Value Locked"""
        if tvl_usd >= 5_000_000:
            return ScoreLevel.EXCELLENT  # >$5M
        elif tvl_usd >= 3_000_000:
            return ScoreLevel.GOOD  # $3-5M
        elif tvl_usd >= 1_000_000:
            return ScoreLevel.MODERATE  # $1-3M
        elif tvl_usd >= 500_000:
            return ScoreLevel.POOR  # $0.5-1M
        else:
            return ScoreLevel.FAIL  # <$500k
    
    def score_gas_headroom(self, expected_reward_usd: float, gas_cost_usd: float) -> ScoreLevel:
        """Score based on profit margin"""
        if gas_cost_usd > 0.20:
            # Gas too expensive for this chain
            if expected_reward_usd >= gas_cost_usd * 3:
                return ScoreLevel.MODERATE  # Very high reward compensates
            else:
                return ScoreLevel.POOR
        
        # Calculate profit metrics
        net_profit = expected_reward_usd - gas_cost_usd
        profit_ratio = expected_reward_usd / gas_cost_usd if gas_cost_usd > 0 else 999
        
        if profit_ratio >= 3.0 and net_profit >= 0.30:
            return ScoreLevel.EXCELLENT  # 3x+ gas cost and $0.30+ net
        elif profit_ratio >= 2.0 and net_profit >= 0.20:
            return ScoreLevel.GOOD  # 2x+ gas cost and $0.20+ net
        elif profit_ratio >= 1.5 and net_profit >= 0.10:
            return ScoreLevel.MODERATE  # 1.5x+ gas cost and $0.10+ net
        elif profit_ratio >= 1.2:
            return ScoreLevel.POOR  # Barely profitable
        else:
            return ScoreLevel.FAIL  # Not profitable
    
    def score_no_odd_roles(self, has_pausable: bool = False, has_allowlist: bool = False,
                           has_timelock: bool = False) -> ScoreLevel:
        """Score based on absence of restrictive mechanisms"""
        if has_allowlist:
            return ScoreLevel.FAIL  # Can't harvest if not on list
        elif has_pausable and has_timelock:
            return ScoreLevel.POOR  # Multiple restrictions
        elif has_pausable or has_timelock:
            return ScoreLevel.MODERATE  # One restriction
        else:
            return ScoreLevel.EXCELLENT  # No restrictions
    
    def evaluate_vault(self, 
                      vault_name: str,
                      address: str,
                      tvl_usd: float,
                      protocol: str = "unknown",
                      harvest_frequency_hours: Optional[float] = None,
                      expected_reward_usd: float = 0.40,
                      gas_estimate: int = 500000) -> VaultScore:
        """Comprehensive vault evaluation"""
        
        # Calculate gas cost
        gas_cost_usd = (gas_estimate * self.gas_price_gwei * 1e-9) * 2500  # Assuming ETH = $2500
        
        # Score each dimension
        call_score, harvest_func = self.score_call_surface(address)
        
        score = VaultScore(
            vault_name=vault_name,
            address=address,
            chain=self.chain,
            call_surface=call_score,
            incentive_clarity=self.score_incentive_clarity(protocol),
            cadence=self.score_cadence(harvest_frequency_hours),
            tvl=self.score_tvl(tvl_usd),
            gas_headroom=self.score_gas_headroom(expected_reward_usd, gas_cost_usd),
            no_odd_roles=self.score_no_odd_roles(),  # Assume no restrictions by default
            tvl_amount=tvl_usd,
            harvest_frequency_hours=harvest_frequency_hours,
            expected_reward_usd=expected_reward_usd,
            gas_cost_usd=gas_cost_usd,
            harvest_function=harvest_func if isinstance(harvest_func, str) else None
        )
        
        return score

def evaluate_batch(vaults: List[Dict]) -> List[VaultScore]:
    """Evaluate multiple vaults and rank them"""
    evaluator = VaultEvaluator(vaults[0].get('chain', 'arbitrum'))
    scores = []
    
    for vault in vaults:
        score = evaluator.evaluate_vault(
            vault_name=vault['name'],
            address=vault['address'],
            tvl_usd=vault.get('tvl', 0),
            protocol=vault.get('protocol', 'unknown'),
            harvest_frequency_hours=vault.get('frequency_hours'),
            expected_reward_usd=vault.get('expected_reward', 0.40)
        )
        scores.append(score)
    
    # Sort by total score
    scores.sort(key=lambda x: x.total_score, reverse=True)
    
    return scores

def main():
    """Example evaluation"""
    print("="*60)
    print("VAULT SCORING SYSTEM")
    print("="*60)
    
    # Example vault to evaluate
    example_vault = {
        'name': 'Beefy_WETH_USDC',
        'address': '0x9bd7A4b5D5Fe8C7dd39D085279306309fA6F1a15',
        'chain': 'base',
        'tvl': 3_500_000,
        'protocol': 'beefy',
        'frequency_hours': 12,
        'expected_reward': 0.50
    }
    
    evaluator = VaultEvaluator(example_vault['chain'])
    score = evaluator.evaluate_vault(
        vault_name=example_vault['name'],
        address=example_vault['address'],
        tvl_usd=example_vault['tvl'],
        protocol=example_vault['protocol'],
        harvest_frequency_hours=example_vault['frequency_hours'],
        expected_reward_usd=example_vault['expected_reward']
    )
    
    # Print detailed report
    score.print_report()
    
    # Generate config
    print("\n📝 SUGGESTED CONFIG:")
    config = score.to_config()
    print(json.dumps(config, indent=2))
    
    print("\n" + "="*60)
    print("SCORING RUBRIC REFERENCE:")
    print("="*60)
    print("""
    🎯 DIMENSIONS (4 points each, 24 total):
    
    1. CALL SURFACE: Can you call harvest publicly?
       - Excellent (4): Public harvest() works
       - Good (3): Public but reverts (cooldown)
       - Fail (0): Restricted to keeper role
    
    2. INCENTIVE CLARITY: Are caller rewards documented?
       - Excellent (4): Beefy/Reaper/Yearn (known good)
       - Good (3): Documented fees
       - Moderate (2): Unknown but possible
    
    3. CADENCE: How often is it harvested?
       - Excellent (4): ≤6 hours
       - Good (3): ≤12 hours
       - Moderate (2): ≤24 hours
       - Poor (1): ≤48 hours
       - Fail (0): >48 hours
    
    4. TVL: Total Value Locked
       - Excellent (4): ≥$5M
       - Good (3): $3-5M
       - Moderate (2): $1-3M
       - Poor (1): $0.5-1M
       - Fail (0): <$500k
    
    5. GAS HEADROOM: Profit margin
       - Excellent (4): 3x+ gas & $0.30+ net
       - Good (3): 2x+ gas & $0.20+ net
       - Moderate (2): 1.5x+ gas & $0.10+ net
       - Poor (1): 1.2x+ gas
       - Fail (0): <1.2x gas
    
    6. NO ODD ROLES: Absence of restrictions
       - Excellent (4): No restrictions
       - Moderate (2): One restriction
       - Poor (1): Multiple restrictions
       - Fail (0): Has allowlist
    
    📊 TOTAL SCORES:
       20-24: Highly Recommended
       16-19: Recommended
       12-15: Marginal
       8-11:  Not Recommended
       0-7:   Avoid
    """)

if __name__ == "__main__":
    main()