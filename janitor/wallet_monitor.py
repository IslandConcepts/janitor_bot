#!/usr/bin/env python3
"""
Wallet balance monitoring and reward verification
"""

import logging
import time
from typing import Dict, List, Optional, Any
from web3 import Web3
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class WalletMonitor:
    """Monitor wallet balances and verify harvested rewards"""
    
    def __init__(self, rpc_manager):
        self.rpc_manager = rpc_manager
        self.balance_history = {}  # chain -> token -> [(timestamp, balance)]
        self.last_check = {}  # chain -> timestamp
        
    def get_wallet_address(self, chain_config: Dict) -> str:
        """Get wallet address from private key"""
        from eth_account import Account
        account = Account.from_key(chain_config['privateKey'])
        return account.address
    
    def get_token_balance(self, w3: Web3, token_address: str, wallet_address: str) -> float:
        """Get ERC20 token balance"""
        try:
            # Standard ERC20 ABI for balanceOf
            abi = [{
                "inputs": [{"name": "account", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }, {
                "inputs": [],
                "name": "decimals",
                "outputs": [{"name": "", "type": "uint8"}],
                "type": "function"
            }, {
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "type": "function"
            }]
            
            contract = w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=abi
            )
            
            balance_raw = contract.functions.balanceOf(wallet_address).call()
            decimals = contract.functions.decimals().call()
            balance = balance_raw / (10 ** decimals)
            
            return balance
            
        except Exception as e:
            logger.error(f"Error getting token balance: {e}")
            return 0.0
    
    def get_native_balance(self, w3: Web3, wallet_address: str) -> float:
        """Get native token balance (ETH/MATIC/etc)"""
        try:
            balance_wei = w3.eth.get_balance(wallet_address)
            balance = balance_wei / 10**18
            return balance
        except Exception as e:
            logger.error(f"Error getting native balance: {e}")
            return 0.0
    
    def check_balances(self, chain_name: str, chain_config: Dict) -> Dict[str, float]:
        """Check all token balances for a chain"""
        balances = {}
        
        try:
            w3 = self.rpc_manager.get_rpc_for_chain(chain_name)
            wallet_address = self.get_wallet_address(chain_config)
            
            # Get native token balance
            native_balance = self.get_native_balance(w3, wallet_address)
            native_symbol = self.get_native_symbol(chain_name)
            balances[native_symbol] = native_balance
            
            # Get common reward token balances
            reward_tokens = self.get_common_reward_tokens(chain_name)
            for token_symbol, token_address in reward_tokens.items():
                if token_address:
                    balance = self.get_token_balance(w3, token_address, wallet_address)
                    if balance > 0:
                        balances[token_symbol] = balance
            
            # Store in history
            timestamp = int(time.time())
            if chain_name not in self.balance_history:
                self.balance_history[chain_name] = {}
            
            for token, balance in balances.items():
                if token not in self.balance_history[chain_name]:
                    self.balance_history[chain_name][token] = []
                self.balance_history[chain_name][token].append((timestamp, balance))
                
                # Keep only last 100 entries
                if len(self.balance_history[chain_name][token]) > 100:
                    self.balance_history[chain_name][token] = self.balance_history[chain_name][token][-100:]
            
            self.last_check[chain_name] = timestamp
            
        except Exception as e:
            logger.error(f"Error checking balances for {chain_name}: {e}")
        
        return balances
    
    def get_native_symbol(self, chain_name: str) -> str:
        """Get native token symbol for chain"""
        symbols = {
            'arbitrum': 'ETH',
            'base': 'ETH',
            'polygon': 'MATIC',
            'optimism': 'ETH',
            'bsc': 'BNB',
            'avalanche': 'AVAX'
        }
        return symbols.get(chain_name.lower(), 'ETH')
    
    def get_common_reward_tokens(self, chain_name: str) -> Dict[str, str]:
        """Get common reward token addresses for chain"""
        # These would be populated with actual token addresses
        tokens = {}
        
        if chain_name.lower() == 'arbitrum':
            tokens = {
                'WETH': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',
                'USDC': '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8',
                'USDT': '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9',
                'ARB': '0x912CE59144191C1204E64559FE8253a0e49E6548'
            }
        elif chain_name.lower() == 'base':
            tokens = {
                'WETH': '0x4200000000000000000000000000000000000006',
                'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
                'USDbC': '0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA'
            }
        
        return tokens
    
    def verify_harvest_reward(
        self,
        chain_name: str,
        tx_hash: str,
        before_balances: Dict[str, float],
        after_balances: Dict[str, float]
    ) -> Dict[str, Any]:
        """Verify that harvest rewards were received"""
        
        received = {}
        total_value_usd = 0.0
        
        # Compare balances
        for token in after_balances:
            before = before_balances.get(token, 0.0)
            after = after_balances.get(token, 0.0)
            difference = after - before
            
            if difference > 0.0001:  # Minimum threshold
                received[token] = difference
                logger.info(f"✅ Received {difference:.6f} {token} from harvest")
        
        return {
            'tx_hash': tx_hash,
            'chain': chain_name,
            'timestamp': int(time.time()),
            'rewards_received': received,
            'verified': len(received) > 0
        }
    
    def get_balance_summary(self, chain_name: str, chain_config: Dict) -> str:
        """Get formatted balance summary"""
        balances = self.check_balances(chain_name, chain_config)
        wallet_address = self.get_wallet_address(chain_config)
        
        lines = []
        lines.append(f"\n💼 Wallet Balance Summary for {chain_name}")
        lines.append(f"   Address: {wallet_address}")
        lines.append(f"   Balances:")
        
        for token, balance in balances.items():
            if balance > 0.0001:
                lines.append(f"     • {balance:.6f} {token}")
        
        # Check recent changes
        if chain_name in self.balance_history:
            lines.append(f"\n   Recent Changes (last hour):")
            for token, history in self.balance_history[chain_name].items():
                if len(history) >= 2:
                    # Get balance from 1 hour ago
                    one_hour_ago = int(time.time()) - 3600
                    old_balance = None
                    for ts, bal in history:
                        if ts <= one_hour_ago:
                            old_balance = bal
                        else:
                            break
                    
                    if old_balance is not None:
                        current = history[-1][1]
                        change = current - old_balance
                        if abs(change) > 0.0001:
                            sign = "+" if change > 0 else ""
                            lines.append(f"     • {token}: {sign}{change:.6f}")
        
        return "\n".join(lines)