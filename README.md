# Janitor Bot 🧹

On-chain maintenance bot ("janitor") for Arbitrum (expandable to Base/Polygon).

## Quick Start

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your keys and RPC endpoints
```

3. Run locally:
```bash
python -m janitor.janitor
```

4. Or run with Docker:
```bash
docker compose up -d
```

## Architecture

- **Poll**: Check target contracts every 5 seconds
- **Profit Gate**: Execute only when `reward >= 1.5x gas cost`
- **Execute**: Send transaction with EIP-1559 gas management
- **Log**: SQLite tracking with P&L per target

## Safety

- Allowlisted functions only
- Gas ceiling protection
- Cooldown enforcement
- Circuit breaker on repeated failures
- Separate hot wallet per chain

## Monitoring

- SQLite logs at `data/janitor.db`
- Optional metrics endpoint at `http://localhost:8000/metrics`
- Daily P&L reports via email (if configured)