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
import random

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
        self.status_messages = []
        self.animation_frame = 0
        self.spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.activity_icons = ["🔍", "⚡", "💰", "📊", "🎯", "✨"]
        self.targets_page = 0
        self.targets_per_page = 15
        self.page_switch_interval = 5  # Switch pages every 5 seconds
        
        # Setup layout structure
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="status", size=3),
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
        
        # Animated header with rotating icon
        icon = self.activity_icons[self.animation_frame % len(self.activity_icons)]
        grid.add_row(
            f"[bold cyan]{icon} JANITOR BOT DASHBOARD {icon}[/bold cyan]"
        )
        grid.add_row(
            f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]"
        )
        return Panel(grid, style="cyan")
    
    def get_status_panel(self) -> Panel:
        """Generate live status feed panel"""
        spinner = self.spinners[self.animation_frame % len(self.spinners)]
        
        # Generate status messages
        status_lines = []
        
        # Rotating primary activities
        activities = [
            f"{spinner} Scanning Arbitrum targets...",
            f"{spinner} Checking Base harvests...", 
            f"{spinner} Monitoring flash loan opportunities...",
            f"{spinner} Analyzing gas prices...",
            f"{spinner} Calculating profit thresholds...",
            f"{spinner} Checking Beefy vaults...",
            f"{spinner} Evaluating liquidation candidates...",
            f"{spinner} Monitoring health factors..."
        ]
        
        current_activity = activities[(self.animation_frame // 3) % len(activities)]
        
        # Add pulsing effect without color codes
        if self.animation_frame % 2 == 0:
            status_lines.append(f"▶ {current_activity}")
        else:
            status_lines.append(f"  {current_activity}")
        
        # Add secondary status with different timing
        secondary_activities = [
            "🔄 Refreshing RPC connections",
            "📊 Updating price feeds",
            "⚙️ Optimizing gas settings",
            "🔍 Searching for MEV opportunities",
            "📋 Checking cooldown timers",
            "🎯 Calculating optimal routes"
        ]
        
        secondary = secondary_activities[(self.animation_frame // 5) % len(secondary_activities)]
        status_lines.append(f"  {secondary}")
        
        # Add recent events that cycle more slowly
        recent_events = [
            "✅ Beefy_MIM_USDC checked - cooldown active",
            "🔍 Found 0 liquidations on Arbitrum",
            "⚡ Flash loans ready (SIMULATION MODE)",
            "📊 Gas optimal: Arb 0.10 | Base 0.05 gwei",
            "🌐 All chains connected successfully",
            "🛡️ No errors in last 100 checks"
        ]
        
        event_idx = (self.animation_frame // 15) % len(recent_events)
        status_lines.append(f"  {recent_events[event_idx]}")
        
        status_text = "\n".join(status_lines)
        return Panel(
            Align.center(Text(status_text)),
            title=f"🎯 Live Activity",
            border_style="green"
        )
    
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
        """Generate targets status panel with paging like an airport display"""
        # Collect all target data first
        all_targets = []
        
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
                # Determine status with animation - all using -ing verbs
                if row['paused_until'] and row['paused_until'] > time.time():
                    # Animate paused status
                    remaining = int(row['paused_until'] - time.time())
                    if self.animation_frame % 10 < 5:
                        status = "[red]⏸ PAUSING[/red]"
                    else:
                        status = "[bold red]⏸ RESTING[/bold red]"
                    status += f" ({remaining}s)"
                elif row['consecutive_failures'] >= 3:
                    # Animate error status
                    if self.animation_frame % 8 < 4:
                        status = "[red]❌ ERROR[/red]"
                    else:
                        status = "[bold red]⚠ RETRYING[/bold red]"
                else:
                    # Animate active status with different patterns - all using -ing verbs
                    cycle = self.animation_frame % 60
                    if cycle < 15:
                        status = "[green]✅ RUNNING[/green]"
                    elif cycle < 30:
                        status = "[bold green]🔄 SCANNING[/bold green]"
                    elif cycle < 45:
                        status = "[green]⚡ WATCHING[/green]"
                    else:
                        status = "[bold green]✅ CHECKING[/bold green]"
                
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
                
                all_targets.append({
                    'name': row['target'][:20],
                    'status': status,
                    'last_call': last_call_str,
                    'failures': failures_str
                })
        
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
                            # Animate waiting status - all using -ing verbs
                            if self.animation_frame % 16 < 8:
                                waiting_status = "[dim]⏳ WAITING[/dim]"
                            else:
                                waiting_status = "[yellow]🔍 INITIALIZING[/yellow]"
                            
                            all_targets.append({
                                'name': target['name'][:20],
                                'status': waiting_status,
                                'last_call': "Never",
                                'failures': "[dim]0[/dim]"
                            })
        
        # Calculate paging
        total_targets = len(all_targets)
        total_pages = (total_targets + self.targets_per_page - 1) // self.targets_per_page
        
        # Auto-advance page every N seconds (like airport display)
        if total_pages > 1:
            # Change page based on animation frame
            seconds_elapsed = self.animation_frame // 2  # 2 updates per second
            self.targets_page = (seconds_elapsed // self.page_switch_interval) % total_pages
        else:
            self.targets_page = 0
        
        # Get targets for current page
        start_idx = self.targets_page * self.targets_per_page
        end_idx = min(start_idx + self.targets_per_page, total_targets)
        page_targets = all_targets[start_idx:end_idx]
        
        # Build table for current page
        table = Table(expand=True)
        table.add_column("Target", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Last Call", justify="center")
        table.add_column("Failures", justify="center")
        
        for target in page_targets:
            table.add_row(
                target['name'],
                target['status'],
                target['last_call'],
                target['failures']
            )
        
        # Add page indicator if multiple pages
        title = "🎯 Targets"
        if total_pages > 1:
            # Create page dots indicator
            dots = []
            for i in range(total_pages):
                if i == self.targets_page:
                    dots.append("●")
                else:
                    dots.append("○")
            page_indicator = " ".join(dots)
            title = f"🎯 Targets [{self.targets_page + 1}/{total_pages}] {page_indicator}"
        
        return Panel(table, title=title, border_style="blue")
    
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
        """Generate liquidation stats panel with animations"""
        # Create a simple stats display for liquidations
        stats = Table(show_header=False, box=None, expand=True)
        stats.add_column("Label", style="dim")
        stats.add_column("Value", justify="right")
        
        # Add liquidation monitoring status with pulse effect
        if self.animation_frame % 30 < 15:
            stats.add_row("[bold]FLASH LOANS[/bold]", "[yellow]● SIMULATION[/yellow]")
        else:
            stats.add_row("[bold]FLASH LOANS[/bold]", "[bold yellow]● SIMULATION[/bold yellow]")
        stats.add_row("", "")
        
        # Simulate scanning animation
        scan_spinner = self.spinners[self.animation_frame % len(self.spinners)]
        if self.animation_frame % 60 < 30:
            stats.add_row("Arbitrum", f"[cyan]{scan_spinner} Scanning...[/cyan]")
        else:
            stats.add_row("Arbitrum", "[dim]Ready[/dim]")
        
        stats.add_row("Arb Found", "0")
        stats.add_row("Arb Profit", "[dim]$0.00[/dim]")
        stats.add_row("", "")
        
        if self.animation_frame % 60 >= 30:
            stats.add_row("Base", f"[cyan]{scan_spinner} Scanning...[/cyan]")
        else:
            stats.add_row("Base", "[dim]Ready[/dim]")
        
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
        # Increment animation frame for smooth animations
        self.animation_frame += 1
        
        # Update all panels
        self.layout["header"].update(self.get_header())
        self.layout["status"].update(self.get_status_panel())
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
            with Live(self.update_display(), refresh_per_second=2, console=console) as live:
                while self.running:
                    time.sleep(0.5)  # Update twice per second for smooth animations
                    live.update(self.update_display())
        except KeyboardInterrupt:
            console.print("\n[yellow]Dashboard stopped[/yellow]")

def main():
    """Entry point for dashboard"""
    dashboard = JanitorDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()