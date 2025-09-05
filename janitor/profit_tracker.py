"""
Profit tracking and reconciliation module
Analyzes actual on-chain rewards vs estimates
"""

import logging
from typing import Dict, Any, List, Optional
from web3 import Web3
from web3.types import TxReceipt
from decimal import Decimal
import json

logger = logging.getLogger(__name__)

class ProfitTracker:
    """Track and reconcile actual vs estimated profits"""
    
    def __init__(self, w3: Web3):
        self.w3 = w3
        
        # Common token addresses on Arbitrum
        self.known_tokens = {
            '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1': {'symbol': 'WETH', 'decimals': 18},
            '0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f': {'symbol': 'WBTC', 'decimals': 8},
            '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9': {'symbol': 'USDT', 'decimals': 6},
            '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8': {'symbol': 'USDC', 'decimals': 6},
            '0x912CE59144191C1204E64559FE8253a0e49E6548': {'symbol': 'ARB', 'decimals': 18},
            '0x6fE14d3CC2f7bDdffBa5CdB3BBE7467dd81ea101': {'symbol': 'COTI', 'decimals': 18},
            '0x6C2C06790b3E3E3c38e12Ee22F8183b37a13EE55': {'symbol': 'DPX', 'decimals': 18},
            '0x539bdE0d7Dbd336b79148AA742883198BBF60342': {'symbol': 'MAGIC', 'decimals': 18},
        }
        
        # ERC20 Transfer event signature
        self.transfer_topic = Web3.keccak(text="Transfer(address,address,uint256)").hex()
        
    def analyze_harvest_receipt(
        self, 
        tx_receipt: TxReceipt,
        harvester_address: str
    ) -> Dict[str, Any]:
        """
        Analyze a harvest transaction receipt to extract actual rewards
        
        Returns:
            Dict containing:
            - rewards: List of token rewards received
            - total_value_usd: Estimated total USD value
            - gas_used: Actual gas used
            - gas_price: Actual gas price paid
            - net_cost_eth: Actual transaction cost in ETH
        """
        
        result = {
            'rewards': [],
            'total_value_usd': 0.0,
            'gas_used': tx_receipt['gasUsed'],
            'gas_price': tx_receipt.get('effectiveGasPrice', 0),
            'net_cost_eth': 0.0,
            'success': tx_receipt['status'] == 1
        }
        
        # Calculate actual gas cost
        if result['gas_price'] > 0:
            result['net_cost_eth'] = (result['gas_used'] * result['gas_price']) / 1e18
        
        if not result['success']:
            return result
        
        # Parse logs for Transfer events TO the harvester
        harvester_address = Web3.to_checksum_address(harvester_address)
        
        for log in tx_receipt.get('logs', []):
            # Check if this is a Transfer event
            if len(log['topics']) >= 3 and log['topics'][0] == self.transfer_topic:
                # Transfer(from, to, value)
                # topics[0] = event signature
                # topics[1] = from address (padded)
                # topics[2] = to address (padded)
                # data = amount
                
                to_address = '0x' + log['topics'][2][-40:]  # Extract address from topic
                to_address = Web3.to_checksum_address(to_address)
                
                # Check if transfer is TO our harvester address
                if to_address == harvester_address:
                    token_address = Web3.to_checksum_address(log['address'])
                    
                    # Decode amount from data
                    amount_raw = int(log['data'], 16) if log['data'] else 0
                    
                    # Get token info
                    token_info = self.known_tokens.get(token_address, {
                        'symbol': f'Unknown({token_address[:8]}...)',
                        'decimals': 18
                    })
                    
                    # Convert to human-readable amount
                    amount = amount_raw / (10 ** token_info['decimals'])
                    
                    reward = {
                        'token_address': token_address,
                        'symbol': token_info['symbol'],
                        'amount_raw': amount_raw,
                        'amount': amount,
                        'decimals': token_info['decimals']
                    }
                    
                    result['rewards'].append(reward)
                    
                    logger.info(f"Found reward: {amount:.6f} {token_info['symbol']} to {harvester_address[:10]}...")
        
        # Also check for direct ETH transfers (not common in harvests but possible)
        if tx_receipt.get('value', 0) > 0:
            eth_amount = tx_receipt['value'] / 1e18
            result['rewards'].append({
                'token_address': 'ETH',
                'symbol': 'ETH',
                'amount_raw': tx_receipt['value'],
                'amount': eth_amount,
                'decimals': 18
            })
        
        return result
    
    def get_token_info(self, token_address: str) -> Dict[str, Any]:
        """Get token symbol and decimals from contract"""
        try:
            # Load minimal ERC20 ABI
            erc20_abi = [
                {"inputs":[],"name":"symbol","outputs":[{"type":"string"}],"type":"function","stateMutability":"view"},
                {"inputs":[],"name":"decimals","outputs":[{"type":"uint8"}],"type":"function","stateMutability":"view"},
                {"inputs":[],"name":"name","outputs":[{"type":"string"}],"type":"function","stateMutability":"view"}
            ]
            
            contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=erc20_abi
            )
            
            symbol = contract.functions.symbol().call()
            decimals = contract.functions.decimals().call()
            
            # Cache for future use
            self.known_tokens[token_address] = {
                'symbol': symbol,
                'decimals': decimals
            }
            
            return {'symbol': symbol, 'decimals': decimals}
            
        except Exception as e:
            logger.warning(f"Could not get token info for {token_address}: {e}")
            return {'symbol': 'Unknown', 'decimals': 18}
    
    def estimate_usd_value(self, rewards: List[Dict], prices: Dict[str, float]) -> float:
        """
        Estimate USD value of rewards
        
        Args:
            rewards: List of reward dicts from analyze_harvest_receipt
            prices: Dict of token_symbol -> USD price
        """
        total_usd = 0.0
        
        for reward in rewards:
            symbol = reward['symbol']
            amount = reward['amount']
            
            # Try to find price
            price = prices.get(symbol, 0.0)
            
            # Special handling for wrapped tokens
            if symbol == 'WETH' and 'ETH' in prices:
                price = prices['ETH']
            elif symbol == 'WBTC' and 'BTC' in prices:
                price = prices['BTC']
            
            value = amount * price
            total_usd += value
            
            if value > 0:
                logger.info(f"Reward value: {amount:.6f} {symbol} @ ${price:.2f} = ${value:.4f}")
        
        return total_usd


