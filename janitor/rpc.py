import json
import logging
from typing import Optional, List, Dict, Any
from web3 import Web3
from web3.providers import HTTPProvider
# WebsocketProvider is optional, handle different web3 versions
WebsocketProvider = None
try:
    from web3.providers import WebsocketProvider
except ImportError:
    try:
        from web3.providers.websocket import WebsocketProvider
    except ImportError:
        pass  # WebSocket support not available
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class RPCManager:
    """Manage Web3 connections with fallback support"""
    
    def __init__(self):
        self.connections: Dict[str, Web3] = {}
        self.current_rpc: Dict[str, int] = {}  # Track which RPC is active per chain
    
    def get_w3(self, chain_name: str, rpc_urls: List[str]) -> Web3:
        """Get Web3 instance with automatic fallback"""
        if chain_name in self.connections and self.connections[chain_name].is_connected():
            return self.connections[chain_name]
        
        # Try each RPC endpoint
        for i, url in enumerate(rpc_urls):
            try:
                if (url.startswith('ws://') or url.startswith('wss://')) and WebsocketProvider:
                    provider = WebsocketProvider(url, websocket_timeout=20)
                else:
                    provider = HTTPProvider(url, request_kwargs={'timeout': 20})
                
                w3 = Web3(provider)
                if w3.is_connected():
                    self.connections[chain_name] = w3
                    self.current_rpc[chain_name] = i
                    logger.info(f"Connected to {chain_name} via RPC #{i}")
                    return w3
            except Exception as e:
                logger.warning(f"Failed to connect to {chain_name} RPC #{i}: {e}")
                continue
        
        raise RuntimeError(f"No healthy RPC for {chain_name}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def call_with_retry(self, w3: Web3, contract_call):
        """Execute contract call with retry logic"""
        return contract_call.call()

def get_base_fee_gwei(w3: Web3) -> float:
    """Get current base fee in Gwei"""
    latest = w3.eth.get_block('latest')
    if 'baseFeePerGas' in latest:
        return latest['baseFeePerGas'] / 1e9
    # Fallback for non-EIP1559 chains
    return w3.eth.gas_price / 1e9

def get_priority_fee_gwei(w3: Web3) -> float:
    """Get suggested priority fee in Gwei"""
    try:
        # Try eth_maxPriorityFeePerGas first
        priority = w3.eth.max_priority_fee
        return priority / 1e9
    except:
        # Fallback to a reasonable default
        return 0.05  # 0.05 Gwei

def estimate_gas(w3: Web3, transaction: Dict[str, Any]) -> int:
    """Estimate gas with safety margin"""
    try:
        estimate = w3.eth.estimate_gas(transaction)
        # Add 20% buffer
        return int(estimate * 1.2)
    except Exception as e:
        logger.error(f"Gas estimation failed: {e}")
        # Return a reasonable default based on transaction type
        return 300000  # Conservative default

def load_contract(w3: Web3, address: str, abi_path: str):
    """Load contract instance"""
    with open(abi_path, 'r') as f:
        abi = json.load(f)
    
    # Ensure checksum address
    address = Web3.to_checksum_address(address)
    return w3.eth.contract(address=address, abi=abi)

def get_native_balance(w3: Web3, address: str) -> float:
    """Get native token balance in Ether"""
    balance_wei = w3.eth.get_balance(Web3.to_checksum_address(address))
    return balance_wei / 1e18