#!/usr/bin/env python3

import time
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any
from rich.console import Console
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

from janitor.config import load_config
from janitor.storage import Database
from janitor.rpc import RPCManager, get_base_fee_gwei, get_native_balance
from janitor.utils import format_address

console = Console()

class JanitorDashboard:
    """Terminal dashboard for janitor bot monitoring"""
    
    def __init__(self):
        self.config = load_config()
        self.db = Database("data/janitor.db")
        self.rpc_manager = RPCManager()
        self.layout = Layout()
        self.running = True
        
        # Setup layout structure
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=4)
        )
        
        self.layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        self.layout["left"].split_column(
            Layout(name="stats", size=18),
            Layout(name="liquidations", size=12),
            Layout(name="targets")
        )
        
        self.layout["right"].split_column(
            Layout(name="recent_runs", size=20),
            Layout(name="gas_info", size=8)
        )
    
    def get_header(self) -> Panel:
        """Generate header panel"""
        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        grid.add_row(
            "[bold cyan]🤖 JANITOR BOT DASHBOARD[/bold cyan]"
        )
        grid.add_row(
            f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]"
        )
        return Panel(grid, style="cyan")
    
    def get_stats_panel(self) -> Panel:
        """Generate P&L statistics panel"""
        # Get total P&L
        total_pnl = self.db.get_total_pnl()
        
        # Get daily P&L
        today_pnl = self.db.get_daily_pnl()
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_pnl = self.db.get_daily_pnl(yesterday)
        
        # Calculate week total
        week_total = 0.0
        for i in range(7):
            date = datetime.now() - timedelta(days=i)
            daily = self.db.get_daily_pnl(date)
            week_total += daily.get('total_net_usd', 0.0)
        
        # Create stats table
        stats = Table(show_header=False, box=None, expand=True)
        stats.add_column("Label", style="dim")
        stats.add_column("Value", justify="right")
        
        # Total lifetime stats
        total_net = total_pnl.get('total_net_usd', 0.0)
        total_color = "green" if total_net > 0 else "red"
        stats.add_row("[bold]TOTAL P&L[/bold]", f"[bold {total_color}]${total_net:.2f}[/bold {total_color}]")
        stats.add_row("Total Runs", f"[cyan]{total_pnl.get('total_runs', 0)}[/cyan]")
        stats.add_row("Days Active", f"{total_pnl.get('days_active', 0)}")
        stats.add_row("Avg Daily", f"${total_pnl.get('avg_daily_profit', 0.0):.2f}")
        stats.add_row("", "")
        
        # Today's stats
        net_color = "green" if today_pnl['total_net_usd'] > 0 else "red"
        stats.add_row("Today Net", f"[{net_color}]${today_pnl['total_net_usd']:.2f}[/{net_color}]")
        stats.add_row("Today Runs", f"[cyan]{today_pnl['total_runs']}[/cyan]")
        stats.add_row("Today Failures", f"[yellow]{today_pnl['total_failures']}[/yellow]")
        stats.add_row("", "")
        
        # Yesterday's stats
        stats.add_row("Yesterday Net", f"${yesterday_pnl['total_net_usd']:.2f}")
        stats.add_row("Yesterday Runs", str(yesterday_pnl['total_runs']))
        stats.add_row("", "")
        
        # Week stats
        week_color = "green" if week_total > 0 else "red"
        stats.add_row("Week Total", f"[bold {week_color}]${week_total:.2f}[/bold {week_color}]")
        
        # Add efficiency metric
        if today_pnl['total_runs'] > 0:
            efficiency = (today_pnl['total_runs'] - today_pnl['total_failures']) / today_pnl['total_runs'] * 100
            stats.add_row("Efficiency", f"{efficiency:.1f}%")
        
        return Panel(stats, title="📊 P&L Statistics", border_style="green")
    
    def get_targets_panel(self) -> Panel:
        """Generate targets status panel"""
        table = Table(expand=True)
        table.add_column("Target", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Last Call", justify="center")
        table.add_column("Failures", justify="center")
        
        # Get target states from database
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
                    status = "[red]⏸ PAUSED[/red]"
                    remaining = int(row['paused_until'] - time.time())
                    status += f" ({remaining}s)"
                elif row['consecutive_failures'] >= 3:
                    status = "[red]❌ ERROR[/red]"
                else:
                    status = "[green]✅ ACTIVE[/green]"
                
                # Format last call time
                if row['last_call_ts']:
                    last_call = datetime.fromtimestamp(row['last_call_ts'])
                    time_ago = int(time.time() - row['last_call_ts'])
                    if time_ago < 60:
                        last_call_str = f"{time_ago}s ago"
                    elif time_ago < 3600:
                        last_call_str = f"{time_ago//60}m ago"
                    else:
                        last_call_str = f"{time_ago//3600}h ago"
                else:
                    last_call_str = "Never"
                
                # Failures color
                failures = row['consecutive_failures']
                if failures == 0:
                    failures_str = "[green]0[/green]"
                elif failures < 3:
                    failures_str = f"[yellow]{failures}[/yellow]"
                else:
                    failures_str = f"[red]{failures}[/red]"
                
                table.add_row(
                    row['target'][:20],
                    status,
                    last_call_str,
                    failures_str
                )
        
        # Add configured but not yet run targets
        for chain_name, chain_config in self.config['chains'].items():
            for target in chain_config.get('targets', []):
                if target.get('enabled', True):
                    # Check if this target is in the database
                    with self.db.get_conn() as conn:
                        exists = conn.execute(
                            'SELECT 1 FROM state WHERE target = ?',
                            (target['name'],)
                        ).fetchone()
                        
                        if not exists:
                            table.add_row(
                                target['name'][:20],
                                "[dim]⏳ WAITING[/dim]",
                                "Never",
                                "[dim]0[/dim]"
                            )
        
        return Panel(table, title="🎯 Targets", border_style="blue")
    
    def get_recent_runs_panel(self) -> Panel:
        """Generate recent runs panel"""
        table = Table(expand=True)
        table.add_column("Time", style="dim", width=8)
        table.add_column("Target", style="cyan", no_wrap=True)
        table.add_column("Net USD", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("TX Hash", style="dim", no_wrap=True)
        
        # Get recent runs
        with self.db.get_conn() as conn:
            results = conn.execute('''
                SELECT * FROM runs
                ORDER BY timestamp DESC
                LIMIT 15
            ''').fetchall()
            
            for row in results:
                # Format time
                run_time = datetime.fromtimestamp(row['timestamp'])
                time_str = run_time.strftime('%H:%M:%S')
                
                # Format net USD with color
                if row['net_usd']:
                    net_color = "green" if row['net_usd'] > 0 else "red"
                    net_str = f"[{net_color}]${row['net_usd']:.4f}[/{net_color}]"
                else:
                    net_str = "[dim]$0.00[/dim]"
                
                # Format status
                if row['status'] == 'success':
                    status = "[green]✓[/green]"
                elif row['status'] == 'failed':
                    status = "[red]✗[/red]"
                else:
                    status = "[yellow]⋯[/yellow]"
                
                # Format tx hash
                tx_hash = format_address(row['tx_hash']) if row['tx_hash'] else "[dim]---[/dim]"
                
                table.add_row(
                    time_str,
                    row['target'][:15],
                    net_str,
                    status,
                    tx_hash
                )
        
        return Panel(table, title="📜 Recent Runs", border_style="yellow")
    
    def get_liquidation_panel(self) -> Panel:
        """Generate liquidation stats panel"""
        # Create a simple stats display for liquidations
        stats = Table(show_header=False, box=None, expand=True)
        stats.add_column("Label", style="dim")
        stats.add_column("Value", justify="right")
        
        # Add liquidation monitoring status
        stats.add_row("[bold]FLASH LOANS[/bold]", "[yellow]SIMULATION[/yellow]")
        stats.add_row("", "")
        
        # Arbitrum stats
        stats.add_row("Arbitrum Checks", "0")
        stats.add_row("Arbitrum Found", "0")
        stats.add_row("Arbitrum Profit", "[dim]$0.00[/dim]")
        stats.add_row("", "")
        
        # Base stats
        stats.add_row("Base Checks", "0")
        stats.add_row("Base Found", "0")
        stats.add_row("Base Profit", "[dim]$0.00[/dim]")
        stats.add_row("", "")
        
        # Total
        stats.add_row("[bold]Total Profit[/bold]", "[bold green]$0.00[/bold green]")
        
        return Panel(stats, title="⚡ Liquidation Monitor", border_style="magenta")
    
    def get_gas_panel(self) -> Panel:
        """Generate gas and balance info panel"""
        table = Table(show_header=False, box=None, expand=True)
        table.add_column("Label", style="dim")
        table.add_column("Value", justify="right")
        
        for chain_name, chain_config in self.config['chains'].items():
            try:
                w3 = self.rpc_manager.get_w3(chain_name, chain_config['rpc'])
                
                # Get gas price
                base_fee = get_base_fee_gwei(w3)
                max_fee = chain_config['maxBaseFeeGwei']
                
                # Color code gas price
                if base_fee > max_fee:
                    gas_color = "red"
                    gas_str = f"[{gas_color}]{base_fee:.3f} gwei ⚠[/{gas_color}]"
                elif base_fee > max_fee * 0.8:
                    gas_color = "yellow"
                    gas_str = f"[{gas_color}]{base_fee:.3f} gwei[/{gas_color}]"
                else:
                    gas_color = "green"
                    gas_str = f"[{gas_color}]{base_fee:.3f} gwei[/{gas_color}]"
                
                # Get wallet balance
                balance = get_native_balance(w3, chain_config['from'])
                
                # Color code balance
                if balance < 0.01:
                    bal_color = "red"
                elif balance < 0.05:
                    bal_color = "yellow"
                else:
                    bal_color = "green"
                
                bal_str = f"[{bal_color}]{balance:.4f} ETH[/{bal_color}]"
                
                table.add_row(f"{chain_name} Gas", gas_str)
                table.add_row(f"{chain_name} Balance", bal_str)
                table.add_row("", "")
                
            except Exception as e:
                table.add_row(f"{chain_name} Gas", "[red]ERROR[/red]")
                table.add_row(f"{chain_name} Balance", "[red]---[/red]")
                table.add_row("", "")
        
        return Panel(table, title="⛽ Gas & Balance", border_style="magenta")
    
    def get_footer(self) -> Panel:
        """Generate footer panel with help text"""
        help_text = Table.grid(expand=True)
        help_text.add_column()
        
        shortcuts = [
            "[bold]q[/bold] Quit",
            "[bold]r[/bold] Refresh",
            "[bold]p[/bold] Pause/Resume",
            "[bold]l[/bold] View Logs",
            "[bold]?[/bold] Help"
        ]
        
        help_text.add_row(
            " | ".join(shortcuts)
        )
        
        return Panel(
            Align.center(help_text),
            style="dim",
            border_style="dim"
        )
    
    def update_display(self) -> Layout:
        """Update all dashboard panels"""
        self.layout["header"].update(self.get_header())
        self.layout["stats"].update(self.get_stats_panel())
        self.layout["liquidations"].update(self.get_liquidation_panel())
        self.layout["targets"].update(self.get_targets_panel())
        self.layout["recent_runs"].update(self.get_recent_runs_panel())
        self.layout["gas_info"].update(self.get_gas_panel())
        self.layout["footer"].update(self.get_footer())
        
        return self.layout
    
    def run(self):
        """Run the dashboard"""
        try:
            with Live(self.update_display(), refresh_per_second=1, console=console) as live:
                while self.running:
                    time.sleep(1)
                    live.update(self.update_display())
        except KeyboardInterrupt:
            console.print("\n[yellow]Dashboard stopped[/yellow]")

def main():
    """Entry point for dashboard"""
    dashboard = JanitorDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()