class ProfitReconciler:
    """Reconcile estimated vs actual profits"""
    
    def __init__(self, db, profit_tracker: ProfitTracker):
        self.db = db
        self.tracker = profit_tracker
        
    def reconcile_transaction(
        self,
        tx_hash: str,
        estimated_reward_usd: float,
        estimated_gas_usd: float,
        actual_receipt: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare estimated vs actual profits
        
        Returns reconciliation report
        """
        
        # Calculate actual gas cost in USD
        actual_gas_eth = actual_receipt['net_cost_eth']
        eth_price = 2500.0  # TODO: Get from price feed
        actual_gas_usd = actual_gas_eth * eth_price
        
        # Get actual rewards value
        # TODO: Integrate with price feeds
        actual_reward_usd = actual_receipt.get('total_value_usd', 0.0)
        
        # Calculate differences
        reward_diff = actual_reward_usd - estimated_reward_usd
        gas_diff = actual_gas_usd - estimated_gas_usd
        
        estimated_net = estimated_reward_usd - estimated_gas_usd
        actual_net = actual_reward_usd - actual_gas_usd
        net_diff = actual_net - estimated_net
        
        reconciliation = {
            'tx_hash': tx_hash,
            'estimated': {
                'reward_usd': estimated_reward_usd,
                'gas_usd': estimated_gas_usd,
                'net_usd': estimated_net
            },
            'actual': {
                'reward_usd': actual_reward_usd,
                'gas_usd': actual_gas_usd,
                'net_usd': actual_net,
                'gas_used': actual_receipt['gas_used'],
                'rewards': actual_receipt['rewards']
            },
            'variance': {
                'reward_usd': reward_diff,
                'gas_usd': gas_diff,
                'net_usd': net_diff,
                'reward_pct': (reward_diff / estimated_reward_usd * 100) if estimated_reward_usd > 0 else 0,
                'gas_pct': (gas_diff / estimated_gas_usd * 100) if estimated_gas_usd > 0 else 0
            },
            'success': actual_receipt['success']
        }
        
        # Log significant variances
        if abs(reconciliation['variance']['reward_pct']) > 20:
            logger.warning(
                f"Significant reward variance for {tx_hash[:10]}...: "
                f"estimated ${estimated_reward_usd:.2f}, actual ${actual_reward_usd:.2f} "
                f"({reconciliation['variance']['reward_pct']:+.1f}%)"
            )
        
        return reconciliation
    
    def save_reconciliation(self, reconciliation: Dict[str, Any]):
        """Save reconciliation to database"""
        with self.db.get_conn() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO profit_reconciliation (
                    tx_hash, timestamp, 
                    estimated_reward_usd, estimated_gas_usd, estimated_net_usd,
                    actual_reward_usd, actual_gas_usd, actual_net_usd,
                    variance_reward_usd, variance_gas_usd, variance_net_usd,
                    variance_reward_pct, variance_gas_pct,
                    actual_rewards_json
                ) VALUES (?, datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                reconciliation['tx_hash'],
                reconciliation['estimated']['reward_usd'],
                reconciliation['estimated']['gas_usd'],
                reconciliation['estimated']['net_usd'],
                reconciliation['actual']['reward_usd'],
                reconciliation['actual']['gas_usd'],
                reconciliation['actual']['net_usd'],
                reconciliation['variance']['reward_usd'],
                reconciliation['variance']['gas_usd'],
                reconciliation['variance']['net_usd'],
                reconciliation['variance']['reward_pct'],
                reconciliation['variance']['gas_pct'],
                json.dumps(reconciliation['actual']['rewards'])
            ))