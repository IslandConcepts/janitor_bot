#!/bin/bash

# Script to help update RPC configuration

echo "🔮 Alchemy RPC Setup Helper"
echo "=========================="
echo ""
echo "1. Copy your Alchemy API key from: https://dashboard.alchemy.com/"
echo "2. It looks like: 'YOUR_API_KEY_HERE' (about 32 characters)"
echo ""
read -p "Paste your Alchemy API key: " API_KEY

if [ -z "$API_KEY" ]; then
    echo "❌ No API key provided"
    exit 1
fi

# Create backup of .env
cp .env .env.backup
echo "✅ Created backup: .env.backup"

# Update the RPC URLs in .env
sed -i '' "s|ARBITRUM_RPC_1=.*|ARBITRUM_RPC_1=https://arb-mainnet.g.alchemy.com/v2/${API_KEY}|" .env
sed -i '' "s|ARBITRUM_RPC_2=.*|ARBITRUM_RPC_2=https://arb1.arbitrum.io/rpc|" .env
sed -i '' "s|ARBITRUM_RPC_3=.*|ARBITRUM_RPC_3=wss://arb-mainnet.g.alchemy.com/v2/${API_KEY}|" .env

echo ""
echo "✅ Updated .env with Alchemy endpoints:"
echo "   Primary RPC: https://arb-mainnet.g.alchemy.com/v2/${API_KEY:0:8}..."
echo "   Backup RPC: https://arb1.arbitrum.io/rpc"
echo "   WebSocket: wss://arb-mainnet.g.alchemy.com/v2/${API_KEY:0:8}..."
echo ""
echo "Testing connection..."

# Test the connection
python3 -c "
from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv()
rpc = os.getenv('ARBITRUM_RPC_1')
w3 = Web3(Web3.HTTPProvider(rpc))

if w3.is_connected():
    block = w3.eth.block_number
    print(f'✅ Successfully connected to Alchemy!')
    print(f'   Current Arbitrum block: {block:,}')
else:
    print('❌ Could not connect. Please check your API key.')
"

echo ""
echo "Next steps:"
echo "1. Run: python test_wallet.py"
echo "2. Fund your wallet with ETH on Arbitrum"
echo "3. Start the bot: ./run.sh start"