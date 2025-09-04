#!/usr/bin/env python3

import time
import signal
import sys
from typing import Dict, Any

from janitor.config import load_config, validate_target
from janitor.rpc import RPCManager, get_base_fee_gwei, load_contract
from janitor.profit import estimate_profit_usd, passes_profit_gate, get_min_pending_threshold
from janitor.tx import TransactionBuilder, execute_janitor_transaction
from janitor.storage import Database
from janitor.utils import calculate_time_until
from janitor.logging_config import get_logger, setup_logging

logger = get_logger(__name__)

class JanitorBot:
    """Main janitor bot orchestrator"
    
    def __init__(self, config_path: str = "janitor/targets.json"):
        self.config = load_config(config_path)
        self.global_config = self.config['global']
        
        # Setup comprehensive logging
        setup_logging(self.global_config)
        
        # Initialize components
        self.rpc_manager = RPCManager()
        self.tx_builder = TransactionBuilder()
        self.db = Database("data/janitor.db")
        
        # Control flags
        self.running = True
        self.paused = False
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.shutdown_handler)
        signal.signal(signal.SIGTERM, self.shutdown_handler)
        
        logger.info(f"Janitor bot initialized in {self.global_config['env']} mode", 
                   env=self.global_config['env'],
                   profit_multiplier=self.global_config['profitMultiplier'],
                   min_net_usd=self.global_config['minNetUSD'])
    
    def shutdown_handler(self, signum, frame):
        """Handle graceful shutdown"""
        logger.info("Shutdown signal received", signal=signum)
        self.running = False
    
    def read_target_state(self, w3, target: Dict[str, Any]) -> Dict[str, Any]:
        """Read on-chain state for target"""
        start_time = time.time()
        try:
            logger.debug(f"Reading on-chain state for {target['name']}", target=target['name'])
            contract = load_contract(w3, target['address'], f"janitor/{target['abi']}")
            state = {}
            
            if target['type'] == 'harvest':
                # Read pending rewards
                func_name = target['read']['pendingRewards']
                state['pending'] = contract.functions[func_name]().call()
                
            elif target['type'] == 'twap':
                # Read last update time
                func_name = target['read']['lastUpdate']
                state['lastUpdate'] = contract.functions[func_name]().call()
                
            elif target['type'] == 'compound':
                # Similar to harvest
                func_name = target['read'].get('pendingCompound', 'pendingRewards')
                state['pendingCompound'] = contract.functions[func_name]().call()
            
            duration_ms = (time.time() - start_time) * 1000
            logger.log_performance('read_state', duration_ms, True, 
                                 {'target': target['name'], 'state': state})
            return state
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"Error reading state for {target['name']}: {e}", 
                        exc_info=True, target=target['name'], error_type='state_read')
            logger.log_performance('read_state', duration_ms, False, 
                                 {'target': target['name'], 'error': str(e)})
            return {}
    
    def should_execute_target(self, target: Dict[str, Any], state: Dict[str, Any]) -> bool:
        """Check if target should be executed based on state"""
        now = int(time.time())
        
        # Check cooldown
        last_call = self.db.get_last_call_ts(target['name'])
        if last_call:
            cooldown = target.get('cooldownSec', 0)
            if (now - last_call) < cooldown:
                time_remaining = cooldown - (now - last_call)
                logger.debug(f"{target['name']}: cooldown active ({time_remaining}s remaining)",
                           target=target['name'], cooldown_remaining=time_remaining)
                return False
        
        # Check target-specific conditions
        if target['type'] == 'harvest':
            pending = state.get('pending', 0)
            min_threshold = get_min_pending_threshold(target)
            if pending < min_threshold:
                logger.debug(f"{target['name']}: pending rewards below threshold",
                           target=target['name'], pending=pending, threshold=min_threshold)
                return False
                
        elif target['type'] == 'twap':
            last_update = state.get('lastUpdate', 0)
            interval = target.get('intervalSec', 300)
            if (now - last_update) < interval:
                time_remaining = interval - (now - last_update)
                logger.debug(f"{target['name']}: update interval not met ({time_remaining}s remaining)",
                           target=target['name'], interval_remaining=time_remaining)
                return False
        
        return True
    
    def process_target(self, chain_name: str, chain_config: Dict[str, Any], target: Dict[str, Any]):
        """Process a single target"""
        try:
            # Check if target is paused
            if self.db.is_paused(target['name']):
                logger.debug(f"{target['name']}: currently paused", 
                           target=target['name'], chain=chain_name)
                return
            
            # Get Web3 connection
            w3 = self.rpc_manager.get_w3(chain_name, chain_config['rpc'])
            
            # Check gas price
            base_fee_gwei = get_base_fee_gwei(w3)
            if base_fee_gwei > chain_config['maxBaseFeeGwei']:
                logger.warning(f"{chain_name}: gas too high ({base_fee_gwei:.2f} > {chain_config['maxBaseFeeGwei']} gwei)",
                             chain=chain_name, target=target['name'], 
                             gas_price=base_fee_gwei, max_gas=chain_config['maxBaseFeeGwei'])
                return
            
            # Read on-chain state
            state = self.read_target_state(w3, target)
            if not state:
                return
            
            # Check if should execute
            if not self.should_execute_target(target, state):
                return
            
            # Estimate profit
            profit_estimate = estimate_profit_usd(chain_config, target, state, base_fee_gwei)
            
            # Check profit gate
            if not passes_profit_gate(profit_estimate, self.config):
                logger.debug(f"{target['name']}: profit gate not met "
                           f"(net=${profit_estimate['net_usd']:.4f}, "
                           f"reward/gas={profit_estimate['reward_usd']/max(profit_estimate['gas_usd'], 0.001):.2f}x)",
                           target=target['name'], chain=chain_name,
                           net_usd=profit_estimate['net_usd'],
                           reward_usd=profit_estimate['reward_usd'],
                           gas_usd=profit_estimate['gas_usd'])
                return
            
            # Execute transaction
            logger.info(f"{target['name']}: executing "
                       f"(expected net=${profit_estimate['net_usd']:.4f})",
                       target=target['name'], chain=chain_name,
                       expected_net_usd=profit_estimate['net_usd'],
                       gas_price=base_fee_gwei)
            
            result = execute_janitor_transaction(w3, chain_config, target, self.tx_builder)
            
            if result['status'] == 'success':
                # Log successful run
                self.db.log_run(
                    chain=chain_name,
                    target=target['name'],
                    action=target['write']['exec'],
                    tx_hash=result['tx_hash'],
                    gas_used=result['gas_used'],
                    gas_cost_usd=result['gas_cost_usd'],
                    reward_usd=profit_estimate['reward_usd'],
                    net_usd=profit_estimate['reward_usd'] - result['gas_cost_usd'],
                    status='success'
                )
                
                # Update state
                self.db.update_state(
                    target=target['name'],
                    timestamp=int(time.time()),
                    tx_hash=result['tx_hash']
                )
                
                net_profit = profit_estimate['reward_usd'] - result['gas_cost_usd']
                logger.info(f"{target['name']}: success! "
                           f"tx={result['tx_hash']}, "
                           f"net=${net_profit:.4f}",
                           target=target['name'], chain=chain_name,
                           tx_hash=result['tx_hash'],
                           profit_usd=net_profit,
                           gas_used=result['gas_used'])
                
                # Log to transaction logger
                logger.log_transaction(chain_name, target['name'], result['tx_hash'],
                                     result['gas_used'], net_profit, 'success')
            else:
                # Log failure
                self.db.log_failure(
                    chain=chain_name,
                    target=target['name'],
                    error=result.get('error', 'Unknown error')
                )
                
                # Check circuit breaker
                failures = self.db.get_consecutive_failures(target['name'])
                if failures >= self.global_config['maxConsecutiveFailures']:
                    self.db.pause_target(
                        target['name'],
                        self.global_config['circuitBreakerMinutes']
                    )
                    logger.error(f"{target['name']}: circuit breaker activated after {failures} failures",
                               target=target['name'], chain=chain_name,
                               consecutive_failures=failures,
                               pause_minutes=self.global_config['circuitBreakerMinutes'])
        
        except Exception as e:
            logger.error(f"Error processing {target['name']}: {e}",
                       exc_info=True, target=target['name'], chain=chain_name,
                       error_type='process_target')
            self.db.log_failure(chain_name, target['name'], str(e))
    
    def run_loop(self):
        """Main janitor loop"""
        logger.info("Starting janitor loop", 
                   loop_interval=5,
                   chains=list(self.config['chains'].keys()))
        loop_interval = 5  # seconds
        loop_count = 0
        
        while self.running:
            try:
                if self.paused:
                    time.sleep(loop_interval)
                    continue
                
                loop_count += 1
                loop_start = time.time()
                
                # Log loop iteration every 100 loops
                if loop_count % 100 == 0:
                    logger.debug(f"Loop iteration {loop_count}", loop_count=loop_count)
                
                # Process each chain
                for chain_name, chain_config in self.config['chains'].items():
                    # Process each target
                    for target in chain_config['targets']:
                        if not validate_target(target):
                            continue
                        
                        if not target.get('enabled', True):
                            continue
                        
                        self.process_target(chain_name, chain_config, target)
                
                # Log loop performance
                loop_duration = (time.time() - loop_start) * 1000
                if loop_duration > 1000:  # Log if loop takes more than 1 second
                    logger.log_performance('main_loop', loop_duration, True,
                                         {'iteration': loop_count})
                
                # Sleep before next iteration
                time.sleep(loop_interval)
            
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received", loop_count=loop_count)
                break
            except Exception as e:
                logger.error(f"Loop error: {e}", exc_info=True, 
                           error_type='main_loop', loop_count=loop_count)
                time.sleep(loop_interval)
        
        logger.info("Janitor loop stopped", total_loops=loop_count)
    
    def run(self):
        """Start the janitor bot"""
        try:
            # Log daily P&L at startup
            pnl = self.db.get_daily_pnl()
            logger.info(f"Today's P&L: net=${pnl['total_net_usd']:.2f}, "
                       f"runs={pnl['total_runs']}, failures={pnl['total_failures']}",
                       daily_net_usd=pnl['total_net_usd'],
                       daily_runs=pnl['total_runs'],
                       daily_failures=pnl['total_failures'])
            
            # Start main loop
            self.run_loop()
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            sys.exit(1)

def main():
    """Entry point"""
    bot = JanitorBot()
    bot.run()

if __name__ == "__main__":
    main()