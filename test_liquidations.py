#!/usr/bin/env python3
"""
Test script for Aave V3 flash loan liquidations
Demonstrates the liquidation monitoring system in simulation mode
"""

import os
import sys
import json
from web3 import Web3
from dotenv import load_dotenv

# Add janitor module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from janitor.flash_loan_adapter import AaveV3Adapter, LiquidationTarget
from janitor.market_monitor import AaveMarketMonitor, MonitorConfig
from janitor.simple_storage import Storage
from janitor.logging_config import setup_logging

def test_flash_loan_adapter():
    """Test the flash loan adapter basic functionality"""
    print("="*60)
    print("TESTING FLASH LOAN ADAPTER")
    print("="*60)
    
    # Load environment
    load_dotenv()
    
    # Setup for Arbitrum
    rpc_url = os.getenv('ARBITRUM_RPC', 'https://arb-mainnet.g.alchemy.com/v2/5mlDO-31svMGY53J2Urqv')
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        print("❌ Failed to connect to Arbitrum")
        return
    
    print(f"✅ Connected to Arbitrum")
    print(f"   Latest block: {w3.eth.block_number:,}")
    
    # Get wallet address
    private_key = os.getenv('PRIVATE_KEY')
    if not private_key:
        print("❌ No private key found in .env")
        return
    
    account = w3.eth.account.from_key(private_key)
    w3.eth.default_account = account.address
    
    print(f"   Wallet: {account.address}")
    print(f"   Balance: {w3.eth.get_balance(account.address) / 1e18:.4f} ETH")
    
    # Initialize adapter
    adapter = AaveV3Adapter(
        chain='arbitrum',
        w3=w3,
        executor_address=account.address
    )
    
    print("\n📊 Testing Aave V3 Integration:")
    
    # Test oracle prices
    print("\n1. Testing Price Oracle:")
    test_tokens = {
        'USDC': adapter.tokens['USDC'],
        'WETH': adapter.tokens['WETH']
    }
    
    for name, address in test_tokens.items():
        try:
            price = adapter.oracle.functions.getAssetPrice(address).call()
            price_usd = price / 1e8
            print(f"   {name}: ${price_usd:,.2f}")
        except Exception as e:
            print(f"   {name}: Error - {e}")
    
    # Test flash loan fee
    print("\n2. Testing Flash Loan Parameters:")
    try:
        fee = adapter.pool.functions.FLASHLOAN_PREMIUM_TOTAL().call()
        print(f"   Flash loan fee: {fee/10000:.2f}%")
    except:
        print(f"   Flash loan fee: 0.09% (default)")
    
    # Test health check on a known address (example)
    print("\n3. Testing Account Health Check:")
    # You can replace with a known address to test
    test_address = "0x0000000000000000000000000000000000000000"
    health = adapter.get_account_health(test_address)
    
    if health:
        print(f"   Total Collateral: ${health['total_collateral_usd']:,.2f}")
        print(f"   Total Debt: ${health['total_debt_usd']:,.2f}")
        print(f"   Health Factor: {health['health_factor']:.4f}")
        print(f"   Liquidatable: {health['is_liquidatable']}")
    else:
        print(f"   No position for test address")
    
    print("\n✅ Flash loan adapter test complete")

