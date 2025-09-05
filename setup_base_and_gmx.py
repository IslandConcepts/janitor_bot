#!/usr/bin/env python3
"""
Setup Base network and update GMX configuration
"""

import json

def create_base_config():
    """Create Base network configuration"""
    
    print("📝 Creating Base network configuration...")
    
    base_config = {
        "chains": {
            "arbitrum": {
                "chainId": 42161,
                "rpc": ["ARBITRUM_RPC_1"],
                "nativeSymbol": "ETH",
                "nativeUsd": 2500.0,
                "gasLimitCaps": {
                    "harvest": 500000,
                    "compound": 400000
                },
                "maxBaseFeeGwei": 0.2,
                "fromEnvKey": "ARBITRUM_FROM_ADDRESS",
                "pkEnvKey": "ARBITRUM_PRIVATE_KEY",
                "targets": [
                    # Existing Beefy vaults
                    {
                        "name": "Beefy_MIM_USDC",
                        "address": "0xD945e7937066f3A8b87460301666c5287f5315dD",
                        "abi": "abi/beefy_strategy.json",
                        "type": "harvest",
                        "enabled": True,
                        "params": ["0x00823727Ec5800ae6f5068fABAEb39608dE8bf45"],
                        "cooldownSec": 43200,
                        "fixedRewardUSD": 0.50,
                        "read": {"lastHarvest": "lastHarvest"},
                        "write": {"exec": "harvest"}
                    },
                    {
                        "name": "Beefy_USDC_USDT_GHO",
                        "address": "0x21d37617F19910a82C6CaeE0BD973Bf87Ce11D8e",
                        "abi": "abi/beefy_strategy.json",
                        "type": "harvest",
                        "enabled": True,
                        "params": ["0x00823727Ec5800ae6f5068fABAEb39608dE8bf45"],
                        "cooldownSec": 43200,
                        "fixedRewardUSD": 0.50,
                        "read": {"lastHarvest": "lastHarvest"},
                        "write": {"exec": "harvest"}
                    },
                    {
                        "name": "Beefy_tBTC_WBTC",
                        "address": "0xa2172783Eafd97FBF25bffFAFda3aD03B5115613",
                        "abi": "abi/beefy_strategy.json",
                        "type": "harvest",
                        "enabled": True,
                        "params": ["0x00823727Ec5800ae6f5068fABAEb39608dE8bf45"],
                        "cooldownSec": 43200,
                        "fixedRewardUSD": 0.50,
                        "read": {"lastHarvest": "lastHarvest"},
                        "write": {"exec": "harvest"}
                    },
                    # GMX self-compounding (now that you're staked)
                    {
                        "name": "GMX_SelfCompound",
                        "address": "0xA906F338CB21815cBc4Bc87ace9e68c87eF8d8F1",
                        "abi": "abi/gmx_reward_router.json",
                        "type": "compound",
                        "enabled": True,
                        "params": [],
                        "cooldownSec": 86400,  # Daily compounding
                        "fixedRewardUSD": 0.0,  # No direct rewards, just compounding
                        "read": {},
                        "write": {"exec": "compound"},
                        "_note": "Self-compounds your GMX staking position"
                    }
                ]
            },
            "base": {
                "chainId": 8453,
                "rpc": ["BASE_RPC_1"],
                "nativeSymbol": "ETH", 
                "nativeUsd": 2500.0,
                "gasLimitCaps": {
                    "harvest": 500000,
                    "compound": 400000
                },
                "maxBaseFeeGwei": 0.1,
                "fromEnvKey": "BASE_FROM_ADDRESS", 
                "pkEnvKey": "BASE_PRIVATE_KEY",
                "targets": [
                    # We'll add Base Beefy vaults here after finding good ones
                    {
                        "name": "Placeholder_Base_Vault",
                        "address": "0x0000000000000000000000000000000000000000",
                        "enabled": False,
                        "_note": "To be replaced with actual Base vaults"
                    }
                ]
            }
        }
    }
    
    return base_config

def get_base_rpc_instructions():
    """Instructions for getting Base RPC"""
    
    print("\n🔗 To get a Base RPC endpoint:")
    print("\n1. **Alchemy** (Recommended):")
    print("   - Go to: https://dashboard.alchemy.com")
    print("   - Create new app → Select 'Base Mainnet'")
    print("   - Copy the HTTPS endpoint")
    print("\n2. **Public RPCs** (Less reliable):")
    print("   - https://mainnet.base.org")
    print("   - https://base.publicnode.com")
    print("\n3. **Add to .env file:**")
    print("   BASE_RPC_1=https://base-mainnet.g.alchemy.com/v2/YOUR_KEY")
    print("   BASE_FROM_ADDRESS=0x00823727Ec5800ae6f5068fABAEb39608dE8bf45")
    print("   BASE_PRIVATE_KEY=(same as ARBITRUM_PRIVATE_KEY)")

def find_base_beefy_strategies():
    """Find actual Base Beefy strategy addresses"""
    
    print("\n🔍 Finding Base Beefy strategies...")
    
    # These would need to be fetched from Beefy API
    # Format: https://api.beefy.finance/vaults/base
    
    sample_base_vaults = [
        {
            "name": "Aerodrome_USDC_ETH",
            "vault": "aerodrome-usdc-weth",
            "strategy": "Check on basescan.org",
            "description": "Aerodrome USDC-ETH LP"
        },
        {
            "name": "Aerodrome_USDC_USDC",
            "vault": "aerodrome-usdc-usdbc",
            "strategy": "Check on basescan.org",
            "description": "Aerodrome stable pool"
        }
    ]
    
    print("\n📋 Sample Base vaults to investigate:")
    for vault in sample_base_vaults:
        print(f"  • {vault['name']}: {vault['description']}")
    
    return sample_base_vaults

if __name__ == "__main__":
    print("=" * 60)
    print("SETTING UP BASE NETWORK & GMX")
    print("=" * 60)
    
    # Create config
    config = create_base_config()
    
    # Save new config
    with open('janitor/targets_multichain.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("\n✅ Created janitor/targets_multichain.json")
    
    # Show RPC instructions
    get_base_rpc_instructions()
    
    # Find Base vaults
    base_vaults = find_base_beefy_strategies()
    
    print("\n" + "=" * 60)
    print("\n🎯 NEXT STEPS:")
    print("1. Get Base RPC endpoint from Alchemy")
    print("2. Add BASE_RPC_1 to .env file")
    print("3. Find specific Base vault strategy addresses")
    print("4. Update targets.json to use multichain config")
    print("5. Restart bot to harvest on both chains")
    
    print("\n💡 Your GMX self-compounding is already added!")
    print("   It will compound your position daily on Arbitrum")