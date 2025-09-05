#!/usr/bin/env python3
"""
Quick launcher for the animated dashboard
"""

if __name__ == "__main__":
    try:
        from janitor.dashboard_v2 import AnimatedDashboard
        
        print("🚀 Launching Janitor Bot Animated Dashboard...")
        print("=" * 60)
        print("📊 Live monitoring of Beefy vault harvests")
        print("⚡ Real-time activity feed and animations")
        print("=" * 60)
        print("\nPress Ctrl+C to exit\n")
        
        dashboard = AnimatedDashboard()
        dashboard.run()
        
    except KeyboardInterrupt:
        print("\n\n✅ Dashboard stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()