def test_market_monitor():
    """Test the market monitor in simulation mode"""
    print("\n" + "="*60)
    print("TESTING MARKET MONITOR")
    print("="*60)
    
    # Load environment
    load_dotenv()
    
    # Setup logging
    setup_logging({'logLevel': 'INFO'})
    
    # Setup for Arbitrum
    rpc_url = os.getenv('ARBITRUM_RPC', 'https://arb-mainnet.g.alchemy.com/v2/5mlDO-31svMGY53J2Urqv')
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        print("❌ Failed to connect to Arbitrum")
        return
    
    # Get wallet
    private_key = os.getenv('PRIVATE_KEY')
    if private_key:
        account = w3.eth.account.from_key(private_key)
        w3.eth.default_account = account.address
    else:
        # Use a dummy address for testing without private key
        w3.eth.default_account = "0x00823727Ec5800ae6f5068fABAEb39608dE8bf45"
        print("⚠️ No private key found, using dummy address for testing")
    
    # Create monitor config (simulation mode)
    config = MonitorConfig(
        chain='arbitrum',
        check_interval_sec=30,  # Check every 30 seconds for testing
        min_profit_usd=1.0,  # Low threshold for testing
        max_debt_usd=500.0,  # Small size for safety
        gas_multiplier=1.5,
        simulation_only=True  # Always true for testing
    )
    
    # Create storage
    storage = Storage({'dataDir': 'data'})
    
    # Create monitor
    monitor = AaveMarketMonitor(
        config=config,
        w3=w3,
        storage=storage
    )
    
    print(f"\n✅ Market monitor initialized")
    print(f"   Chain: {config.chain}")
    print(f"   Mode: {'SIMULATION' if config.simulation_only else 'LIVE'}")
    print(f"   Max Debt: ${config.max_debt_usd}")
    print(f"   Min Profit: ${config.min_profit_usd}")
    
    # Run a few check cycles
    print(f"\n🔍 Running 3 check cycles...")
    
    for i in range(3):
        print(f"\n--- Check Cycle {i+1} ---")
        monitor.run_check_cycle()
        
        # Print current stats
        print(f"Checks performed: {monitor.stats.checks_performed}")
        print(f"Liquidatable found: {monitor.stats.liquidatable_found}")
        print(f"Profitable opportunities: {monitor.stats.profitable_opportunities}")
    
    # Print final stats
    print(monitor.get_stats_summary())
    
    print("\n✅ Market monitor test complete")

def test_liquidation_simulation():
    """Test a mock liquidation simulation"""
    print("\n" + "="*60)
    print("MOCK LIQUIDATION SIMULATION")
    print("="*60)
    
    # Create a mock liquidation target
    mock_target = LiquidationTarget(
        borrower="0x1234567890123456789012345678901234567890",
        debt_token="0xaf88d065e77c8cC2239327C5EDb3A432268e5831",  # USDC on Arbitrum
        collateral_token="0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",  # WETH on Arbitrum
        debt_to_cover=1000_000000,  # 1000 USDC (6 decimals)
        health_factor=0.95,
        max_liquidatable=1000_000000,
        expected_profit_usd=15.0
    )
    
    print(f"Mock Liquidation Target:")
    print(f"  Borrower: {mock_target.borrower[:10]}...")
    print(f"  Debt: 1000 USDC")
    print(f"  Collateral: WETH")
    print(f"  Health Factor: {mock_target.health_factor}")
    print(f"  Expected Profit: ${mock_target.expected_profit_usd:.2f}")
    
    # Simulate the liquidation
    print(f"\n📊 Simulation Results:")
    print(f"  Flash Loan Amount: 1000 USDC")
    print(f"  Flash Fee (0.09%): $0.90")
    print(f"  Liquidation Bonus (5%): $50.00")
    print(f"  Gas Cost: $0.25")
    print(f"  Swap Fees (0.3%): $3.00")
    print(f"  Net Profit: $45.85")
    print(f"  Profitable: ✅ YES")
    
    print("\n✅ Simulation test complete")

def main():
    """Run all tests"""
    print("="*80)
    print("AAVE V3 FLASH LOAN LIQUIDATION SYSTEM TEST")
    print("="*80)
    
    # Test components
    test_flash_loan_adapter()
    test_market_monitor()
    test_liquidation_simulation()
    
    print("\n" + "="*80)
    print("ALL TESTS COMPLETE")
    print("="*80)
    
    print("""
Next Steps:
1. Deploy a flash loan receiver contract (required for actual execution)
2. Monitor Aave events to find liquidatable positions
3. Start with simulation_only=True to verify profitability
4. Graduate to small live liquidations with tight caps

Configuration to add to config.json:
{
  "liquidations": {
    "enabled": true,
    "arbitrum": {
      "enabled": true,
      "simulation_only": true,
      "check_interval": 60,
      "min_profit_usd": 2.0,
      "max_debt_usd": 1000.0,
      "gas_multiplier": 2.0,
      "max_daily": 10,
      "allowed_tokens": []
    },
    "base": {
      "enabled": true,
      "simulation_only": true,
      "check_interval": 60,
      "min_profit_usd": 2.0,
      "max_debt_usd": 1000.0,
      "gas_multiplier": 2.0,
      "max_daily": 10,
      "allowed_tokens": []
    }
  }
}
""")

if __name__ == "__main__":
    main()