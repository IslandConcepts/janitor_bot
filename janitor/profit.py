import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def estimate_profit_usd(
    chain: Dict[str, Any],
    target: Dict[str, Any],
    onchain_state: Dict[str, Any],
    base_fee_gwei: float
) -> Dict[str, float]:
    """
    Estimate profit in USD for a given target
    
    Returns:
        Dict with keys: reward_usd, gas_usd, net_usd, is_profitable
    """
    
    result = {
        'reward_usd': 0.0,
        'gas_usd': 0.0,
        'net_usd': 0.0,
        'is_profitable': False
    }
    
    try:
        # Calculate expected reward
        if target['type'] == 'harvest':
            result['reward_usd'] = calculate_harvest_reward(target, onchain_state)
        elif target['type'] == 'twap':
            result['reward_usd'] = target.get('fixedRewardUSD', 0.0)
        elif target['type'] == 'compound':
            result['reward_usd'] = calculate_compound_reward(target, onchain_state)
        
        # Calculate gas cost
        result['gas_usd'] = estimate_gas_cost_usd(chain, target, base_fee_gwei)
        
        # Calculate net profit
        result['net_usd'] = result['reward_usd'] - result['gas_usd']
        result['is_profitable'] = result['net_usd'] > 0
        
        logger.debug(f"Profit estimate for {target['name']}: reward=${result['reward_usd']:.4f}, "
                    f"gas=${result['gas_usd']:.4f}, net=${result['net_usd']:.4f}")
        
    except Exception as e:
        logger.error(f"Profit calculation error for {target['name']}: {e}")
    
    return result

def calculate_harvest_reward(target: Dict[str, Any], onchain_state: Dict[str, Any]) -> float:
    """Calculate expected reward from harvest operation"""
    
    # If we have a fixed reward estimate, use it
    if 'fixedRewardUSD' in target:
        return target['fixedRewardUSD']
    
    # Otherwise try to calculate from pending rewards
    pending = onchain_state.get('pending', 0)
    
    if pending == 0:
        return 0.0
    
    # Convert pending rewards to decimal format
    decimals = target.get('rewardTokenDecimals', 18)
    pending_decimal = pending / (10 ** decimals)
    
    # Apply call fee (in basis points)
    call_fee_bps = target.get('callFeeBps', 0)
    reward_tokens = pending_decimal * (call_fee_bps / 10000)
    
    # Convert to USD
    price_usd = target.get('rewardPriceUSD', 0.0)
    reward_usd = reward_tokens * price_usd
    
    return reward_usd

def calculate_compound_reward(target: Dict[str, Any], onchain_state: Dict[str, Any]) -> float:
    """Calculate expected reward from compound operation"""
    # Similar to harvest but may have different fee structure
    pending = onchain_state.get('pendingCompound', 0)
    
    if pending == 0:
        return 0.0
    
    decimals = target.get('rewardTokenDecimals', 18)
    pending_decimal = pending / (10 ** decimals)
    
    compound_fee_bps = target.get('compoundFeeBps', 50)  # Default 0.5%
    reward_tokens = pending_decimal * (compound_fee_bps / 10000)
    
    price_usd = target.get('rewardPriceUSD', 0.0)
    reward_usd = reward_tokens * price_usd
    
    return reward_usd

def estimate_gas_cost_usd(chain: Dict[str, Any], target: Dict[str, Any], base_fee_gwei: float) -> float:
    """Estimate gas cost in USD"""
    # Get gas limit for this operation type
    gas_limit = chain['gasLimitCaps'].get(target['type'], 500000)
    
    # Calculate max fee (base + priority)
    priority_fee_gwei = 0.05  # Conservative priority fee
    max_fee_gwei = base_fee_gwei + priority_fee_gwei
    
    # Calculate gas cost in ETH
    gas_cost_eth = (gas_limit * max_fee_gwei) / 1e9
    
    # Convert to USD
    native_price_usd = chain.get('nativeUsd', 2500.0)
    gas_cost_usd = gas_cost_eth * native_price_usd
    
    return gas_cost_usd

def passes_profit_gate(estimate: Dict[str, float], config: Dict[str, Any]) -> bool:
    """Check if profit estimate passes configured thresholds"""
    global_config = config.get('global', {})
    
    # Check minimum net profit
    min_net = global_config.get('minNetUSD', 0.02)
    if estimate['net_usd'] < min_net:
        return False
    
    # Check profit multiplier (reward must be >= X times gas cost)
    multiplier = global_config.get('profitMultiplier', 1.5)
    if estimate['reward_usd'] < (estimate['gas_usd'] * multiplier):
        return False
    
    return True

def get_min_pending_threshold(target: Dict[str, Any]) -> int:
    """Calculate minimum pending rewards threshold"""
    if 'minPendingRewardTokens' in target and target['minPendingRewardTokens'] != 'auto':
        decimals = target.get('rewardTokenDecimals', 18)
        return int(target['minPendingRewardTokens'] * (10 ** decimals))
    
    # Auto-calculate based on call fee and minimum profit
    # Rough calculation: we want at least $1 in rewards after fees
    min_reward_usd = 1.0
    price_usd = target.get('rewardPriceUSD', 1.0)
    call_fee_bps = target.get('callFeeBps', 50)
    
    if price_usd > 0 and call_fee_bps > 0:
        # Reverse calculate: min_reward_usd = tokens * (fee/10000) * price
        # tokens = min_reward_usd * 10000 / (fee * price)
        min_tokens = (min_reward_usd * 10000) / (call_fee_bps * price_usd)
        decimals = target.get('rewardTokenDecimals', 18)
        return int(min_tokens * (10 ** decimals))
    
    # Fallback to a reasonable default
    return 10 ** target.get('rewardTokenDecimals', 18)  # 1 token