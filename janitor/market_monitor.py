"""
USDC/WETH Market Monitor for Aave V3
Monitors lending markets for liquidation opportunities
"""

import time
import json
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from web3 import Web3
from janitor.flash_loan_adapter import AaveV3Adapter, LiquidationTarget
from janitor.logging_config import get_logger
from janitor.simple_storage import Storage

logger = get_logger("janitor.monitor")

@dataclass
class MonitorConfig:
    """Configuration for market monitoring"""
    chain: str
    check_interval_sec: int = 60  # How often to check for liquidations
    min_profit_usd: float = 2.0  # Minimum profit to attempt
    max_debt_usd: float = 1000.0  # Maximum debt to liquidate (starter cap)
    gas_multiplier: float = 2.0  # Require profit >= gas * multiplier
    allowed_tokens: List[str] = field(default_factory=list)
    max_positions_per_user: int = 2  # Check top N positions per user
    cooldown_after_liquidation: int = 300  # 5 min cooldown after success
    max_daily_liquidations: int = 10  # Daily cap for safety
    simulation_only: bool = True  # Start in simulation mode

@dataclass 
class MarketStats:
    """Statistics for monitoring performance"""
    checks_performed: int = 0
    liquidatable_found: int = 0
    simulations_run: int = 0
    profitable_opportunities: int = 0
    liquidations_attempted: int = 0
    liquidations_successful: int = 0
    total_profit_usd: float = 0.0
    last_check: Optional[datetime] = None
    last_liquidation: Optional[datetime] = None

