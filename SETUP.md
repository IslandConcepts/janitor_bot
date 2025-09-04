# Janitor Bot Setup Guide

## Prerequisites

- Python 3.11+
- Git
- Docker (optional)
- Arbitrum RPC endpoint (Alchemy/Infura)
- Hot wallet with ~$50 ETH on Arbitrum

## Quick Setup

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/janitor-bot.git
cd janitor-bot
```

### 2. Install Dependencies

```bash
./run.sh install
# or manually:
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration:
- `ARBITRUM_PRIVATE_KEY`: Your hot wallet private key (use a dedicated bot wallet!)
- `ARBITRUM_FROM_ADDRESS`: Your hot wallet address
- `ARBITRUM_RPC_1`: Primary RPC endpoint (e.g., Alchemy)
- `ARBITRUM_RPC_2`: Backup RPC endpoint

### 4. Configure Targets

Edit `janitor/targets.json` to add real vault addresses:
- Replace example addresses with actual vault contracts
- Adjust reward prices and fees based on current values
- Set appropriate cooldowns and thresholds

### 5. Run the Bot

```bash
# Run locally
./run.sh start

# Or with Docker
./run.sh docker

# Run with dashboard
./run.sh dashboard  # In one terminal
./run.sh start      # In another terminal
```

## Finding Profitable Targets

### Where to Look

1. **Beefy Finance**: https://app.beefy.finance/
   - Look for vaults with "Harvest" call fees
   - Check their GitHub for contract addresses

2. **Yearn Finance**: https://yearn.finance/
   - V2/V3 vaults with harvest functions
   - Check docs for keeper requirements

3. **GMX**: https://gmx.io/
   - Price oracle updates
   - Position keepers

4. **Curve/Convex**: 
   - Gauge reward claims
   - Pool rebalances

### How to Verify Targets

1. Check contract on Arbiscan:
   - Look for `harvest()` or `compound()` functions
   - Verify call fees in contract code
   - Check `pendingRewards()` view function

2. Test on testnet first:
   - Deploy mock contracts if needed
   - Verify profit calculations
   - Test gas estimations

## Safety Checklist

- [ ] Using dedicated hot wallet (not main wallet)
- [ ] Wallet has minimal funds (~$50)
- [ ] Private key stored securely in .env
- [ ] .env file NOT committed to git
- [ ] RPC endpoints configured and working
- [ ] Target contracts verified on Arbiscan
- [ ] Gas limits set appropriately
- [ ] Profit multiplier configured (1.5x recommended)

## Monitoring

### Terminal Dashboard
```bash
./run.sh dashboard
```

### View Logs
```bash
# Real-time logs
./run.sh log-tail

# Analyze performance
./run.sh log-viewer --performance

# Check errors
./run.sh log-viewer --errors
```

### Metrics Endpoint
```bash
./run.sh metrics
# Visit http://localhost:8000/metrics
```

## Expected Returns

- **Week 1-2**: $80-150 (learning/tuning)
- **Month 1**: $400-600 (optimized targets)
- **Month 2+**: $1000-1500 (expanded coverage)

Returns depend on:
- Number of active targets
- Gas prices on Arbitrum
- Competition from other bots
- Protocol TVL and activity

## Troubleshooting

### Bot not executing
- Check gas prices (may be too high)
- Verify cooldowns aren't active
- Ensure pending rewards meet threshold
- Check wallet balance

### Transaction failures
- Verify contract ABI matches
- Check gas limits
- Ensure wallet has funds
- Review error logs

### Low profits
- Add more targets
- Optimize gas usage
- Adjust profit thresholds
- Run on additional chains

## Support

- GitHub Issues: https://github.com/YOUR_USERNAME/janitor-bot/issues
- Documentation: See LOGGING.md for detailed logging info

## License

MIT