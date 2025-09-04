# Janitor Bot Logging System

## Overview

The janitor bot maintains comprehensive, detailed logs with multiple output formats and analysis tools.

## Log Files

All logs are stored in `data/logs/` directory:

### 1. **janitor.log** - Main Log File
- Human-readable format with detailed context
- Rotating file (10MB max, 10 backups)
- Includes all log levels from DEBUG to CRITICAL
- Color-coded when viewing in terminal

### 2. **janitor.json** - Structured JSON Logs
- Machine-readable JSON format for parsing
- Contains all metadata and context fields
- Perfect for analysis and monitoring tools
- Rotating file (10MB max, 5 backups)

### 3. **errors.log** - Error-Only Log
- Contains only ERROR and CRITICAL level logs
- Detailed stack traces and error context
- Rotating file (5MB max, 5 backups)
- Quick reference for troubleshooting

### 4. **transactions.log** - Transaction Log
- Dedicated log for successful transactions
- Format: `timestamp | CHAIN | TARGET | TX_HASH | GAS | PROFIT | STATUS`
- Permanent record of all executed transactions
- No rotation - keeps complete history

### 5. **performance.log** - Performance Metrics
- JSON format with timing information
- Tracks operation durations and success rates
- Used for optimization and bottleneck identification
- Rotating file (5MB max, 3 backups)

## Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General informational messages
- **WARNING**: Warning messages (gas high, etc.)
- **ERROR**: Error conditions that don't stop the bot
- **CRITICAL**: Fatal errors that stop execution

## Contextual Information

Each log entry includes relevant context:
- `chain`: Blockchain network
- `target`: Target contract name
- `tx_hash`: Transaction hash
- `gas_price`: Current gas price
- `profit_usd`: Profit in USD
- `error_type`: Category of error
- `duration_ms`: Operation duration

## Viewing Logs

### Real-time Monitoring
```bash
# Tail logs in real-time
./run.sh log-tail

# View last 20 log entries
python -m janitor.log_viewer --tail
```

### Log Analysis
```bash
# Analyze last 24 hours
python -m janitor.log_viewer --hours 24

# View transaction summary
python -m janitor.log_viewer --transactions

# Analyze errors
python -m janitor.log_viewer --errors

# Performance metrics
python -m janitor.log_viewer --performance

# Filter by target
python -m janitor.log_viewer --target "BeefyVault-USDC"

# Filter by log level
python -m janitor.log_viewer --level ERROR
```

### Log Viewer Options
```bash
python -m janitor.log_viewer --help

Options:
  --log-file PATH      Path to log file (default: data/logs/janitor.json)
  --start TIME         Start time (ISO format)
  --end TIME           End time (ISO format)  
  --hours N            Last N hours
  --level LEVEL        Filter by log level
  --target NAME        Filter by target name
  --chain NAME         Filter by chain
  --transactions       Analyze transactions
  --errors            Analyze errors
  --performance       Analyze performance
  --tail              Show last lines
  --follow            Follow mode (like tail -f)
```

## Example Log Entries

### Successful Transaction
```json
{
  "timestamp": "2024-01-15T14:32:45.123456",
  "level": "INFO",
  "logger": "janitor.janitor",
  "message": "BeefyVault-USDC: success! tx=0xabc123..., net=$0.4523",
  "chain": "arbitrum",
  "target": "BeefyVault-USDC",
  "tx_hash": "0xabc123...",
  "profit_usd": 0.4523,
  "gas_used": 250000
}
```

### Error Entry
```json
{
  "timestamp": "2024-01-15T14:35:12.789012",
  "level": "ERROR",
  "logger": "janitor.janitor",
  "message": "Error processing YearnVault-ETH: Gas estimation failed",
  "chain": "arbitrum",
  "target": "YearnVault-ETH",
  "error_type": "gas_estimation",
  "exception": "Traceback (most recent call last)..."
}
```

### Performance Entry
```json
{
  "timestamp": "2024-01-15T14:36:00.000000",
  "level": "DEBUG",
  "logger": "janitor.performance",
  "message": "Performance: read_state",
  "operation": "read_state",
  "duration_ms": 145.23,
  "success": true,
  "target": "GMX-PriceOracle"
}
```

## Log Rotation

- Automatic rotation when files exceed size limits
- Keeps multiple backups with `.1`, `.2` suffix
- Old logs compressed to save space
- Transaction logs never rotate (permanent record)

## Monitoring Best Practices

1. **Daily Review**: Check error logs daily
2. **Performance**: Monitor performance.log for slow operations
3. **Transactions**: Verify all transactions in transactions.log
4. **Alerts**: Set up alerts for ERROR/CRITICAL levels
5. **Archival**: Archive old logs monthly

## Troubleshooting

### Common Issues

1. **No logs appearing**
   - Check log directory permissions
   - Verify LOG_LEVEL in .env
   - Ensure data/logs/ directory exists

2. **Disk space issues**
   - Reduce backup count in logging_config.py
   - Archive old logs
   - Decrease rotation size limits

3. **Performance impact**
   - Increase LOG_LEVEL to INFO or WARNING
   - Disable DEBUG logging in production
   - Use JSON logs only (disable console output)