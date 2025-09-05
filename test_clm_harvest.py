#!/usr/bin/env python3
"""
Test CLM harvest functions directly
"""

from web3 import Web3
import json

# Setup
RPC = "https://arb-mainnet.g.alchemy.com/v2/5mlDO-31svMGY53J2Urqv"
w3 = Web3(Web3.HTTPProvider(RPC))

# Known harvestable CLM strategy from Arbiscan
CLM_STRATEGY = "0x33a8B05CAf2853D724c18432762A6B7EbC1DCBec"
HARVESTER = "0x03d9964f4d93a24b58c0fc3a8df3474b59ba8557"
BOT_ADDRESS = "0x00823727Ec5800ae6f5068fABAEb39608dE8bf45"

# Test different harvest function signatures
test_signatures = [
    ("harvest()", "0x4641257d", []),
    ("harvest(address)", "0x018ee9b7", [BOT_ADDRESS]),
    ("harvest(address)", "0x018ee9b7", [HARVESTER]),  # Try with known harvester
    ("compound()", "0xa0712d68", []),
    ("work()", "0xe26b013b", []),
    ("tend()", "0x440368a4", []),
    ("doHarvest()", "0x3e2d86d1", []),
]

print(f"Testing CLM strategy: {CLM_STRATEGY}")
print(f"Known harvester: {HARVESTER}")
print(f"Our bot: {BOT_ADDRESS}")
print("="*60)

for func_name, selector, params in test_signatures:
    print(f"\nTesting {func_name}...")
    
    # Build call data
    call_data = selector
    for param in params:
        if isinstance(param, str) and param.startswith("0x"):
            call_data += param[2:].lower().zfill(64)
    
    # Try calling
    try:
        result = w3.eth.call({
            'from': BOT_ADDRESS,
            'to': CLM_STRATEGY,
            'data': call_data
        })
        print(f"  ✅ SUCCESS! Function callable")
        print(f"     Result: {result.hex()}")
    except Exception as e:
        error_str = str(e)
        if "revert" in error_str.lower():
            print(f"  ❌ Reverted: {error_str[:100]}")
        else:
            print(f"  ❌ Error: {error_str[:100]}")

# Also check what the known harvester is calling
print("\n" + "="*60)
print("Checking what known harvester uses...")

# Get a recent transaction from the harvester
filter_params = {
    'fromBlock': w3.eth.block_number - 10000,
    'toBlock': 'latest',
    'address': CLM_STRATEGY
}

try:
    logs = w3.eth.get_logs(filter_params)
    print(f"Found {len(logs)} recent logs")
    
    # Try to find harvest transactions
    for log in logs[-5:]:  # Last 5 logs
        tx_hash = log['transactionHash']
        tx = w3.eth.get_transaction(tx_hash)
        if tx['from'].lower() == HARVESTER.lower():
            print(f"\nFound harvest tx: {tx_hash.hex()}")
            print(f"  Input data: {tx['input'][:10]}")
            print(f"  Full selector: {tx['input'][:10]}")
            break
except Exception as e:
    print(f"Error getting logs: {e}")

print("\n" + "="*60)
print("Recommendations:")
print("1. The CLM strategies appear to use non-standard harvest functions")
print("2. They may be using proxy patterns with different implementations")
print("3. Consider monitoring the known harvester's transactions")
print("4. May need to reverse-engineer the actual function signature")