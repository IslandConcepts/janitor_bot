import logging
from typing import Dict, Any, Optional
from web3 import Web3
from eth_account import Account
from eth_account.signers.local import LocalAccount
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class NonceManager:
    """Manage transaction nonces to avoid conflicts"""
    
    def __init__(self):
        self.nonces: Dict[str, int] = {}  # address -> last used nonce
        self.pending: Dict[str, bool] = {}  # address -> has pending tx
    
    def get_nonce(self, w3: Web3, address: str) -> int:
        """Get next available nonce for address"""
        address = Web3.to_checksum_address(address)
        
        # Always get the pending nonce from the chain to avoid conflicts
        # 'pending' includes both confirmed and pending transactions
        chain_nonce = w3.eth.get_transaction_count(address, 'pending')
        
        # Use max of chain nonce and our tracked nonce
        if address in self.nonces:
            nonce = max(chain_nonce, self.nonces[address] + 1)
        else:
            nonce = chain_nonce
        
        self.nonces[address] = nonce
        self.pending[address] = True
        return nonce
    
    def mark_confirmed(self, address: str):
        """Mark transaction as confirmed"""
        address = Web3.to_checksum_address(address)
        self.pending[address] = False
    
    def reset(self, address: str):
        """Reset nonce tracking for address"""
        address = Web3.to_checksum_address(address)
        if address in self.nonces:
            del self.nonces[address]
        if address in self.pending:
            del self.pending[address]
        logger.info(f"Reset nonce tracking for {address}")

class TransactionBuilder:
    """Build and send EIP-1559 transactions"""
    
    def __init__(self):
        self.nonce_manager = NonceManager()
    
    def build_transaction(
        self,
        w3: Web3,
        chain_config: Dict[str, Any],
        target: Dict[str, Any],
        call_data: bytes,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Build EIP-1559 transaction"""
        
        from_address = Web3.to_checksum_address(chain_config['from'])
        
        # Get gas parameters
        base_fee = w3.eth.get_block('latest')['baseFeePerGas']
        max_priority_fee = Web3.to_wei(0.05, 'gwei')  # Conservative tip
        max_fee = base_fee * 2 + max_priority_fee  # 2x base fee + tip
        
        # Cap max fee if configured
        max_fee_cap = Web3.to_wei(chain_config['maxBaseFeeGwei'] * 2, 'gwei')
        max_fee = min(max_fee, max_fee_cap)
        
        # Get gas limit
        if gas_limit is None:
            gas_limit = chain_config['gasLimitCaps'].get(target['type'], 500000)
        
        # Build transaction
        tx = {
            'from': from_address,
            'to': Web3.to_checksum_address(target['address']),
            'data': call_data,
            'gas': gas_limit,
            'maxFeePerGas': max_fee,
            'maxPriorityFeePerGas': max_priority_fee,
            'nonce': self.nonce_manager.get_nonce(w3, from_address),
            'chainId': chain_config['chainId']
        }
        
        return tx
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def send_transaction(
        self,
        w3: Web3,
        chain_config: Dict[str, Any],
        transaction: Dict[str, Any]
    ) -> str:
        """Sign and send transaction"""
        
        try:
            # Create account from private key
            account: LocalAccount = Account.from_key(chain_config['privateKey'])
            
            # Sign transaction
            signed_tx = account.sign_transaction(transaction)
            
            # Handle different web3.py versions (rawTransaction vs raw_transaction)
            raw_tx = getattr(signed_tx, 'rawTransaction', None) or getattr(signed_tx, 'raw_transaction', None)
            if not raw_tx:
                raise ValueError("Cannot find raw transaction attribute in SignedTransaction object")
            
            # Send transaction
            tx_hash = w3.eth.send_raw_transaction(raw_tx)
            
            logger.info(f"Transaction sent: {tx_hash.hex()}")
            
            return tx_hash.hex()
            
        except Exception as e:
            error_msg = str(e).lower()
            # If nonce error, reset nonce and retry on next attempt
            if 'nonce' in error_msg:
                from_address = transaction.get('from')
                if from_address:
                    logger.warning(f"Nonce error detected, resetting nonce for {from_address}")
                    self.nonce_manager.reset(from_address)
            raise
    
    def wait_for_receipt(
        self,
        w3: Web3,
        tx_hash: str,
        timeout: int = 60
    ) -> Optional[Dict[str, Any]]:
        """Wait for transaction receipt"""
        
        try:
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
            
            if receipt['status'] == 1:
                logger.info(f"Transaction confirmed: {tx_hash}")
            else:
                logger.error(f"Transaction failed: {tx_hash}")
            
            # Mark nonce as confirmed
            self.nonce_manager.mark_confirmed(receipt['from'])
            
            return receipt
        
        except Exception as e:
            logger.error(f"Error waiting for receipt: {e}")
            return None

def execute_janitor_transaction(
    w3: Web3,
    chain_config: Dict[str, Any],
    target: Dict[str, Any],
    tx_builder: TransactionBuilder
) -> Dict[str, Any]:
    """Execute a janitor transaction and return results"""
    
    result = {
        'tx_hash': None,
        'gas_used': 0,
        'gas_cost_usd': 0.0,
        'status': 'failed',
        'error': None
    }
    
    try:
        # Load contract
        from janitor.rpc import load_contract
        contract = load_contract(w3, target['address'], f"janitor/{target['abi']}")
        
        # Build call data
        exec_func = target['write']['exec']
        params = target.get('params', [])
        call = contract.functions[exec_func](*params)
        
        # Get from address
        from_address = chain_config.get('from') or chain_config.get('fromAddress')
        if not from_address:
            raise ValueError(f"No 'from' address in chain config")
        
        # Estimate gas
        gas_estimate = call.estimate_gas({'from': from_address})
        gas_limit = int(gas_estimate * 1.2)  # Add 20% buffer
        
        # Build transaction
        tx = tx_builder.build_transaction(
            w3=w3,
            chain_config=chain_config,
            target=target,
            call_data=call._encode_transaction_data(),
            gas_limit=gas_limit
        )
        
        # Send transaction
        tx_hash = tx_builder.send_transaction(w3, chain_config, tx)
        result['tx_hash'] = tx_hash
        
        # Wait for receipt
        receipt = tx_builder.wait_for_receipt(w3, tx_hash)
        
        if receipt:
            result['gas_used'] = receipt['gasUsed']
            result['gas_cost_usd'] = calculate_gas_cost_usd(
                receipt['gasUsed'],
                receipt['effectiveGasPrice'],
                chain_config.get('nativeUsd', 2500.0)
            )
            result['status'] = 'success' if receipt['status'] == 1 else 'failed'
        
    except Exception as e:
        import traceback
        logger.error(f"Transaction execution error: {e}", exc_info=True)
        print(f"  ❌ TX Error: {e}")
        print(f"  📋 Target: {target.get('name')}")
        print(f"  📋 Params: {target.get('params')}")
        traceback.print_exc()
        result['error'] = str(e)
    
    return result

def calculate_gas_cost_usd(gas_used: int, gas_price: int, native_usd: float) -> float:
    """Calculate actual gas cost in USD"""
    gas_cost_eth = (gas_used * gas_price) / 1e18
    return gas_cost_eth * native_usd