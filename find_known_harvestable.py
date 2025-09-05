#!/usr/bin/env python3
"""
Find known harvestable contracts on Arbitrum
Including GMX, Sushi, Camelot, and other DeFi protocols
"""

import json
import requests
from datetime import datetime

KNOWN_HARVESTABLE = [
    {
        "name": "GMX_RewardRouterV2", 
        "address": "0xA906F338CB21815cBc4Bc87ace9e68c87eF8d8F1",
        "type": "compound",
        "protocol": "GMX",
        "description": "GMX Reward Router V2 - compound() for esGMX and multiplier points",
        "verify": "https://arbiscan.io/address/0xA906F338CB21815cBc4Bc87ace9e68c87eF8d8F1#code"
    },
    {
        "name": "GMX_GlpRewardRouter",
        "address": "0xB95DB5B167D75e6d04227CfFFA61069348d271F5",
        "type": "compound",
        "protocol": "GMX",
        "description": "GMX GLP Reward Router - compound() for GLP rewards",
        "verify": "https://arbiscan.io/address/0xB95DB5B167D75e6d04227CfFFA61069348d271F5#code"
    },
    {
        "name": "Sushi_MiniChefV2",
        "address": "0xF4d73326C13a4Fc5FD7A064217e12780e9Bd62c3",
        "type": "harvest",
        "protocol": "Sushi",
        "description": "SushiSwap MiniChef V2 - harvest() for SUSHI rewards",
        "verify": "https://arbiscan.io/address/0xF4d73326C13a4Fc5FD7A064217e12780e9Bd62c3#code"
    },
    {
        "name": "Camelot_NftPool",
        "address": "0x6BC938abA940fB828D39Daa23A94dfc522120C11",
        "type": "harvest", 
        "protocol": "Camelot",
        "description": "Camelot NFT Pool - harvestPosition() for GRAIL rewards",
        "verify": "https://arbiscan.io/address/0x6BC938abA940fB828D39Daa23A94dfc522120C11#code"
    },
    {
        "name": "Radiant_MultiFeeDistribution",
        "address": "0x76ba3eC5f5adBf1C58c91e86502232317EeA72dE",
        "type": "harvest",
        "protocol": "Radiant",
        "description": "Radiant Capital Fee Distribution - exit() for RDNT rewards",
        "verify": "https://arbiscan.io/address/0x76ba3eC5f5adBf1C58c91e86502232317EeA72dE#code"
    },
    {
        "name": "Gains_Trading",
        "address": "0x6B8D3C08072a020aC065c467ce922e3A36D3F9d6",
        "type": "harvest",
        "protocol": "Gains",
        "description": "Gains Network Trading - harvest rewards",
        "verify": "https://arbiscan.io/address/0x6B8D3C08072a020aC065c467ce922e3A36D3F9d6#code"
    },
    {
        "name": "Pendle_MarketETH",
        "address": "0x08a152834de126d2ef83D612ff36e4523FD0017F",
        "type": "twap",
        "protocol": "Pendle",
        "description": "Pendle PT-rsETH market - updateImpliedRate() for TWAP",
        "verify": "https://arbiscan.io/address/0x08a152834de126d2ef83D612ff36e4523FD0017F#code"
    },
    {
        "name": "Pendle_MarketUSD",
        "address": "0x2Dfaf9a5E4F293BceedE49f2dBa29aACDD88E0C4",
        "type": "twap",
        "protocol": "Pendle",
        "description": "Pendle PT-USD market - updateImpliedRate() for TWAP",
        "verify": "https://arbiscan.io/address/0x2Dfaf9a5E4F293BceedE49f2dBa29aACDD88E0C4#code"
    },
    {
        "name": "Vela_VLP",
        "address": "0xC4ABADE3a15064F9E3596943c699032748b13352",
        "type": "compound",
        "protocol": "Vela",
        "description": "Vela Exchange VLP - compound rewards",
        "verify": "https://arbiscan.io/address/0xC4ABADE3a15064F9E3596943c699032748b13352#code"
    },
    {
        "name": "Plutus_PlsJones",
        "address": "0xe7f6C3c1F0018E4C08aCC52965e5cbfF99e34A44",
        "type": "harvest",
        "protocol": "Plutus",
        "description": "Plutus plsJONES - harvest() for PLS rewards",
        "verify": "https://arbiscan.io/address/0xe7f6C3c1F0018E4C08aCC52965e5cbfF99e34A44#code"
    }
]

def main():
    print("🧹 Janitor Bot - Known Harvestable Contracts")
    print("=" * 80)
    
    print(f"\n📋 {len(KNOWN_HARVESTABLE)} Known Harvestable Contracts on Arbitrum:\n")
    
    by_protocol = {}
    for contract in KNOWN_HARVESTABLE:
        protocol = contract['protocol']
        if protocol not in by_protocol:
            by_protocol[protocol] = []
        by_protocol[protocol].append(contract)
    
    # Show by protocol
    for protocol, contracts in sorted(by_protocol.items()):
        print(f"\n🏢 {protocol} ({len(contracts)} contracts)")
        print("-" * 40)
        
        for c in contracts:
            print(f"  • {c['name']}")
            print(f"    Address: {c['address']}")
            print(f"    Type: {c['type']}")
            print(f"    {c['description']}")
    
    # Generate config samples
    print("\n💾 Sample Configuration for targets.json:")
    print("-" * 80)
    
    # GMX example
    gmx_config = {
        "name": "GMX_RewardRouterV2",
        "address": "0xA906F338CB21815cBc4Bc87ace9e68c87eF8d8F1",
        "abi": "abi/gmx_reward_router.json",
        "type": "compound",
        "read": {
            "pendingRewards": "claimableRewards"
        },
        "write": {
            "exec": "compound"
        },
        "params": [],
        "rewardToken": "0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a",
        "rewardTokenDecimals": 18,
        "rewardTokenSymbol": "GMX",
        "rewardPriceUSD": 30.0,
        "callFeeBps": 0,
        "cooldownSec": 3600,
        "minPendingRewardTokens": 0.01,
        "enabled": False,
        "_note": "GMX Reward Router V2 - auto-compound esGMX",
        "_verify": "https://arbiscan.io/address/0xA906F338CB21815cBc4Bc87ace9e68c87eF8d8F1#code"
    }
    
    print(json.dumps(gmx_config, indent=2))
    
    print("\n⚠️  Next Steps:")
    print("1. Verify each contract has the expected function")
    print("2. Check recent transactions for activity")
    print("3. Download or create appropriate ABIs")
    print("4. Configure in targets.json")
    print("5. Test with small amounts first")
    
    # Save to file
    output = {
        "timestamp": datetime.now().isoformat(),
        "contracts": KNOWN_HARVESTABLE,
        "sample_config": gmx_config
    }
    
    with open('known_harvestable.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n✅ Saved {len(KNOWN_HARVESTABLE)} contracts to known_harvestable.json")

if __name__ == "__main__":
    main()