#!/usr/bin/env python3
"""
Test Alchemy RPC connection
"""

import os
from dotenv import load_dotenv
from web3 import Web3
import time

# Load environment variables
load_dotenv()

def test_alchemy():
    """Test Alchemy RPC connection"""
    
    print("🔮 Testing Alchemy RPC Connection")
    print("=" * 50)
    
    # Get RPC URL
    rpc_url = os.getenv('ARBITRUM_RPC_1')
    
    if not rpc_url or 'alchemy.com' not in rpc_url:
        print("❌ Alchemy RPC not configured in .env")
        return False
    
    # Extract API key for display
    api_key = rpc_url.split('/v2/')[-1]
    print(f"✅ Alchemy API key configured: {api_key[:8]}...")
    
    try:
        # Connect to Alchemy
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # Test connection
        start_time = time.time()
        is_connected = w3.is_connected()
        response_time = (time.time() - start_time) * 1000
        
        if is_connected:
            print(f"✅ Connected to Alchemy RPC")
            print(f"⚡ Response time: {response_time:.2f}ms")
            
            # Get network info
            block_number = w3.eth.block_number
            chain_id = w3.eth.chain_id
            gas_price = w3.eth.gas_price / 1e9
            
            print(f"\n📊 Arbitrum Network Status:")
            print(f"   Chain ID: {chain_id}")
            print(f"   Block Number: {block_number:,}")
            print(f"   Gas Price: {gas_price:.4f} Gwei")
            
            # Test wallet address if configured
            wallet_address = os.getenv('ARBITRUM_FROM_ADDRESS')
            if wallet_address and wallet_address != '0x43CFFd2479DA159241B662d1991275D9317f3103':
                balance_wei = w3.eth.get_balance(wallet_address)
                balance_eth = balance_wei / 1e18
                print(f"\n💰 Your Wallet:")
                print(f"   Address: {wallet_address}")
                print(f"   Balance: {balance_eth:.6f} ETH")
                
                if balance_eth < 0.001:
                    print(f"\n⚠️  Wallet needs funding!")
                    print(f"   Send 0.01-0.02 ETH to {wallet_address}")
                    print(f"   Network: Arbitrum One")
            else:
                print(f"\n⚠️  Please update your MetaMask wallet address in .env")
                print(f"   Current: {wallet_address}")
                print(f"   This appears to be the example address")
            
            # Test WebSocket connection
            ws_url = os.getenv('ARBITRUM_RPC_3')
            if ws_url and 'wss://' in ws_url:
                print(f"\n🔌 WebSocket endpoint configured")
                print(f"   URL: {ws_url[:40]}...")
            
            print("\n" + "=" * 50)
            print("✅ Alchemy setup complete!")
            print("\n🎯 Next Steps:")
            print("1. Update your wallet address and private key in .env")
            print("2. Fund your wallet with ETH on Arbitrum")
            print("3. Run: python test_wallet.py")
            print("4. Start the bot: ./run.sh start")
            
            return True
            
        else:
            print("❌ Could not connect to Alchemy")
            print("   Please check your API key")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check your API key is correct")
        print("2. Make sure the app is for 'Arbitrum One'")
        print("3. Try regenerating the API key in Alchemy dashboard")
        return False

if __name__ == "__main__":
    test_alchemy()