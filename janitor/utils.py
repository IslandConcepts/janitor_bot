import time
import logging
from typing import Any, Callable
from functools import wraps

logger = logging.getLogger(__name__)

def setup_logging(level: str = "INFO"):
    """Configure logging for the janitor bot"""
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('data/janitor.log')
        ]
    )

def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0
):
    """Decorator for retrying functions with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(f"All {max_retries} attempts failed")
            
            raise last_exception
        return wrapper
    return decorator

def format_wei_to_ether(wei: int) -> float:
    """Convert Wei to Ether"""
    return wei / 1e18

def format_ether_to_wei(ether: float) -> int:
    """Convert Ether to Wei"""
    return int(ether * 1e18)

def format_gwei_to_wei(gwei: float) -> int:
    """Convert Gwei to Wei"""
    return int(gwei * 1e9)

def format_address(address: str) -> str:
    """Format address for display (shortened)"""
    if not address:
        return "0x0000"
    return f"{address[:6]}...{address[-4:]}"

def calculate_time_until(target_timestamp: int) -> int:
    """Calculate seconds until target timestamp"""
    now = int(time.time())
    return max(0, target_timestamp - now)

def is_address(value: str) -> bool:
    """Check if string is valid Ethereum address"""
    if not value:
        return False
    if not value.startswith('0x'):
        return False
    if len(value) != 42:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False

def safe_get_nested(data: dict, *keys: str, default: Any = None) -> Any:
    """Safely get nested dictionary value"""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key)
        else:
            return default
    return data if data is not None else default