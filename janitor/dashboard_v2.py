#!/usr/bin/env python3
"""
Enhanced Dashboard with Live Animations
"""

import time
import sys
import random
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

from janitor.config import load_config
from janitor.storage import Database
from janitor.rpc import RPCManager, get_base_fee_gwei, get_native_balance
from janitor.utils import format_address

console = Console()

class AnimatedDashboard:
    """Enhanced dashboard with animations and live status"""
    
    def __init__(self):
        self.config = load_config()
        self.db = Database("data/janitor.db")
        self.rpc_manager = RPCManager()
        self.layout = Layout()
        self.running = True
        
        # Animation state
        self.frame = 0
        self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.pulse_frames = ["●", "◉", "◎", "○", "◎", "◉"]
        
        # Status rotation
        self.status_idx = 0
        self.status_messages = [
            ("🔍", "Scanning for harvest opportunities"),
            ("📡", "Checking vault cooldowns"),
            ("⛽", "Monitoring gas prices"),
            ("🎯", "Evaluating profit targets"),
            ("💰", "Calculating expected rewards"),
            ("🔄", "Polling strategy contracts"),
            ("📊", "Analyzing vault TVL"),
            ("⏰", "Tracking harvest timers"),
            ("🌊", "Watching mempool activity"),
            ("🛡️", "Verifying safety checks")
        ]
        
        # Activity log
        self.activities = []
        self.max_activities = 6
        
        # Simulated events (replace with real data)
        self.last_event_time = time.time()
        
        # Setup layout
        self.layout.split_column(
            Layout(name="header", size=5),
            Layout(name="activity", size=4),
            Layout(name="body"),
            Layout(name="footer", size=4)
        )
        
        self.layout["body"].split_row(
            Layout(name="left", ratio=3),
            Layout(name="right", ratio=2)
        )
        
        self.layout["left"].split_column(
            Layout(name="stats", size=10),
            Layout(name="targets")
        )
        
        self.layout["right"].split_column(
            Layout(name="recent_runs"),
            Layout(name="gas_info", size=8)
        )
    
    def get_header(self) -> Panel:
        """Animated header with connection status"""
        spinner = self.spinner_frames[self.frame % len(self.spinner_frames)]
        pulse = self.pulse_frames[(self.frame // 3) % len(self.pulse_frames)]
        
        # Connection heartbeat
        if self.frame % 20 < 10:
            conn_status = f"[green]{pulse} CONNECTED[/green]"
        else:
            conn_status = f"[green]○ CONNECTED[/green]"
        
        # Build header
        header_text = Text()
        header_text.append(f"🧹 JANITOR BOT ", style="bold cyan")
        header_text.append(f"{spinner}\n", style="cyan")
        header_text.append(f"Harvesting Beefy Vaults on Arbitrum  ", style="yellow")
        header_text.append(f"{conn_status}\n", style="")
        
        # Add chain info
        header_text.append(f"⛓️ Arbitrum | ", style="dim")
        header_text.append(f"Block: {self.get_block_number()} | ", style="dim")
        header_text.append(datetime.now().strftime('%H:%M:%S'), style="dim")
        
        return Panel(
            Align.center(header_text),
            border_style="cyan",
            padding=(0, 1)
        )
    
    def get_activity_panel(self) -> Panel:
        """Live activity feed with current action"""
        # Rotate status every 2 seconds
        if self.frame % 20 == 0:
            self.status_idx = (self.status_idx + 1) % len(self.status_messages)
        
        icon, message = self.status_messages[self.status_idx]
        
        # Animated dots
        dots = "." * ((self.frame // 5) % 4)
        
        activity_text = Text()
        
        # Current action
        activity_text.append(f"{icon} ", style="bright_yellow")
        activity_text.append(f"{message}{dots}\n", style="yellow")
        
        # Activity history
        if self.activities:
            activity_text.append("\n", style="")
            for activity in self.activities[-3:]:
                activity_text.append(f"  {activity}\n", style="dim white")
        
        return Panel(
            activity_text,
            title=f"[bold]⚡ Live Activity [dim]({len(self.activities)} events)[/dim][/bold]",
            border_style="yellow",
            padding=(0, 1)
        )
    
    def get_stats_panel(self) -> Panel:
        """P&L statistics with animations"""
        today_pnl = self.db.get_daily_pnl()
        yesterday = datetime.now() - timedelta(days=1)
        yesterday_pnl = self.db.get_daily_pnl(yesterday)
        
        # Calculate week P&L from daily totals
        week_total = 0.0
        week_gas = 0.0
        week_harvests = 0
        for i in range(7):
            day = datetime.now() - timedelta(days=i)
            day_pnl = self.db.get_daily_pnl(day)
            week_total += day_pnl.get('total_net_usd', 0) or 0
            week_gas += day_pnl.get('total_gas_usd', 0) or 0
            week_harvests += day_pnl.get('total_runs', 0) or 0
        
        table = Table.grid(padding=1, expand=True)
        table.add_column(style="dim", width=15)
        table.add_column(justify="right")
        
        # Animate positive values
        today_net = today_pnl.get('total_net_usd', 0) or 0
        pulse = self.pulse_frames[(self.frame // 5) % len(self.pulse_frames)] if today_net > 0 else "•"
        
        table.add_row("Today's P&L:", f"[green]${today_net:.4f}[/green] {pulse}")
        table.add_row("Gas Spent:", f"[yellow]${today_pnl.get('total_gas_usd', 0) or 0:.4f}[/yellow]")
        table.add_row("Harvests:", f"[cyan]{today_pnl.get('total_runs', 0) or 0}[/cyan]")
        table.add_row("")
        table.add_row("Yesterday:", f"${yesterday_pnl.get('total_net_usd', 0) or 0:.4f}")
        table.add_row("This Week:", f"[bold]${week_total:.4f}[/bold]")
        
        return Panel(table, title="💰 P&L Statistics", border_style="green")
    
    def get_targets_panel(self) -> Panel:
        """Target vaults with cooldown animations"""
        table = Table(expand=True)
        table.add_column("Vault", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("Cooldown", style="dim")
        table.add_column("Ready", justify="center")
        
        # Get targets from config
        for chain_name, chain_config in self.config['chains'].items():
            for target in chain_config.get('targets', []):
                if not target.get('enabled', False):
                    continue
                
                # Simulate cooldown (replace with real data)
                name = target['name'][:15]
                
                # Check database for last harvest
                with self.db.get_conn() as conn:
                    last_run = conn.execute(
                        'SELECT * FROM runs WHERE target = ? ORDER BY timestamp DESC LIMIT 1',
                        (target['name'],)
                    ).fetchone()
                
                if last_run:
                    time_since = time.time() - last_run['timestamp']
                    cooldown = target.get('cooldownSec', 43200)
                    remaining = max(0, cooldown - time_since)
                    
                    if remaining == 0:
                        status = "[green]✅ ACTIVE[/green]"
                        cooldown_str = "[green]Ready![/green]"
                        ready = "🟢"
                    else:
                        status = "[yellow]⏰ WAITING[/yellow]"
                        hours = int(remaining / 3600)
                        mins = int((remaining % 3600) / 60)
                        cooldown_str = f"{hours}h {mins}m"
                        ready = "🟡"
                else:
                    status = "[dim]💤 IDLE[/dim]"
                    cooldown_str = "[dim]Never run[/dim]"
                    ready = "⚪"
                
                # Add pulsing animation for ready vaults
                if ready == "🟢" and self.frame % 10 < 5:
                    ready = "🟢 ←"
                
                table.add_row(name, status, cooldown_str, ready)
        
        return Panel(table, title="🎯 Target Vaults", border_style="blue")
    
    def get_recent_runs_panel(self) -> Panel:
        """Recent harvest attempts"""
        table = Table(expand=True)
        table.add_column("Time", style="dim", width=8)
        table.add_column("Vault", style="cyan")
        table.add_column("Profit", justify="right")
        table.add_column("", width=2)
        
        with self.db.get_conn() as conn:
            results = conn.execute('''
                SELECT * FROM runs
                ORDER BY timestamp DESC
                LIMIT 8
            ''').fetchall()
            
            for row in results:
                run_time = datetime.fromtimestamp(row['timestamp'])
                time_str = run_time.strftime('%H:%M')
                
                vault = row['target'][:12]
                
                if row['net_usd']:
                    if row['net_usd'] > 0:
                        profit = f"[green]+${row['net_usd']:.3f}[/green]"
                        icon = "✓"
                    else:
                        profit = f"[red]-${abs(row['net_usd']):.3f}[/red]"
                        icon = "✗"
                else:
                    profit = "[dim]--[/dim]"
                    icon = "⋯"
                
                table.add_row(time_str, vault, profit, icon)
        
        return Panel(table, title="📜 Recent Harvests", border_style="yellow")
    
    def get_gas_panel(self) -> Panel:
        """Gas price monitor with trend indicator"""
        try:
            # Get gas price
            for chain_name, chain_config in self.config['chains'].items():
                w3 = self.rpc_manager.get_web3(chain_name, chain_config)
                base_fee_gwei = get_base_fee_gwei(w3)
                
                # Simulate trend (replace with real tracking)
                if self.frame % 60 < 30:
                    trend = "📈"
                else:
                    trend = "📉"
                
                gas_text = Text()
                gas_text.append(f"⛽ Gas Price {trend}\n", style="bold")
                gas_text.append(f"{base_fee_gwei:.2f} gwei\n", style="cyan")
                gas_text.append(f"\n", style="")
                
                # Estimate harvest cost
                gas_limit = 500000
                gas_cost_eth = (base_fee_gwei * gas_limit) / 1e9
                gas_cost_usd = gas_cost_eth * 2500
                
                gas_text.append(f"Est. harvest cost:\n", style="dim")
                gas_text.append(f"${gas_cost_usd:.2f}", style="yellow")
                
                return Panel(gas_text, title="⛽ Gas Monitor", border_style="magenta")
        except:
            return Panel("[dim]Gas data unavailable[/dim]", title="⛽ Gas Monitor", border_style="magenta")
    
    def get_footer(self) -> Panel:
        """Footer with help text"""
        help_text = Text()
        help_text.append("Commands: ", style="dim")
        help_text.append("[Q]uit", style="cyan")
        help_text.append(" | ", style="dim")
        help_text.append("[R]efresh", style="cyan")
        help_text.append(" | ", style="dim")
        help_text.append("[P]ause", style="cyan")
        help_text.append(" | ", style="dim")
        help_text.append("[L]ogs", style="cyan")
        
        return Panel(
            Align.center(help_text),
            style="dim",
            border_style="dim"
        )
    
    def get_block_number(self) -> str:
        """Get current block number"""
        try:
            for chain_name, chain_config in self.config['chains'].items():
                w3 = self.rpc_manager.get_web3(chain_name, chain_config)
                return f"{w3.eth.block_number:,}"
        except:
            return "---"
    
    def add_activity(self, message: str):
        """Add activity to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.activities.append(f"[{timestamp}] {message}")
        if len(self.activities) > self.max_activities:
            self.activities.pop(0)
    
    def simulate_events(self):
        """Simulate harvest events (replace with real monitoring)"""
        if time.time() - self.last_event_time > random.randint(10, 30):
            events = [
                "✅ Harvested Beefy_MIM_USDC (+$0.042)",
                "📊 Cooldown expired for tBTC_WBTC",
                "⛽ Gas price dropped to 0.08 gwei",
                "🔄 Checking USDC_USDT_GHO vault",
                "💰 Profit threshold met for harvest",
                "⏰ 2 vaults ready in next hour",
            ]
            self.add_activity(random.choice(events))
            self.last_event_time = time.time()
    
    def update_display(self) -> Layout:
        """Update all panels"""
        self.frame += 1
        
        # Simulate events periodically
        self.simulate_events()
        
        self.layout["header"].update(self.get_header())
        self.layout["activity"].update(self.get_activity_panel())
        self.layout["stats"].update(self.get_stats_panel())
        self.layout["targets"].update(self.get_targets_panel())
        self.layout["recent_runs"].update(self.get_recent_runs_panel())
        self.layout["gas_info"].update(self.get_gas_panel())
        self.layout["footer"].update(self.get_footer())
        
        return self.layout
    
    def run(self):
        """Run the dashboard"""
        try:
            with Live(self.update_display(), refresh_per_second=10, console=console) as live:
                while self.running:
                    time.sleep(0.1)  # 10 FPS for smooth animations
                    live.update(self.update_display())
        except KeyboardInterrupt:
            console.print("\n[yellow]Dashboard stopped[/yellow]")

def main():
    """Run the animated dashboard"""
    dashboard = AnimatedDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()