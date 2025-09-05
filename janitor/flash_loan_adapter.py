"""
Aave V3 Flash Loan Adapter for Janitor Bot
Provides capital-efficient liquidations without tying up principal
"""

import json
from typing import Dict, List, Optional, Tuple
from web3 import Web3
from web3.types import TxParams
from dataclasses import dataclass
from decimal import Decimal
from janitor.logging_config import get_logger

logger = get_logger("janitor.flashloan")

@dataclass
class FlashLoanParams:
    """Parameters for a flash loan operation"""
    asset: str  # Token address to borrow
    amount: int  # Amount to borrow (in wei/smallest unit)
    premium: int  # Flash loan fee (9 = 0.09%)
    initiator: str  # Contract initiating the loan
    params: bytes  # Encoded parameters for the operation

@dataclass
class LiquidationTarget:
    """Target account for liquidation"""
    borrower: str  # Address of the account to liquidate
    debt_token: str  # Token that borrower owes
    collateral_token: str  # Token to seize as collateral
    debt_to_cover: int  # Amount of debt to repay
    health_factor: float  # Current health factor
    max_liquidatable: int  # Max amount that can be liquidated
    expected_profit_usd: float  # Expected profit in USD

class AaveV3Adapter:
    """Aave V3 Flash Loan Adapter"""
    
    # Aave V3 addresses
    ADDRESSES = {
        'arbitrum': {
            'pool': '0x794a61358D6845594F94dc1DB02A252b5b4814aD',
            'oracle': '0xb56c2F0B653B2e0b10C9b928C8580Ac5Df02C7C7',
            'pool_data_provider': '0x69FA688f1Dc47d4B5d8029D5a35FB7a548310654',
        },
        'base': {
            'pool': '0xA238Dd80C259a72e81d7e4664a9801593F98d1c5',
            'oracle': '0x2Cc0Fc26eD4563A5ce5e8bdcfe1A2878676Ae156',
            'pool_data_provider': '0x2d8A3C5677189723C4cB8873CfC9C8976FDF38Ac',
        }
    }
    
    # Common token addresses
    TOKENS = {
        'arbitrum': {
            'USDC': '0xaf88d065e77c8cC2239327C5EDb3A432268e5831',
            'USDC.e': '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8',
            'WETH': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',
            'WBTC': '0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f',
        },
        'base': {
            'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
            'USDbC': '0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA',
            'WETH': '0x4200000000000000000000000000000000000006',
            'cbETH': '0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22',
        }
    }
    
    def __init__(self, chain: str, w3: Web3, executor_address: str):
        """
        Initialize Aave V3 adapter
        
        Args:
            chain: 'arbitrum' or 'base'
            w3: Web3 instance
            executor_address: Address that will execute flash loans
        """
        self.chain = chain
        self.w3 = w3
        self.executor = executor_address
        
        if chain not in self.ADDRESSES:
            raise ValueError(f"Unsupported chain: {chain}")
        
        self.addresses = self.ADDRESSES[chain]
        self.tokens = self.TOKENS[chain]
        
        # Load ABIs
        self._load_abis()
        
        # Initialize contracts
        self.pool = self.w3.eth.contract(
            address=self.addresses['pool'],
            abi=self.pool_abi
        )
        self.oracle = self.w3.eth.contract(
            address=self.addresses['oracle'],
            abi=self.oracle_abi
        )
        self.data_provider = self.w3.eth.contract(
            address=self.addresses['pool_data_provider'],
            abi=self.data_provider_abi
        )
        
        logger.info(f"Aave V3 adapter initialized for {chain}", chain=chain)
    
    def _load_abis(self):
        """Load necessary ABIs"""
        # Minimal ABIs for the functions we need
        self.pool_abi = [
            {
                "name": "flashLoan",
                "type": "function",
                "stateMutability": "nonpayable",
                "inputs": [
                    {"name": "receiverAddress", "type": "address"},
                    {"name": "assets", "type": "address[]"},
                    {"name": "amounts", "type": "uint256[]"},
                    {"name": "interestRateModes", "type": "uint256[]"},
                    {"name": "onBehalfOf", "type": "address"},
                    {"name": "params", "type": "bytes"},
                    {"name": "referralCode", "type": "uint16"}
                ],
                "outputs": []
            },
            {
                "name": "liquidationCall",
                "type": "function",
                "stateMutability": "nonpayable",
                "inputs": [
                    {"name": "collateralAsset", "type": "address"},
                    {"name": "debtAsset", "type": "address"},
                    {"name": "user", "type": "address"},
                    {"name": "debtToCover", "type": "uint256"},
                    {"name": "receiveAToken", "type": "bool"}
                ],
                "outputs": []
            },
            {
                "name": "getUserAccountData",
                "type": "function",
                "stateMutability": "view",
                "inputs": [{"name": "user", "type": "address"}],
                "outputs": [
                    {"name": "totalCollateralBase", "type": "uint256"},
                    {"name": "totalDebtBase", "type": "uint256"},
                    {"name": "availableBorrowsBase", "type": "uint256"},
                    {"name": "currentLiquidationThreshold", "type": "uint256"},
                    {"name": "ltv", "type": "uint256"},
                    {"name": "healthFactor", "type": "uint256"}
                ]
            },
            {
                "name": "FLASHLOAN_PREMIUM_TOTAL",
                "type": "function",
                "stateMutability": "view",
                "inputs": [],
                "outputs": [{"name": "", "type": "uint128"}]
            }
        ]
        
        self.oracle_abi = [
            {
                "name": "getAssetPrice",
                "type": "function",
                "stateMutability": "view",
                "inputs": [{"name": "asset", "type": "address"}],
                "outputs": [{"name": "", "type": "uint256"}]
            },
            {
                "name": "getAssetsPrices",
                "type": "function",
                "stateMutability": "view",
                "inputs": [{"name": "assets", "type": "address[]"}],
                "outputs": [{"name": "", "type": "uint256[]"}]
            }
        ]
        
        self.data_provider_abi = [
            {
                "name": "getUserReserveData",
                "type": "function",
                "stateMutability": "view",
                "inputs": [
                    {"name": "asset", "type": "address"},
                    {"name": "user", "type": "address"}
                ],
                "outputs": [
                    {"name": "currentATokenBalance", "type": "uint256"},
                    {"name": "currentStableDebt", "type": "uint256"},
                    {"name": "currentVariableDebt", "type": "uint256"},
                    {"name": "principalStableDebt", "type": "uint256"},
                    {"name": "scaledVariableDebt", "type": "uint256"},
                    {"name": "stableBorrowRate", "type": "uint256"},
                    {"name": "liquidityRate", "type": "uint256"},
                    {"name": "stableRateLastUpdated", "type": "uint40"},
                    {"name": "usageAsCollateralEnabled", "type": "bool"}
                ]
            },
            {
                "name": "getReserveConfigurationData",
                "type": "function",
                "stateMutability": "view",
                "inputs": [{"name": "asset", "type": "address"}],
                "outputs": [
                    {"name": "decimals", "type": "uint256"},
                    {"name": "ltv", "type": "uint256"},
                    {"name": "liquidationThreshold", "type": "uint256"},
                    {"name": "liquidationBonus", "type": "uint256"},
                    {"name": "reserveFactor", "type": "uint256"},
                    {"name": "usageAsCollateralEnabled", "type": "bool"},
                    {"name": "borrowingEnabled", "type": "bool"},
                    {"name": "stableBorrowRateEnabled", "type": "bool"},
                    {"name": "isActive", "type": "bool"},
                    {"name": "isFrozen", "type": "bool"}
                ]
            }
        ]
        
        # ERC20 ABI for token operations
        self.erc20_abi = [
            {
                "name": "approve",
                "type": "function",
                "stateMutability": "nonpayable",
                "inputs": [
                    {"name": "spender", "type": "address"},
                    {"name": "amount", "type": "uint256"}
                ],
                "outputs": [{"name": "", "type": "bool"}]
            },
            {
                "name": "balanceOf",
                "type": "function",
                "stateMutability": "view",
                "inputs": [{"name": "account", "type": "address"}],
                "outputs": [{"name": "", "type": "uint256"}]
            },
            {
                "name": "decimals",
                "type": "function",
                "stateMutability": "view",
                "inputs": [],
                "outputs": [{"name": "", "type": "uint8"}]
            }
        ]
    
    def get_account_health(self, user: str) -> Dict:
        """
        Get account health data
        
        Returns:
            Dict with health factor and other account data
        """
        try:
            data = self.pool.functions.getUserAccountData(user).call()
            
            health_factor = data[5] / 1e18 if data[5] > 0 else 0
            
            return {
                'total_collateral_usd': data[0] / 1e8,  # Base currency has 8 decimals
                'total_debt_usd': data[1] / 1e8,
                'available_borrows_usd': data[2] / 1e8,
                'liquidation_threshold': data[3] / 10000,  # In percentage
                'ltv': data[4] / 10000,
                'health_factor': health_factor,
                'is_liquidatable': health_factor < 1.0 and health_factor > 0
            }
        except Exception as e:
            logger.error(f"Failed to get account health: {e}", user=user)
            return None
    
    def get_user_position(self, user: str, asset: str) -> Dict:
        """Get user's position for a specific asset"""
        try:
            data = self.data_provider.functions.getUserReserveData(asset, user).call()
            
            return {
                'collateral_balance': data[0],
                'stable_debt': data[1],
                'variable_debt': data[2],
                'total_debt': data[1] + data[2],
                'is_collateral': data[8]
            }
        except Exception as e:
            logger.error(f"Failed to get user position: {e}", user=user, asset=asset)
            return None
    
    def get_liquidation_bonus(self, collateral_asset: str) -> float:
        """Get liquidation bonus for an asset (e.g., 1.05 = 5% bonus)"""
        try:
            config = self.data_provider.functions.getReserveConfigurationData(collateral_asset).call()
            # liquidationBonus is at index 3, in basis points (10000 = 100%)
            return config[3] / 10000
        except Exception as e:
            logger.error(f"Failed to get liquidation bonus: {e}", asset=collateral_asset)
            return 1.0  # Default to no bonus if error
    
    def calculate_liquidation_opportunity(
        self,
        user: str,
        debt_asset: str,
        collateral_asset: str,
        gas_price_gwei: float = 0.1
    ) -> Optional[LiquidationTarget]:
        """
        Calculate if a liquidation opportunity exists
        
        Returns:
            LiquidationTarget if profitable, None otherwise
        """
        # Get account health
        health = self.get_account_health(user)
        if not health or not health['is_liquidatable']:
            return None
        
        # Get positions
        debt_position = self.get_user_position(user, debt_asset)
        collateral_position = self.get_user_position(user, collateral_asset)
        
        if not debt_position or not collateral_position:
            return None
        
        total_debt = debt_position['total_debt']
        if total_debt == 0:
            return None
        
        # Get prices
        prices = self.oracle.functions.getAssetsPrices([debt_asset, collateral_asset]).call()
        debt_price_usd = prices[0] / 1e8
        collateral_price_usd = prices[1] / 1e8
        
        # Get token decimals
        debt_token = self.w3.eth.contract(address=debt_asset, abi=self.erc20_abi)
        collateral_token = self.w3.eth.contract(address=collateral_asset, abi=self.erc20_abi)
        debt_decimals = debt_token.functions.decimals().call()
        collateral_decimals = collateral_token.functions.decimals().call()
        
        # Calculate max liquidatable (typically 50% of debt)
        close_factor = 0.5  # Aave V3 typically allows 50% liquidation
        max_liquidatable = int(total_debt * close_factor)
        
        # Calculate expected collateral to receive
        liquidation_bonus = self.get_liquidation_bonus(collateral_asset)
        
        # Convert to USD values
        debt_to_cover_usd = (max_liquidatable / (10 ** debt_decimals)) * debt_price_usd
        collateral_to_receive_usd = debt_to_cover_usd * liquidation_bonus
        
        # Calculate profit
        gross_profit_usd = collateral_to_receive_usd - debt_to_cover_usd
        
        # Estimate costs
        gas_cost_usd = 500000 * gas_price_gwei * 1e-9 * 2500  # Assume ETH = $2500
        flash_fee_usd = debt_to_cover_usd * 0.0009  # Aave charges 0.09%
        swap_fees_usd = debt_to_cover_usd * 0.003  # Assume 0.3% swap fees
        
        net_profit_usd = gross_profit_usd - gas_cost_usd - flash_fee_usd - swap_fees_usd
        
        # Only return if profitable
        if net_profit_usd > 1.0 and gross_profit_usd > gas_cost_usd * 2:
            return LiquidationTarget(
                borrower=user,
                debt_token=debt_asset,
                collateral_token=collateral_asset,
                debt_to_cover=max_liquidatable,
                health_factor=health['health_factor'],
                max_liquidatable=max_liquidatable,
                expected_profit_usd=net_profit_usd
            )
        
        return None
    
    def simulate_flash_loan_liquidation(
        self,
        target: LiquidationTarget,
        slippage: float = 0.005
    ) -> Dict:
        """
        Simulate a flash loan liquidation
        
        Returns:
            Simulation results with expected profit and required parameters
        """
        try:
            # Get current prices
            prices = self.oracle.functions.getAssetsPrices([
                target.debt_token,
                target.collateral_token
            ]).call()
            
            debt_price = prices[0] / 1e8
            collateral_price = prices[1] / 1e8
            
            # Get decimals
            debt_token = self.w3.eth.contract(address=target.debt_token, abi=self.erc20_abi)
            collateral_token = self.w3.eth.contract(address=target.collateral_token, abi=self.erc20_abi)
            debt_decimals = debt_token.functions.decimals().call()
            collateral_decimals = collateral_token.functions.decimals().call()
            
            # Calculate amounts
            debt_amount = target.debt_to_cover
            debt_usd = (debt_amount / (10 ** debt_decimals)) * debt_price
            
            # Get liquidation bonus
            liquidation_bonus = self.get_liquidation_bonus(target.collateral_token)
            collateral_usd = debt_usd * liquidation_bonus
            collateral_amount = int((collateral_usd / collateral_price) * (10 ** collateral_decimals))
            
            # Calculate costs
            flash_fee = int(debt_amount * 0.0009)  # 0.09% fee
            gas_estimate = 500000
            gas_cost_usd = gas_estimate * 0.1 * 1e-9 * 2500
            
            # Apply slippage to swap
            swap_output = int(debt_amount * (1 - slippage))
            swap_cost_usd = debt_usd * slippage
            
            # Final profit calculation
            gross_profit_usd = collateral_usd - debt_usd
            total_costs_usd = gas_cost_usd + (flash_fee / (10 ** debt_decimals) * debt_price) + swap_cost_usd
            net_profit_usd = gross_profit_usd - total_costs_usd
            
            return {
                'profitable': net_profit_usd > 1.0,
                'debt_amount': debt_amount,
                'debt_usd': debt_usd,
                'collateral_amount': collateral_amount,
                'collateral_usd': collateral_usd,
                'flash_fee': flash_fee,
                'gas_estimate': gas_estimate,
                'gas_cost_usd': gas_cost_usd,
                'swap_cost_usd': swap_cost_usd,
                'gross_profit_usd': gross_profit_usd,
                'net_profit_usd': net_profit_usd,
                'liquidation_bonus': liquidation_bonus,
                'health_factor': target.health_factor
            }
            
        except Exception as e:
            logger.error(f"Simulation failed: {e}", target=target.borrower)
            return {'profitable': False, 'error': str(e)}
    
    def build_flash_loan_tx(
        self,
        target: LiquidationTarget,
        gas_price: Optional[int] = None,
        max_priority_fee: Optional[int] = None
    ) -> Optional[TxParams]:
        """
        Build flash loan transaction (not executed, for review)
        
        Note: This requires a smart contract to receive and execute the flash loan
        For now, this returns the parameters needed
        """
        try:
            # For a real implementation, you need a smart contract that:
            # 1. Implements IFlashLoanReceiver interface
            # 2. Receives the flash loan
            # 3. Executes the liquidation
            # 4. Swaps collateral back to debt token
            # 5. Repays the flash loan + fee
            
            params = {
                'receiver': self.executor,  # Your flash loan receiver contract
                'assets': [target.debt_token],
                'amounts': [target.debt_to_cover],
                'modes': [0],  # 0 = no debt, just flash loan
                'onBehalfOf': self.executor,
                'params': self.w3.codec.encode(
                    ['address', 'address', 'address', 'uint256'],
                    [target.borrower, target.debt_token, target.collateral_token, target.debt_to_cover]
                ),
                'referralCode': 0
            }
            
            logger.info(
                "Flash loan params prepared",
                borrower=target.borrower,
                debt_amount=target.debt_to_cover,
                expected_profit=target.expected_profit_usd
            )
            
            return params
            
        except Exception as e:
            logger.error(f"Failed to build flash loan tx: {e}")
            return None