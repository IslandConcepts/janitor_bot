"""
Liquidation Module - Integrates flash loan liquidations with Janitor Bot
"""

import threading
import time
from typing import Dict, Optional
from web3 import Web3
from janitor.market_monitor import AaveMarketMonitor, MonitorConfig
from janitor.simple_storage import Storage
from janitor.logging_config import get_logger
from janitor.profit import calculate_profit_estimate

logger = get_logger("janitor.liquidation")

class LiquidationModule:
    """Liquidation module for Janitor Bot"""
    
    def __init__(self, config: Dict, w3_instances: Dict[str, Web3], storage: Storage):
        """
        Initialize liquidation module
        
        Args:
            config: Main janitor config
            w3_instances: Web3 instances by chain
            storage: Storage instance
        """
        self.config = config
        self.w3_instances = w3_instances
        self.storage = storage
        self.monitors = {}
        self.threads = {}
        self.enabled = config.get('liquidations', {}).get('enabled', False)
        
        if not self.enabled:
            logger.info("Liquidation module disabled in config")
            return
        
        # Initialize monitors for each chain
        self._setup_monitors()
        
        logger.info("Liquidation module initialized", enabled=self.enabled)
    
    def _setup_monitors(self):
        """Setup market monitors for configured chains"""
        liquidation_config = self.config.get('liquidations', {})
        
        for chain_name, chain_config in self.config.get('chains', {}).items():
            if not chain_config.get('enabled', False):
                continue
            
            # Skip if no RPC for this chain
            if chain_name not in self.w3_instances:
                logger.warning(f"No Web3 instance for {chain_name}, skipping liquidations")
                continue
            
            # Get chain-specific liquidation config
            chain_liquidation = liquidation_config.get(chain_name, {})
            
            if not chain_liquidation.get('enabled', True):
                logger.info(f"Liquidations disabled for {chain_name}")
                continue
            
            # Create monitor config
            monitor_config = MonitorConfig(
                chain=chain_name,
                check_interval_sec=chain_liquidation.get('check_interval', 60),
                min_profit_usd=chain_liquidation.get('min_profit_usd', 2.0),
                max_debt_usd=chain_liquidation.get('max_debt_usd', 1000.0),
                gas_multiplier=chain_liquidation.get('gas_multiplier', 2.0),
                allowed_tokens=chain_liquidation.get('allowed_tokens', []),
                max_positions_per_user=chain_liquidation.get('max_positions_per_user', 2),
                cooldown_after_liquidation=chain_liquidation.get('cooldown_sec', 300),
                max_daily_liquidations=chain_liquidation.get('max_daily', 10),
                simulation_only=chain_liquidation.get('simulation_only', True)
            )
            
            # Create monitor
            monitor = AaveMarketMonitor(
                config=monitor_config,
                w3=self.w3_instances[chain_name],
                storage=self.storage
            )
            
            self.monitors[chain_name] = monitor
            
            logger.info(
                f"Market monitor created for {chain_name}",
                simulation_only=monitor_config.simulation_only,
                max_debt_usd=monitor_config.max_debt_usd
            )
    
    def start(self):
        """Start liquidation monitoring on all chains"""
        if not self.enabled:
            return
        
        for chain_name, monitor in self.monitors.items():
            # Create thread for each chain's monitor
            thread = threading.Thread(
                target=self._run_monitor,
                args=(chain_name, monitor),
                daemon=True,
                name=f"liquidation_{chain_name}"
            )
            
            self.threads[chain_name] = thread
            thread.start()
            
            logger.info(f"Started liquidation monitor for {chain_name}")
        
        logger.info(f"All liquidation monitors started ({len(self.threads)} chains)")
    
    def _run_monitor(self, chain_name: str, monitor: AaveMarketMonitor):
        """Run monitor in thread"""
        logger.info(f"Liquidation monitor thread started for {chain_name}")
        
        try:
            # Run monitoring loop
            while True:
                try:
                    monitor.run_check_cycle()
                    time.sleep(monitor.config.check_interval_sec)
                    
                except Exception as e:
                    logger.error(f"Error in {chain_name} monitor: {e}")
                    time.sleep(60)  # Wait before retry
                    
        except KeyboardInterrupt:
            logger.info(f"Liquidation monitor for {chain_name} stopped")
    
    def get_stats(self) -> Dict:
        """Get statistics from all monitors"""
        stats = {}
        
        for chain_name, monitor in self.monitors.items():
            stats[chain_name] = {
                'checks': monitor.stats.checks_performed,
                'found': monitor.stats.liquidatable_found,
                'profitable': monitor.stats.profitable_opportunities,
                'executed': monitor.stats.liquidations_successful,
                'profit_usd': monitor.stats.total_profit_usd,
                'last_check': monitor.stats.last_check,
                'simulation_only': monitor.config.simulation_only
            }
        
        return stats
    
    def stop(self):
        """Stop all liquidation monitors"""
        logger.info("Stopping liquidation monitors...")
        
        # Threads are daemon threads, will stop with main program
        for chain_name in self.threads:
            logger.info(f"Stopped monitor for {chain_name}")

def integrate_liquidations(janitor_bot):
    """
    Integrate liquidation module with existing JanitorBot
    
    This function is called from janitor.py to add liquidation capabilities
    """
    try:
        # Create liquidation module
        liquidation_module = LiquidationModule(
            config=janitor_bot.config,
            w3_instances=janitor_bot.w3_instances,
            storage=janitor_bot.storage
        )
        
        # Start monitoring
        liquidation_module.start()
        
        # Attach to bot for stats/control
        janitor_bot.liquidation_module = liquidation_module
        
        logger.info("Liquidation module integrated with JanitorBot")
        
        return liquidation_module
        
    except Exception as e:
        logger.error(f"Failed to integrate liquidations: {e}")
        return None