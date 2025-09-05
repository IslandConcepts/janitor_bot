import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class Database:
    """SQLite database for janitor bot tracking"""
    
    def __init__(self, db_path: str = "data/janitor.db"):
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_conn(self):
        """Get database connection context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_db(self):
        """Initialize database tables"""
        with self.get_conn() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    chain TEXT NOT NULL,
                    target TEXT NOT NULL,
                    action TEXT NOT NULL,
                    tx_hash TEXT,
                    gas_used INTEGER,
                    gas_cost_usd REAL,
                    reward_tokens REAL,
                    reward_usd REAL,
                    net_usd REAL,
                    status TEXT NOT NULL,
                    reason TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS state (
                    target TEXT PRIMARY KEY,
                    last_call_ts INTEGER,
                    last_tx_hash TEXT,
                    consecutive_failures INTEGER DEFAULT 0,
                    paused_until INTEGER
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS failures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    chain TEXT NOT NULL,
                    target TEXT NOT NULL,
                    error TEXT NOT NULL,
                    detail TEXT
                )
            ''')
            
            # Create profit reconciliation table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS profit_reconciliation (
                    tx_hash TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    estimated_reward_usd REAL,
                    estimated_gas_usd REAL,
                    estimated_net_usd REAL,
                    actual_reward_usd REAL,
                    actual_gas_usd REAL,
                    actual_net_usd REAL,
                    variance_reward_usd REAL,
                    variance_gas_usd REAL,
                    variance_net_usd REAL,
                    variance_reward_pct REAL,
                    variance_gas_pct REAL,
                    actual_rewards_json TEXT
                )
            ''')
            
            # Create indexes
            conn.execute('CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON runs(timestamp)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_runs_target ON runs(target)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_failures_target ON failures(target)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_recon_timestamp ON profit_reconciliation(timestamp)')
    
    def log_run(
        self,
        chain: str,
        target: str,
        action: str,
        tx_hash: Optional[str] = None,
        gas_used: int = 0,
        gas_cost_usd: float = 0.0,
        reward_usd: float = 0.0,
        net_usd: float = 0.0,
        status: str = 'pending',
        reason: str = ''
    ):
        """Log a janitor run"""
        with self.get_conn() as conn:
            conn.execute('''
                INSERT INTO runs (
                    timestamp, chain, target, action, tx_hash,
                    gas_used, gas_cost_usd, reward_tokens, reward_usd,
                    net_usd, status, reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                int(datetime.now().timestamp()),
                chain, target, action, tx_hash,
                gas_used, gas_cost_usd, 0, reward_usd,
                net_usd, status, reason
            ))
    
    def log_failure(self, chain: str, target: str, error: str, detail: str = ''):
        """Log a failure"""
        with self.get_conn() as conn:
            # Log to failures table
            conn.execute('''
                INSERT INTO failures (timestamp, chain, target, error, detail)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                int(datetime.now().timestamp()),
                chain, target, error, detail
            ))
            
            # Update consecutive failures in state
            conn.execute('''
                INSERT INTO state (target, consecutive_failures)
                VALUES (?, 1)
                ON CONFLICT(target) DO UPDATE SET
                    consecutive_failures = consecutive_failures + 1
            ''', (target,))
    
    def get_last_call_ts(self, target: str) -> Optional[int]:
        """Get timestamp of last successful call for target"""
        with self.get_conn() as conn:
            result = conn.execute(
                'SELECT last_call_ts FROM state WHERE target = ?',
                (target,)
            ).fetchone()
            return result['last_call_ts'] if result else None
    
    def update_state(self, target: str, timestamp: int, tx_hash: str):
        """Update state after successful call"""
        with self.get_conn() as conn:
            conn.execute('''
                INSERT INTO state (target, last_call_ts, last_tx_hash, consecutive_failures)
                VALUES (?, ?, ?, 0)
                ON CONFLICT(target) DO UPDATE SET
                    last_call_ts = excluded.last_call_ts,
                    last_tx_hash = excluded.last_tx_hash,
                    consecutive_failures = 0
            ''', (target, timestamp, tx_hash))
    
    def recent_failures(self, target: str, minutes: int = 60) -> int:
        """Count recent failures for a target"""
        with self.get_conn() as conn:
            cutoff = int((datetime.now() - timedelta(minutes=minutes)).timestamp())
            result = conn.execute('''
                SELECT COUNT(*) as count FROM failures
                WHERE target = ? AND timestamp > ?
            ''', (target, cutoff)).fetchone()
            return result['count'] if result else 0
    
    def get_consecutive_failures(self, target: str) -> int:
        """Get consecutive failure count for target"""
        with self.get_conn() as conn:
            result = conn.execute(
                'SELECT consecutive_failures FROM state WHERE target = ?',
                (target,)
            ).fetchone()
            return result['consecutive_failures'] if result else 0
    
    def pause_target(self, target: str, minutes: int):
        """Pause a target for specified minutes"""
        paused_until = int((datetime.now() + timedelta(minutes=minutes)).timestamp())
        with self.get_conn() as conn:
            conn.execute('''
                INSERT INTO state (target, paused_until)
                VALUES (?, ?)
                ON CONFLICT(target) DO UPDATE SET
                    paused_until = excluded.paused_until
            ''', (target, paused_until))
        logger.warning(f"Paused {target} for {minutes} minutes")
    
    def is_paused(self, target: str) -> bool:
        """Check if target is currently paused"""
        with self.get_conn() as conn:
            result = conn.execute(
                'SELECT paused_until FROM state WHERE target = ?',
                (target,)
            ).fetchone()
            if result and result['paused_until']:
                return result['paused_until'] > int(datetime.now().timestamp())
            return False
    
    def get_daily_pnl(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get daily P&L summary"""
        if date is None:
            date = datetime.now()
        
        start = int(datetime(date.year, date.month, date.day).timestamp())
        end = start + 86400
        
        with self.get_conn() as conn:
            # Get successful runs
            runs = conn.execute('''
                SELECT 
                    target,
                    COUNT(*) as count,
                    SUM(gas_cost_usd) as total_gas,
                    SUM(reward_usd) as total_reward,
                    SUM(net_usd) as total_net
                FROM runs
                WHERE timestamp >= ? AND timestamp < ?
                    AND status = 'success'
                GROUP BY target
            ''', (start, end)).fetchall()
            
            # Get failure count
            failures = conn.execute('''
                SELECT COUNT(*) as count
                FROM failures
                WHERE timestamp >= ? AND timestamp < ?
            ''', (start, end)).fetchone()
            
            return {
                'date': date.strftime('%Y-%m-%d'),
                'targets': [dict(r) for r in runs],
                'total_runs': sum(r['count'] for r in runs),
                'total_failures': failures['count'] if failures else 0,
                'total_gas_usd': sum(r['total_gas'] for r in runs if r['total_gas']),
                'total_reward_usd': sum(r['total_reward'] for r in runs if r['total_reward']),
                'total_net_usd': sum(r['total_net'] for r in runs if r['total_net'])
            }