class AaveMarketMonitor:
    """Monitors Aave V3 markets for liquidation opportunities"""
    
    def __init__(self, config: MonitorConfig, w3: Web3, storage: Storage):
        """
        Initialize market monitor
        
        Args:
            config: Monitor configuration
            w3: Web3 instance
            storage: Storage for persistence
        """
        self.config = config
        self.w3 = w3
        self.storage = storage
        
        # Initialize flash loan adapter
        self.adapter = AaveV3Adapter(
            chain=config.chain,
            w3=w3,
            executor_address=w3.eth.default_account
        )
        
        # Track processed liquidations (avoid duplicates)
        self.processed_liquidations: Set[str] = set()
        self.last_liquidation_time: Optional[datetime] = None
        self.daily_liquidation_count = 0
        self.daily_reset_time = datetime.now()
        
        # Load or initialize stats
        self.stats = self._load_stats()
        
        # Token configuration
        self._setup_tokens()
        
        logger.info(
            "Market monitor initialized",
            chain=config.chain,
            simulation_mode=config.simulation_only,
            max_debt_usd=config.max_debt_usd
        )
    
    def _setup_tokens(self):
        """Setup token addresses for monitoring"""
        if self.config.allowed_tokens:
            self.tokens = self.config.allowed_tokens
        else:
            # Default to USDC/WETH
            if self.config.chain == 'arbitrum':
                self.tokens = [
                    self.adapter.tokens['USDC'],
                    self.adapter.tokens['USDC.e'],
                    self.adapter.tokens['WETH'],
                    self.adapter.tokens['WBTC']
                ]
            else:  # base
                self.tokens = [
                    self.adapter.tokens['USDC'],
                    self.adapter.tokens['USDbC'],
                    self.adapter.tokens['WETH'],
                    self.adapter.tokens['cbETH']
                ]
    
    def _load_stats(self) -> MarketStats:
        """Load statistics from storage"""
        try:
            stats_data = self.storage.load(f"monitor_stats_{self.config.chain}")
            if stats_data:
                return MarketStats(**stats_data)
        except Exception as e:
            logger.warning(f"Could not load stats: {e}")
        
        return MarketStats()
    
    def _save_stats(self):
        """Save statistics to storage"""
        try:
            stats_dict = {
                'checks_performed': self.stats.checks_performed,
                'liquidatable_found': self.stats.liquidatable_found,
                'simulations_run': self.stats.simulations_run,
                'profitable_opportunities': self.stats.profitable_opportunities,
                'liquidations_attempted': self.stats.liquidations_attempted,
                'liquidations_successful': self.stats.liquidations_successful,
                'total_profit_usd': self.stats.total_profit_usd,
                'last_check': self.stats.last_check.isoformat() if self.stats.last_check else None,
                'last_liquidation': self.stats.last_liquidation.isoformat() if self.stats.last_liquidation else None
            }
            self.storage.save(f"monitor_stats_{self.config.chain}", stats_dict)
        except Exception as e:
            logger.error(f"Could not save stats: {e}")
    
    def _reset_daily_limits(self):
        """Reset daily liquidation counter"""
        now = datetime.now()
        if now.date() > self.daily_reset_time.date():
            self.daily_liquidation_count = 0
            self.daily_reset_time = now
            logger.info("Daily limits reset")
    
    def _is_in_cooldown(self) -> bool:
        """Check if we're in cooldown period"""
        if not self.last_liquidation_time:
            return False
        
        elapsed = (datetime.now() - self.last_liquidation_time).seconds
        return elapsed < self.config.cooldown_after_liquidation
    
    def find_liquidation_opportunities(self) -> List[LiquidationTarget]:
        """
        Find accounts that can be liquidated
        
        Returns:
            List of liquidation targets
        """
        opportunities = []
        
        # Get recent borrowers from events (would need event monitoring)
        # For now, we'll use a provided list or scan known addresses
        # In production, you'd monitor Borrow/Repay events
        
        # Example: Check a known risky position (you'd get this from events)
        # This is where you'd integrate with a subgraph or event monitor
        test_users = self._get_risky_users()
        
        for user in test_users:
            # Check account health
            health = self.adapter.get_account_health(user)
            
            if not health or not health['is_liquidatable']:
                continue
            
            self.stats.liquidatable_found += 1
            logger.info(
                f"Found liquidatable account",
                user=user,
                health_factor=health['health_factor'],
                debt_usd=health['total_debt_usd']
            )
            
            # Check each token pair
            for debt_token in self.tokens:
                for collateral_token in self.tokens:
                    if debt_token == collateral_token:
                        continue
                    
                    # Calculate opportunity
                    target = self.adapter.calculate_liquidation_opportunity(
                        user=user,
                        debt_asset=debt_token,
                        collateral_asset=collateral_token,
                        gas_price_gwei=0.1 if self.config.chain == 'arbitrum' else 0.05
                    )
                    
                    if target:
                        # Apply our filters
                        debt_token_contract = self.w3.eth.contract(
                            address=debt_token,
                            abi=self.adapter.erc20_abi
                        )
                        decimals = debt_token_contract.functions.decimals().call()
                        debt_usd = (target.debt_to_cover / (10 ** decimals)) * self._get_token_price(debt_token)
                        
                        if debt_usd > self.config.max_debt_usd:
                            logger.debug(f"Debt too large: ${debt_usd:.2f} > ${self.config.max_debt_usd}")
                            continue
                        
                        if target.expected_profit_usd < self.config.min_profit_usd:
                            logger.debug(f"Profit too small: ${target.expected_profit_usd:.2f}")
                            continue
                        
                        # Check if already processed
                        key = f"{user}_{debt_token}_{collateral_token}"
                        if key not in self.processed_liquidations:
                            opportunities.append(target)
                            logger.info(
                                f"Profitable liquidation found",
                                user=user[:10] + "...",
                                profit_usd=target.expected_profit_usd,
                                debt_usd=debt_usd
                            )
        
        return opportunities
    
    def _get_risky_users(self) -> List[str]:
        """
        Get users with risky positions
        In production, this would come from:
        1. Event monitoring (Borrow, Withdraw events)
        2. Subgraph queries
        3. Known whale addresses
        """
        # For testing, return empty or known test addresses
        # You would populate this from event monitoring
        return []
    
    def _get_token_price(self, token: str) -> float:
        """Get token price in USD"""
        try:
            price = self.adapter.oracle.functions.getAssetPrice(token).call()
            return price / 1e8
        except:
            return 0.0
    
    def simulate_liquidation(self, target: LiquidationTarget) -> Optional[Dict]:
        """
        Simulate a liquidation to verify profitability
        
        Returns:
            Simulation results if profitable, None otherwise
        """
        self.stats.simulations_run += 1
        
        try:
            # Run simulation
            sim = self.adapter.simulate_flash_loan_liquidation(target)
            
            if sim['profitable']:
                self.stats.profitable_opportunities += 1
                
                logger.info(
                    "Simulation successful",
                    borrower=target.borrower[:10] + "...",
                    net_profit_usd=sim['net_profit_usd'],
                    health_factor=sim['health_factor'],
                    liquidation_bonus=sim['liquidation_bonus']
                )
                
                # Log details
                print(f"\n{'='*60}")
                print(f"LIQUIDATION SIMULATION RESULTS")
                print(f"{'='*60}")
                print(f"Borrower: {target.borrower}")
                print(f"Health Factor: {sim['health_factor']:.4f}")
                print(f"Debt Amount: ${sim['debt_usd']:.2f}")
                print(f"Collateral Value: ${sim['collateral_usd']:.2f}")
                print(f"Liquidation Bonus: {(sim['liquidation_bonus']-1)*100:.1f}%")
                print(f"Flash Fee: ${sim['flash_fee'] / 1e6:.2f}")  # Assuming USDC
                print(f"Gas Cost: ${sim['gas_cost_usd']:.2f}")
                print(f"Swap Cost: ${sim['swap_cost_usd']:.2f}")
                print(f"Gross Profit: ${sim['gross_profit_usd']:.2f}")
                print(f"Net Profit: ${sim['net_profit_usd']:.2f}")
                print(f"{'='*60}\n")
                
                return sim
            else:
                logger.debug("Simulation not profitable", borrower=target.borrower[:10] + "...")
                
        except Exception as e:
            logger.error(f"Simulation failed: {e}", borrower=target.borrower)
        
        return None
    
    def execute_liquidation(self, target: LiquidationTarget, simulation: Dict) -> bool:
        """
        Execute a flash loan liquidation
        
        Note: This requires a deployed flash loan receiver contract
        For now, this logs what would be executed
        """
        if self.config.simulation_only:
            logger.info(
                "SIMULATION MODE: Would execute liquidation",
                borrower=target.borrower,
                expected_profit=simulation['net_profit_usd']
            )
            return True
        
        # Check daily limit
        if self.daily_liquidation_count >= self.config.max_daily_liquidations:
            logger.warning("Daily liquidation limit reached")
            return False
        
        try:
            self.stats.liquidations_attempted += 1
            
            # Build transaction (requires flash loan receiver contract)
            tx_params = self.adapter.build_flash_loan_tx(target)
            
            if not tx_params:
                logger.error("Failed to build transaction")
                return False
            
            # Log what would be sent
            logger.info(
                "Ready to execute liquidation",
                borrower=target.borrower,
                debt_token=target.debt_token,
                collateral_token=target.collateral_token,
                debt_amount=target.debt_to_cover
            )
            
            # Mark as processed
            key = f"{target.borrower}_{target.debt_token}_{target.collateral_token}"
            self.processed_liquidations.add(key)
            
            # Update stats
            self.stats.liquidations_successful += 1
            self.stats.total_profit_usd += simulation['net_profit_usd']
            self.stats.last_liquidation = datetime.now()
            self.last_liquidation_time = datetime.now()
            self.daily_liquidation_count += 1
            
            # Save stats
            self._save_stats()
            
            return True
            
        except Exception as e:
            logger.error(f"Liquidation execution failed: {e}")
            return False
    
    def run_check_cycle(self):
        """Run a single check cycle"""
        self.stats.checks_performed += 1
        self.stats.last_check = datetime.now()
        
        # Reset daily limits if needed
        self._reset_daily_limits()
        
        # Check cooldown
        if self._is_in_cooldown():
            logger.debug("In cooldown period, skipping check")
            return
        
        logger.debug(f"Running liquidation check cycle #{self.stats.checks_performed}")
        
        # Find opportunities
        opportunities = self.find_liquidation_opportunities()
        
        if not opportunities:
            logger.debug("No liquidation opportunities found")
            return
        
        logger.info(f"Found {len(opportunities)} potential liquidations")
        
        # Process each opportunity
        for target in opportunities:
            # Simulate first
            simulation = self.simulate_liquidation(target)
            
            if simulation and simulation['profitable']:
                # Execute if profitable
                success = self.execute_liquidation(target, simulation)
                
                if success:
                    logger.info(
                        "Liquidation processed",
                        profit_usd=simulation['net_profit_usd'],
                        total_profit=self.stats.total_profit_usd
                    )
                    break  # Process one at a time for safety
    
    def get_stats_summary(self) -> str:
        """Get formatted statistics summary"""
        return f"""
{'='*60}
MARKET MONITOR STATISTICS - {self.config.chain.upper()}
{'='*60}
Checks Performed: {self.stats.checks_performed}
Liquidatable Found: {self.stats.liquidatable_found}
Simulations Run: {self.stats.simulations_run}
Profitable Opportunities: {self.stats.profitable_opportunities}
Liquidations Attempted: {self.stats.liquidations_attempted}
Liquidations Successful: {self.stats.liquidations_successful}
Total Profit: ${self.stats.total_profit_usd:.2f}
Last Check: {self.stats.last_check or 'Never'}
Last Liquidation: {self.stats.last_liquidation or 'Never'}
Simulation Mode: {self.config.simulation_only}
{'='*60}
"""
    
    def start_monitoring(self):
        """Start continuous monitoring loop"""
        logger.info(
            "Starting market monitoring",
            chain=self.config.chain,
            interval=self.config.check_interval_sec,
            simulation_only=self.config.simulation_only
        )
        
        print(self.get_stats_summary())
        
        while True:
            try:
                self.run_check_cycle()
                
                # Print stats every 10 checks
                if self.stats.checks_performed % 10 == 0:
                    print(self.get_stats_summary())
                
                time.sleep(self.config.check_interval_sec)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.config.check_interval_sec)