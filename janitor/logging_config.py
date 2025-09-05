"""
Comprehensive logging configuration for Janitor Bot
"""

import os
import json
import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

class StructuredFormatter(logging.Formatter):
    """JSON structured logging formatter"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'chain'):
            log_obj['chain'] = record.chain
        if hasattr(record, 'target'):
            log_obj['target'] = record.target
        if hasattr(record, 'tx_hash'):
            log_obj['tx_hash'] = record.tx_hash
        if hasattr(record, 'gas_price'):
            log_obj['gas_price'] = record.gas_price
        if hasattr(record, 'profit_usd'):
            log_obj['profit_usd'] = record.profit_usd
        if hasattr(record, 'error_type'):
            log_obj['error_type'] = record.error_type
        
        # Add exception info if present
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj)

class DetailedFormatter(logging.Formatter):
    """Detailed human-readable formatter with color support"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def __init__(self, use_color: bool = True):
        self.use_color = use_color
        super().__init__()
    
    def format(self, record: logging.LogRecord) -> str:
        # Base format
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        level = record.levelname.ljust(8)
        logger = record.name
        
        # Add color if enabled
        if self.use_color and record.levelname in self.COLORS:
            level = f"{self.COLORS[record.levelname]}{level}{self.COLORS['RESET']}"
        
        # Build message
        msg_parts = [f"[{timestamp}] {level} {logger} - {record.getMessage()}"]
        
        # Add context if available
        context_parts = []
        if hasattr(record, 'chain'):
            context_parts.append(f"chain={record.chain}")
        if hasattr(record, 'target'):
            context_parts.append(f"target={record.target}")
        if hasattr(record, 'tx_hash'):
            context_parts.append(f"tx={record.tx_hash[:10]}...")
        if hasattr(record, 'gas_price'):
            context_parts.append(f"gas={record.gas_price:.3f}gwei")
        if hasattr(record, 'profit_usd'):
            context_parts.append(f"profit=${record.profit_usd:.4f}")
        
        if context_parts:
            msg_parts.append(f"  Context: {' | '.join(context_parts)}")
        
        # Add location info for warnings and errors
        if record.levelno >= logging.WARNING:
            msg_parts.append(f"  Location: {record.pathname}:{record.lineno} in {record.funcName}()")
        
        # Add exception if present
        if record.exc_info:
            msg_parts.append(f"  Exception: {self.formatException(record.exc_info)}")
        
        return '\n'.join(msg_parts)

