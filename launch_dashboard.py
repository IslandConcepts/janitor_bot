#!/usr/bin/env python3
"""
Launch the Janitor Bot Dashboard
Shows real-time status of Beefy vault harvests
"""

import os
import sys
from pathlib import Path

# Add janitor module to path
sys.path.insert(0, str(Path(__file__).parent))

# Import and run dashboard
from janitor.dashboard import JanitorDashboard

def main():
    print("🚀 Launching Janitor Bot Dashboard...")
    print("=" * 60)
    print("📊 Monitoring Beefy Vaults on Arbitrum")
    print("💰 Tracking harvest opportunities and P&L")
    print("=" * 60)
    print("\nPress Ctrl+C to exit\n")
    
    try:
        dashboard = JanitorDashboard()
        dashboard.run()
    except KeyboardInterrupt:
        print("\n\n✅ Dashboard stopped gracefully")
    except Exception as e:
        print(f"\n❌ Dashboard error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()