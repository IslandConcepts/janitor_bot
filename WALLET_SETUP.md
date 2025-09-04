# Hot Wallet Setup Guide

## Your Wallet Address
```
0x43CFFd2479DA159241B662d1991275D9317f3103
```

## ⚠️ CRITICAL SECURITY STEPS

### 1. Generate Private Key
If you haven't already created this wallet:
- Use MetaMask, Rainbow, or another wallet to create a NEW wallet
- This should be a DEDICATED bot wallet, NOT your main wallet
- Never use a wallet that holds significant funds

### 2. Get Your Private Key
In MetaMask:
1. Click the three dots menu
2. Select "Account Details"
3. Click "Export Private Key"
4. Enter your password
5. Copy the private key (starts with 0x)

### 3. Add to .env File
```bash
# Edit the .env file
nano .env

# Replace YOUR_PRIVATE_KEY_HERE with your actual private key
ARBITRUM_PRIVATE_KEY=0x... (your 64-character private key)
```

### 4. Secure the File
```bash
# Set restrictive permissions
chmod 600 .env

# Verify it's in .gitignore
grep "\.env" .gitignore
```

## 💰 Fund Your Bot Wallet

### Initial Funding (Arbitrum)
Send ETH to: `0x43CFFd2479DA159241B662d1991275D9317f3103`

Recommended amounts:
- **Testing**: 0.01 ETH (~$25)
- **Production Start**: 0.02 ETH (~$50)
- **Active Running**: 0.04 ETH (~$100)

### Check Balance
```bash
# Using the bot's built-in dashboard
./run.sh dashboard

# Or check on Arbiscan
# https://arbiscan.io/address/0x43CFFd2479DA159241B662d1991275D9317f3103
```

## 🔑 RPC Endpoints Setup

### Free Options

1. **Public RPC** (already configured)
   - Already set in your .env
   - May have rate limits

2. **Alchemy** (Recommended)
   - Sign up: https://www.alchemy.com/
   - Create an Arbitrum app
   - Copy your API key
   - Update .env:
   ```
   ARBITRUM_RPC_1=https://arb-mainnet.g.alchemy.com/v2/YOUR_KEY
   ARBITRUM_RPC_3=wss://arb-mainnet.g.alchemy.com/v2/YOUR_KEY
   ```

3. **Infura**
   - Sign up: https://infura.io/
   - Create a project
   - Enable Arbitrum
   - Update .env:
   ```
   ARBITRUM_RPC_1=https://arbitrum-mainnet.infura.io/v3/YOUR_KEY
   ```

## 🎯 Finding Profitable Targets

### Step 1: Find Vaults on Arbitrum

**Beefy Finance**
- Visit: https://app.beefy.finance/
- Filter: Arbitrum network
- Look for high TVL vaults
- Find contract addresses on their docs

**Example Beefy Vaults** (verify these are current):
```json
{
  "name": "Beefy_GLP_Vault",
  "address": "0x8080B5cE6dfb49a6B86370d6982B3e2A86FBBb08",
  "callFeeBps": 50
}
```

**Yearn Finance**
- Visit: https://yearn.fi/#/vaults
- Network: Arbitrum
- Check v3 vaults

### Step 2: Verify on Arbiscan

1. Go to https://arbiscan.io/
2. Search for the vault address
3. Check "Contract" tab
4. Look for:
   - `harvest()` function
   - `pendingRewards()` view function
   - Call fee parameters

### Step 3: Test a Target

Add to `janitor/targets.json`:
```json
{
  "name": "TestVault",
  "address": "0x...",
  "enabled": false,  // Start disabled
  "minPendingRewardTokens": 100
}
```

## 📊 Monitoring Your Wallet

### Gas Usage Tracking
```bash
# View recent transactions
./run.sh log-viewer --transactions

# Check daily P&L
./run.sh pnl
```

### Balance Alerts
The dashboard shows your balance with color coding:
- 🟢 Green: > 0.05 ETH (healthy)
- 🟡 Yellow: 0.01-0.05 ETH (refill soon)
- 🔴 Red: < 0.01 ETH (refill needed)

## 🚀 Starting the Bot

### Pre-flight Checklist
- [ ] Private key added to .env
- [ ] Wallet funded with ETH
- [ ] RPC endpoints configured
- [ ] At least one target configured
- [ ] .env file permissions set to 600

### Launch
```bash
# Test mode first
./run.sh test

# If tests pass, run production
./run.sh start

# Monitor with dashboard
./run.sh dashboard
```

## ⚡ Gas Optimization Tips

1. **Timing**: Run during low-gas periods (weekends, late night UTC)
2. **Batch**: Group multiple harvests if possible
3. **Limits**: Set appropriate MAX_BASE_FEE_GWEI
4. **Priority**: Keep priority fees low (0.01-0.05 Gwei)

## 🔒 Security Reminders

1. **Never share your private key**
2. **Never commit .env to git**
3. **Use a dedicated bot wallet**
4. **Keep minimal funds** (just enough for gas)
5. **Monitor regularly** for unusual activity
6. **Rotate keys** if you suspect compromise

## 📈 Expected Gas Usage

- Average harvest tx: 200,000-400,000 gas
- At 0.1 Gwei: ~$0.05-0.10 per tx
- Daily usage: $1-5 depending on activity
- Weekly: $10-30

Your 0.02 ETH should last 1-2 weeks of active running.

## Need Help?

- Check logs: `./run.sh log-tail`
- View errors: `./run.sh log-viewer --errors`
- Dashboard: `./run.sh dashboard`
- Arbiscan: https://arbiscan.io/address/0x43CFFd2479DA159241B662d1991275D9317f3103