class JanitorLogger:
    """Enhanced logger with structured logging capabilities"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_done = False
    
    def setup(self, config: Dict[str, Any]):
        """Setup comprehensive logging"""
        if self._setup_done:
            return
        
        # Create logs directory
        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set base level
        log_level = getattr(logging, config.get('logLevel', 'INFO'))
        self.logger.setLevel(log_level)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # 1. Console Handler (human-readable)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_handler.setFormatter(DetailedFormatter(use_color=True))
        self.logger.addHandler(console_handler)
        
        # 2. Main Log File (detailed, rotating)
        main_log_file = log_dir / "janitor.log"
        file_handler = logging.handlers.RotatingFileHandler(
            main_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)  # Always log everything to file
        file_handler.setFormatter(DetailedFormatter(use_color=False))
        self.logger.addHandler(file_handler)
        
        # 3. JSON Structured Log (for parsing/analysis)
        json_log_file = log_dir / "janitor.json"
        json_handler = logging.handlers.RotatingFileHandler(
            json_log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        json_handler.setLevel(logging.DEBUG)
        json_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(json_handler)
        
        # 4. Error Log (errors and above only)
        error_log_file = log_dir / "errors.log"
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(DetailedFormatter(use_color=False))
        self.logger.addHandler(error_handler)
        
        # 5. Transaction Log (specific to successful transactions)
        tx_log_file = log_dir / "transactions.log"
        self.tx_handler = logging.FileHandler(tx_log_file, encoding='utf-8')
        self.tx_handler.setLevel(logging.INFO)
        tx_formatter = logging.Formatter(
            '%(asctime)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.tx_handler.setFormatter(tx_formatter)
        
        # Create transaction logger
        self.tx_logger = logging.getLogger(f"{self.logger.name}.transactions")
        self.tx_logger.setLevel(logging.INFO)
        self.tx_logger.addHandler(self.tx_handler)
        self.tx_logger.propagate = False
        
        # 6. Performance Log (for timing and optimization)
        perf_log_file = log_dir / "performance.log"
        self.perf_handler = logging.handlers.RotatingFileHandler(
            perf_log_file,
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        self.perf_handler.setLevel(logging.DEBUG)
        self.perf_handler.setFormatter(StructuredFormatter())
        
        # Create performance logger
        self.perf_logger = logging.getLogger(f"{self.logger.name}.performance")
        self.perf_logger.setLevel(logging.DEBUG)
        self.perf_logger.addHandler(self.perf_handler)
        self.perf_logger.propagate = False
        
        self._setup_done = True
        self.logger.info("Logging system initialized", extra={
            'log_dir': str(log_dir),
            'log_level': config.get('logLevel', 'INFO'),
            'handlers': ['console', 'main', 'json', 'error', 'transaction', 'performance']
        })
    
    def log_transaction(self, chain: str, target: str, tx_hash: str, 
                       gas_used: int, profit_usd: float, status: str):
        """Log transaction details"""
        msg = f"CHAIN={chain} | TARGET={target} | TX={tx_hash} | GAS={gas_used} | PROFIT=${profit_usd:.4f} | STATUS={status}"
        if hasattr(self, 'tx_logger'):
            self.tx_logger.info(msg)
        else:
            self.logger.info(msg)
        
        # Also log to main logger with context
        self.logger.info(f"Transaction executed: {status}", extra={
            'chain': chain,
            'target': target,
            'tx_hash': tx_hash,
            'gas_used': gas_used,
            'profit_usd': profit_usd
        })
    
    def log_performance(self, operation: str, duration_ms: float, 
                       success: bool, details: Dict[str, Any] = None):
        """Log performance metrics"""
        perf_data = {
            'operation': operation,
            'duration_ms': duration_ms,
            'success': success
        }
        if details:
            perf_data.update(details)
        
        if hasattr(self, 'perf_logger'):
            self.perf_logger.debug(f"Performance: {operation}", extra=perf_data)
        else:
            self.logger.debug(f"Performance: {operation} - {duration_ms:.2f}ms", extra=perf_data)
    
    def debug(self, msg: str, **kwargs):
        self.logger.debug(msg, extra=kwargs)
    
    def info(self, msg: str, **kwargs):
        self.logger.info(msg, extra=kwargs)
    
    def warning(self, msg: str, **kwargs):
        self.logger.warning(msg, extra=kwargs)
    
    def error(self, msg: str, exc_info: bool = False, **kwargs):
        self.logger.error(msg, exc_info=exc_info, extra=kwargs)
    
    def critical(self, msg: str, **kwargs):
        self.logger.critical(msg, extra=kwargs)

# Global logger instance
janitor_logger = JanitorLogger("janitor")

def setup_logging(config: Dict[str, Any]):
    """Initialize the logging system"""
    janitor_logger.setup(config)
    
    # Setup logging for all modules
    loggers_to_setup = [
        "janitor.rpc",
        "janitor.profit",
        "janitor.tx",
        "janitor.storage",
        "janitor.metrics"
    ]
    
    for logger_name in loggers_to_setup:
        logger = JanitorLogger(logger_name)
        logger.setup(config)

def get_logger(name: str) -> JanitorLogger:
    """Get a logger instance"""
    logger = JanitorLogger(name)
    # Note: setup should be called by main application
    return logger