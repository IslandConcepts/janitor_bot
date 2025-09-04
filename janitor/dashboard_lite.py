#!/usr/bin/env python3

"""
Lightweight alternative dashboard for systems without rich library
"""

import time
import os
import sys
from datetime import datetime, timedelta
from janitor.config import load_config
from janitor.storage import Database
from janitor.rpc import RPCManager, get_base_fee_gwei, get_native_balance
from janitor.utils import format_address

class SimpleDashboard:
    """Simple terminal dashboard without rich dependency"""
    
    def __init__(self):
        self.config = load_config()
        self.db = Database("data/janitor.db")
        self.rpc_manager = RPCManager()
        self.running = True
    
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """Print dashboard header"""
        print("=" * 80)
        print(f"{'JANITOR BOT DASHBOARD':^80}")
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S'):^80}")
        print("=" * 80)
    
    def print_pnl_stats(self):
        """Print P&L statistics"""
        today_pnl = self.db.get_daily_pnl()
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_pnl = self.db.get_daily_pnl(yesterday)
        
        # Calculate week total
        week_total = 0.0
        for i in range(7):
            date = datetime.now() - timedelta(days=i)
            daily = self.db.get_daily_pnl(date)
            week_total += daily.get('total_net_usd', 0.0)
        
        print("\n📊 P&L STATISTICS")
        print("-" * 40)
        print(f"Today Net:        ${today_pnl['total_net_usd']:>8.2f}")
        print(f"Today Runs:       {today_pnl['total_runs']:>10}")
        print(f"Today Failures:   {today_pnl['total_failures']:>10}")
        print(f"Yesterday Net:    ${yesterday_pnl['total_net_usd']:>8.2f}")
        print(f"Week Total:       ${week_total:>8.2f}")
        
        if today_pnl['total_runs'] > 0:
            efficiency = (today_pnl['total_runs'] - today_pnl['total_failures']) / today_pnl['total_runs'] * 100
            print(f"Efficiency:       {efficiency:>9.1f}%")
    
    def print_targets(self):
        """Print target status"""
        print("\n🎯 TARGETS")
        print("-" * 40)
        print(f"{'Target':<20} {'Status':<12} {'Last Call':<12} {'Failures'}")
        print("-" * 40)
        
        with self.db.get_conn() as conn:
            results = conn.execute('''
                SELECT 
                    target,
                    last_call_ts,
                    consecutive_failures,
                    paused_until
                FROM state
                ORDER BY target
            ''').fetchall()
            
            for row in results:
                # Determine status
                if row['paused_until'] and row['paused_until'] > time.time():
                    status = "PAUSED"
                elif row['consecutive_failures'] >= 3:
                    status = "ERROR"
                else:
                    status = "ACTIVE"
                
                # Format last call time
                if row['last_call_ts']:
                    time_ago = int(time.time() - row['last_call_ts'])
                    if time_ago < 60:
                        last_call_str = f"{time_ago}s ago"
                    elif time_ago < 3600:
                        last_call_str = f"{time_ago//60}m ago"
                    else:
                        last_call_str = f"{time_ago//3600}h ago"
                else:
                    last_call_str = "Never"
                
                print(f"{row['target'][:20]:<20} {status:<12} {last_call_str:<12} {row['consecutive_failures']}")
    
    def print_recent_runs(self):
        """Print recent runs"""
        print("\n📜 RECENT RUNS")
        print("-" * 80)
        print(f"{'Time':<10} {'Target':<20} {'Net USD':<12} {'Status':<10} {'TX Hash'}")
        print("-" * 80)
        
        with self.db.get_conn() as conn:
            results = conn.execute('''
                SELECT * FROM runs
                ORDER BY timestamp DESC
                LIMIT 10
            ''').fetchall()
            
            for row in results:
                # Format time
                run_time = datetime.fromtimestamp(row['timestamp'])
                time_str = run_time.strftime('%H:%M:%S')
                
                # Format net USD
                net_str = f"${row['net_usd']:.4f}" if row['net_usd'] else "$0.00"
                
                # Format status
                status = "SUCCESS" if row['status'] == 'success' else "FAILED"
                
                # Format tx hash
                tx_hash = format_address(row['tx_hash']) if row['tx_hash'] else "---"
                
                print(f"{time_str:<10} {row['target'][:20]:<20} {net_str:<12} {status:<10} {tx_hash}")
    
    def print_gas_info(self):
        """Print gas and balance information"""
        print("\n⛽ GAS & BALANCE")
        print("-" * 40)
        
        for chain_name, chain_config in self.config['chains'].items():
            try:
                w3 = self.rpc_manager.get_w3(chain_name, chain_config['rpc'])
                
                # Get gas price
                base_fee = get_base_fee_gwei(w3)
                max_fee = chain_config['maxBaseFeeGwei']
                
                # Get wallet balance
                balance = get_native_balance(w3, chain_config['from'])
                
                print(f"{chain_name}:")
                print(f"  Gas:     {base_fee:.3f} gwei (max: {max_fee} gwei)")
                print(f"  Balance: {balance:.4f} ETH")
                
            except Exception as e:
                print(f"{chain_name}: ERROR")
    
    def print_footer(self):
        """Print footer with instructions"""
        print("\n" + "=" * 80)
        print("Press Ctrl+C to exit | Dashboard refreshes every 5 seconds")
    
    def run(self):
        """Run the dashboard loop"""
        try:
            while self.running:
                self.clear_screen()
                self.print_header()
                self.print_pnl_stats()
                self.print_targets()
                self.print_recent_runs()
                self.print_gas_info()
                self.print_footer()
                
                time.sleep(5)  # Refresh every 5 seconds
                
        except KeyboardInterrupt:
            print("\nDashboard stopped")

def main():
    """Entry point for simple dashboard"""
    dashboard = SimpleDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()