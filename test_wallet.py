#!/usr/bin/env python3
"""
Quick wallet verification script
"""

import os
import sys
from dotenv import load_dotenv
from web3 import Web3

# Load environment variables
load_dotenv()

def test_wallet():
    """Test wallet configuration"""
    
    # Get credentials
    private_key = os.getenv('ARBITRUM_PRIVATE_KEY')
    from_address = os.getenv('ARBITRUM_FROM_ADDRESS')
    rpc_url = os.getenv('ARBITRUM_RPC_1', 'https://arb1.arbitrum.io/rpc')
    
    print("🧹 Janitor Bot Wallet Test")
    print("=" * 50)
    
    # Check if credentials exist
    if not private_key or private_key == 'YOUR_PRIVATE_KEY_HERE':
        print("❌ Private key not configured in .env")
        print("   Please add your MetaMask private key to ARBITRUM_PRIVATE_KEY")
        return False
    
    if not from_address:
        print("❌ Wallet address not configured in .env")
        print("   Please add your MetaMask address to ARBITRUM_FROM_ADDRESS")
        return False
    
    print(f"✅ Wallet Address: {from_address}")
    
    # Verify private key matches address
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Derive address from private key
        from eth_account import Account
        account = Account.from_key(private_key)
        derived_address = account.address
        
        if derived_address.lower() != from_address.lower():
            print(f"❌ Private key doesn't match address!")
            print(f"   Expected: {from_address}")
            print(f"   Derived:  {derived_address}")
            return False
        
        print("✅ Private key matches address")
        
        # Check connection
        if w3.is_connected():
            print(f"✅ Connected to Arbitrum RPC")
            
            # Check balance
            balance_wei = w3.eth.get_balance(from_address)
            balance_eth = balance_wei / 1e18
            
            print(f"💰 Balance: {balance_eth:.6f} ETH")
            
            if balance_eth < 0.001:
                print("⚠️  Balance very low! Send at least 0.01 ETH to:")
                print(f"   {from_address}")
                print("   Network: Arbitrum One")
            elif balance_eth < 0.01:
                print("⚠️  Balance low. Consider adding more ETH for sustained operation")
            else:
                print("✅ Balance sufficient for operation")
                
            # Check gas price
            gas_price = w3.eth.gas_price
            gas_price_gwei = gas_price / 1e9
            print(f"⛽ Current gas price: {gas_price_gwei:.4f} Gwei")
            
        else:
            print("⚠️  Could not connect to Arbitrum RPC")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ Wallet setup complete and verified!")
    print("\nNext steps:")
    print("1. Fund your wallet with 0.01-0.02 ETH on Arbitrum")
    print("2. Run: ./run.sh start")
    print("3. Monitor: ./run.sh dashboard")
    
    return True

if __name__ == "__main__":
    success = test_wallet()
    sys.exit(0 if success else 1)