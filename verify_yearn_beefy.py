#!/usr/bin/env python3
"""
Verify and setup Yearn and Beefy treasury/strategy addresses
"""

from web3 import Web3
import json

# Connect to Arbitrum
RPC = "https://arb-mainnet.g.alchemy.com/v2/5mlDO-31svMGY53J2Urqv"
w3_arb = Web3(Web3.HTTPProvider(RPC))

# Connect to Base
BASE_RPC = "https://base-mainnet.g.alchemy.com/v2/3AvaLFHobnzEIToydrEiN"
w3_base = Web3(Web3.HTTPProvider(BASE_RPC))

# Addresses provided
YEARN_ADDRESSES = [
    "0x182863131F9a4630fF9E27830d945B1413e347E8",
    "0x6FAF8b7fFeE3306EfcFc2BA9Fec912b4d49834C1",
    "0x7DEB119b92b76f78C212bc54FBBb34CEA75f4d4A",
    "0xc0ba9bfED28aB46Da48d2B69316A3838698EF3f5",
    "0x989381F7eFb45F97E46BE9f390a69c5d94bf9e17",
    "0x4d81C7d534D703E0a0AECaDF668C0E0253E1f1C3",
    "0x25f32eC89ce7732A4E9f8F3340a09259F823b7d3"
]

BEEFY_TREASURIES = {
    "arbitrum": "0x3f5eddad52C665A4AA011cd11A21E1d5107d7862",
    "base": "0x1A07DceEfeEbBA3D1873e2B92BeF190d2f11C3cB"
}

# Common harvest/keeper function signatures
HARVEST_SIGS = [
    "0x4641257d",  # harvest()
    "0x018ee9b7",  # harvest(address)
    "0x3d18b912",  # report()
    "0x9f678cdc",  # tend()
    "0xa0712d68",  # compound()
    "0x853828b6",  # withdrawAll()
]

def check_contract_code(w3, address, chain_name):
    """Check if address has contract code"""
    try:
        code = w3.eth.get_code(address)
        has_code = len(code) > 2  # More than just '0x'
        
        if has_code:
            # Try to get recent transactions
            block_num = w3.eth.block_number
            
            print(f"  ✅ {chain_name}: Contract exists")
            print(f"     Latest block: {block_num:,}")
            
            return True
        else:
            print(f"  ❌ {chain_name}: No contract code")
            return False
    except Exception as e:
        print(f"  ⚠️  {chain_name}: Error checking - {e}")
        return False

def analyze_yearn_addresses():
    """Analyze Yearn addresses on Arbitrum"""
    print("🔍 Analyzing Yearn Addresses on Arbitrum")
    print("=" * 50)
    
    valid_targets = []
    
    for i, addr in enumerate(YEARN_ADDRESSES, 1):
        print(f"\n{i}. {addr}")
        
        # Check if contract exists
        if check_contract_code(w3_arb, addr, "Arbitrum"):
            # Try to identify the contract type
            # You would need to check these on Arbiscan for actual functions
            valid_targets.append({
                "address": addr,
                "chain": "arbitrum",
                "protocol": "yearn",
                "needs_verification": True
            })
    
    return valid_targets

def analyze_beefy_treasuries():
    """Analyze Beefy treasury contracts"""
    print("\n🔍 Analyzing Beefy Treasury Contracts")
    print("=" * 50)
    
    treasury_info = []
    
    # Check Arbitrum treasury
    print(f"\n1. Arbitrum Treasury: {BEEFY_TREASURIES['arbitrum']}")
    if check_contract_code(w3_arb, BEEFY_TREASURIES['arbitrum'], "Arbitrum"):
        treasury_info.append({
            "address": BEEFY_TREASURIES['arbitrum'],
            "chain": "arbitrum",
            "type": "treasury",
            "protocol": "beefy"
        })
    
    # Check Base treasury
    print(f"\n2. Base Treasury: {BEEFY_TREASURIES['base']}")
    if check_contract_code(w3_base, BEEFY_TREASURIES['base'], "Base"):
        treasury_info.append({
            "address": BEEFY_TREASURIES['base'],
            "chain": "base",
            "type": "treasury",
            "protocol": "beefy"
        })
    
    return treasury_info

def create_target_configs(yearn_targets, beefy_info):
    """Create target configurations for verified addresses"""
    
    targets = []
    
    # Create Yearn targets
    for yt in yearn_targets:
        target = {
            "name": f"Yearn_Strategy_{yt['address'][:8]}",
            "address": yt['address'],
            "abi": "abi/yearn_v3_strategy.json",
            "type": "harvest",
            "enabled": False,  # Start disabled until verified
            "params": [],
            "cooldownSec": 43200,
            "fixedRewardUSD": 0.50,
            "read": {},
            "write": {
                "exec": "report"  # Yearn v3 uses report()
            },
            "_note": "Yearn v3 strategy - needs function verification",
            "_verify_url": f"https://arbiscan.io/address/{yt['address']}#code"
        }
        targets.append(target)
    
    # Beefy treasuries might not be harvestable
    # They're usually for fee collection, not public harvesting
    
    return targets

def main():
    print("=" * 60)
    print("YEARN & BEEFY CONTRACT VERIFICATION")
    print("=" * 60)
    
    # Analyze Yearn addresses
    yearn_valid = analyze_yearn_addresses()
    
    # Analyze Beefy treasuries
    beefy_info = analyze_beefy_treasuries()
    
    # Create configurations
    if yearn_valid:
        targets = create_target_configs(yearn_valid, beefy_info)
        
        print("\n" + "=" * 60)
        print("RECOMMENDED TARGETS")
        print("=" * 60)
        
        print(f"\n📝 Found {len(yearn_valid)} Yearn contracts to verify")
        print(f"📝 Found {len(beefy_info)} Beefy treasury contracts")
        
        print("\n⚠️  IMPORTANT: Before enabling these targets:")
        print("  1. Check each address on Arbiscan/Basescan")
        print("  2. Look for public harvest/report/tend functions")
        print("  3. Verify there's a caller reward mechanism")
        print("  4. Check recent transactions for harvest patterns")
        
        # Save results
        output = {
            "yearn_addresses": yearn_valid,
            "beefy_treasuries": beefy_info,
            "suggested_targets": targets,
            "verification_needed": True
        }
        
        with open('yearn_beefy_targets.json', 'w') as f:
            json.dump(output, f, indent=2)
        
        print("\n💾 Saved to yearn_beefy_targets.json")
        
        print("\n🔍 Next steps:")
        print("  1. Visit each address on the block explorer")
        print("  2. Check 'Read Contract' for harvest functions")
        print("  3. Check 'Transactions' for recent harvest calls")
        print("  4. Verify caller rewards in the code")
        
        # Print direct links
        print("\n🔗 Verification links:")
        for addr in YEARN_ADDRESSES[:3]:  # Show first 3
            print(f"  • https://arbiscan.io/address/{addr}#code")
        
        if len(YEARN_ADDRESSES) > 3:
            print(f"  • ... and {len(YEARN_ADDRESSES) - 3} more in yearn_beefy_targets.json")

if __name__ == "__main__":
    main()