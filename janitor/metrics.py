import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from janitor.storage import Database

logger = logging.getLogger(__name__)

app = FastAPI(title="Janitor Bot Metrics")

db = Database("data/janitor.db")

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/metrics")
async def metrics():
    """Get current metrics"""
    try:
        # Get today's P&L
        today_pnl = db.get_daily_pnl()
        
        # Get yesterday's P&L
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_pnl = db.get_daily_pnl(yesterday)
        
        # Get week P&L
        week_total = 0.0
        for i in range(7):
            date = datetime.now() - timedelta(days=i)
            daily = db.get_daily_pnl(date)
            week_total += daily.get('total_net_usd', 0.0)
        
        metrics = {
            "today": {
                "net_usd": today_pnl['total_net_usd'],
                "runs": today_pnl['total_runs'],
                "failures": today_pnl['total_failures'],
                "gas_usd": today_pnl['total_gas_usd'],
                "reward_usd": today_pnl['total_reward_usd']
            },
            "yesterday": {
                "net_usd": yesterday_pnl['total_net_usd'],
                "runs": yesterday_pnl['total_runs'],
                "failures": yesterday_pnl['total_failures']
            },
            "week": {
                "net_usd": week_total
            },
            "targets": today_pnl.get('targets', [])
        }
        
        return JSONResponse(content=metrics)
    
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/targets")
async def targets():
    """Get target status"""
    try:
        with db.get_conn() as conn:
            results = conn.execute('''
                SELECT 
                    target,
                    last_call_ts,
                    consecutive_failures,
                    paused_until
                FROM state
            ''').fetchall()
            
            targets = []
            for row in results:
                status = "active"
                if row['paused_until'] and row['paused_until'] > datetime.now().timestamp():
                    status = "paused"
                elif row['consecutive_failures'] >= 3:
                    status = "error"
                
                targets.append({
                    "name": row['target'],
                    "status": status,
                    "last_call": datetime.fromtimestamp(row['last_call_ts']).isoformat() if row['last_call_ts'] else None,
                    "failures": row['consecutive_failures']
                })
            
            return JSONResponse(content={"targets": targets})
    
    except Exception as e:
        logger.error(f"Targets error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/recent_runs")
async def recent_runs(limit: int = 50):
    """Get recent runs"""
    try:
        with db.get_conn() as conn:
            results = conn.execute('''
                SELECT * FROM runs
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,)).fetchall()
            
            runs = []
            for row in results:
                runs.append({
                    "timestamp": datetime.fromtimestamp(row['timestamp']).isoformat(),
                    "chain": row['chain'],
                    "target": row['target'],
                    "action": row['action'],
                    "tx_hash": row['tx_hash'],
                    "net_usd": row['net_usd'],
                    "status": row['status']
                })
            
            return JSONResponse(content={"runs": runs})
    
    except Exception as e:
        logger.error(f"Recent runs error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

def start_metrics_server(port: int = 8000):
    """Start the metrics HTTP server"""
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")

if __name__ == "__main__":
    start_metrics_server()