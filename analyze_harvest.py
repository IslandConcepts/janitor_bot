#!/usr/bin/env python3
"""
Analyze a harvest transaction to see actual rewards received
"""

import sys
from web3 import Web3
from janitor.profit_tracker import ProfitTracker
from janitor.rpc import RPCManager
from janitor.config import load_config

def analyze_harvest(tx_hash: str = None):
    """Analyze a harvest transaction"""
    
    # Default to the recent successful harvest if no hash provided
    if not tx_hash:
        tx_hash = "0x1e791cd15eb23d4bdbfa1fe209e6dd80fb0bb9a2783c2e3d342cb018350a8de9"
    
    print(f"🔍 Analyzing harvest transaction: {tx_hash}")
    print("-" * 60)
    
    # Load config and connect to RPC
    config = load_config()
    rpc_manager = RPCManager()
    chain_config = config['chains']['arbitrum']
    w3 = rpc_manager.get_w3('arbitrum', chain_config['rpc'])
    
    # Get transaction receipt
    try:
        tx_receipt = w3.eth.get_transaction_receipt(tx_hash)
        tx = w3.eth.get_transaction(tx_hash)
    except Exception as e:
        print(f"❌ Error fetching transaction: {e}")
        return
    
    # Basic transaction info
    print(f"📋 Transaction Info:")
    print(f"   From: {tx['from']}")
    print(f"   To: {tx['to']}")
    print(f"   Block: {tx_receipt['blockNumber']:,}")
    print(f"   Status: {'✅ Success' if tx_receipt['status'] == 1 else '❌ Failed'}")
    print()
    
    # Gas analysis
    gas_used = tx_receipt['gasUsed']
    gas_price = tx_receipt.get('effectiveGasPrice', 0)
    gas_cost_eth = (gas_used * gas_price) / 1e18
    gas_cost_usd = gas_cost_eth * 2500  # Approximate ETH price
    
    print(f"⛽ Gas Usage:")
    print(f"   Gas Used: {gas_used:,} units")
    print(f"   Gas Price: {gas_price / 1e9:.4f} gwei")
    print(f"   Cost: {gas_cost_eth:.8f} ETH (${gas_cost_usd:.4f})")
    print()
    
    # Analyze rewards using ProfitTracker
    tracker = ProfitTracker(w3)
    harvester_address = chain_config.get('from') or chain_config.get('fromAddress')
    analysis = tracker.analyze_harvest_receipt(tx_receipt, harvester_address)
    
    print(f"💰 Rewards Analysis:")
    if analysis['rewards']:
        print(f"   Found {len(analysis['rewards'])} reward transfers:")
        for reward in analysis['rewards']:
            print(f"   • {reward['amount']:.8f} {reward['symbol']}")
            print(f"     Token: {reward['token_address']}")
            if reward['symbol'] in ['WETH', 'ETH']:
                value_usd = reward['amount'] * 2500
                print(f"     Value: ~${value_usd:.2f} @ $2500/ETH")
            elif reward['symbol'] == 'WBTC':
                value_usd = reward['amount'] * 65000
                print(f"     Value: ~${value_usd:.2f} @ $65000/BTC")
    else:
        print("   ⚠️  No ERC-20 transfers found to harvester address")
        print(f"   Harvester address checked: {harvester_address}")
    
    print()
    
    # Check logs for any harvest events
    print(f"📜 Event Logs ({len(tx_receipt.get('logs', []))} total):")
    for i, log in enumerate(tx_receipt.get('logs', [])[:5]):  # Show first 5 logs
        print(f"   Log {i}: {log['address'][:10]}...")
        if log.get('topics'):
            print(f"          Topic: {log['topics'][0][:10]}...")
    
    if len(tx_receipt.get('logs', [])) > 5:
        print(f"   ... and {len(tx_receipt['logs']) - 5} more logs")
    
    print()
    print("=" * 60)
    
    # Summary
    if analysis['rewards']:
        total_value = sum([
            r['amount'] * (2500 if r['symbol'] in ['WETH', 'ETH'] else 
                          65000 if r['symbol'] == 'WBTC' else 0)
            for r in analysis['rewards']
        ])
        net_profit = total_value - gas_cost_usd
        print(f"📊 Summary:")
        print(f"   Estimated Reward Value: ${total_value:.2f}")
        print(f"   Gas Cost: ${gas_cost_usd:.2f}")
        print(f"   Net Profit: ${net_profit:.2f}")
    else:
        print("📊 Summary: Unable to calculate profit (no rewards detected)")
        print("   This might mean:")
        print("   • Rewards were sent in native ETH (check internal txs)")
        print("   • Rewards were sent to a different address")
        print("   • Rewards will be distributed later")
        print("   • The vault has a different reward mechanism")

if __name__ == "__main__":
    tx_hash = sys.argv[1] if len(sys.argv) > 1 else None
    analyze_harvest(tx_hash)