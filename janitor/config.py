import json
import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

def load_config(targets_path: str = "janitor/targets.json") -> Dict[str, Any]:
    """Load and validate configuration from targets.json and environment variables"""
    
    # Load targets configuration
    with open(targets_path, 'r') as f:
        config = json.load(f)
    
    # Merge environment variables
    for chain_name, chain_config in config['chains'].items():
        # Replace env keys with actual values
        if isinstance(chain_config.get('maxBaseFeeGwei'), str):
            chain_config['maxBaseFeeGwei'] = float(os.getenv(chain_config['maxBaseFeeGwei'], 0.2))
        
        chain_config['from'] = os.getenv(chain_config['fromEnvKey'])
        chain_config['privateKey'] = os.getenv(chain_config['pkEnvKey'])
        
        # Replace RPC env keys with actual URLs
        rpcs = []
        for rpc_key in chain_config['rpc']:
            if rpc_url := os.getenv(rpc_key):
                rpcs.append(rpc_url)
        chain_config['rpc'] = rpcs
        
        # Validate required fields
        if not chain_config['from']:
            raise ValueError(f"Missing FROM address for {chain_name}")
        if not chain_config['privateKey']:
            raise ValueError(f"Missing private key for {chain_name}")
        if not rpcs:
            raise ValueError(f"No RPC endpoints configured for {chain_name}")
    
    # Add global config from env
    config['global'] = {
        'env': os.getenv('ENV', 'dev'),
        'logLevel': os.getenv('LOG_LEVEL', 'INFO'),
        'profitMultiplier': float(os.getenv('PROFIT_MULTIPLIER', 1.5)),
        'minNetUSD': float(os.getenv('MIN_NET_USD', 0.02)),
        'maxConsecutiveFailures': int(os.getenv('MAX_CONSECUTIVE_FAILURES', 3)),
        'circuitBreakerMinutes': int(os.getenv('CIRCUIT_BREAKER_MINUTES', 60)),
        'metricsPort': int(os.getenv('METRICS_PORT', 8000)),
        'reportEmail': os.getenv('REPORT_EMAIL'),
        'smtpServer': os.getenv('SMTP_SERVER'),
    }
    
    return config

def validate_target(target: Dict[str, Any]) -> bool:
    """Validate a target configuration"""
    required = ['name', 'address', 'abi', 'type']
    return all(field in target for field in required) and target.get('enabled', True)