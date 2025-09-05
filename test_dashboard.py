#!/usr/bin/env python3
"""
Test dashboard with liquidation panel
"""

from janitor.dashboard import JanitorDashboard
import time

def test_dashboard():
    """Test the dashboard display"""
    dashboard = JanitorDashboard()
    
    # Test each panel individually
    print("Testing Dashboard Panels:")
    print("="*60)
    
    try:
        print("\n1. Header Panel:")
        header = dashboard.get_header()
        print("   ✅ Header panel created")
    except Exception as e:
        print(f"   ❌ Header error: {e}")
    
    try:
        print("\n2. Stats Panel:")
        stats = dashboard.get_stats_panel()
        print("   ✅ Stats panel created")
    except Exception as e:
        print(f"   ❌ Stats error: {e}")
    
    try:
        print("\n3. Liquidation Panel:")
        liquidation = dashboard.get_liquidation_panel()
        print("   ✅ Liquidation panel created")
        print(f"   Title: {liquidation.title}")
    except Exception as e:
        print(f"   ❌ Liquidation error: {e}")
    
    try:
        print("\n4. Targets Panel:")
        targets = dashboard.get_targets_panel()
        print("   ✅ Targets panel created")
    except Exception as e:
        print(f"   ❌ Targets error: {e}")
    
    try:
        print("\n5. Recent Runs Panel:")
        recent = dashboard.get_recent_runs_panel()
        print("   ✅ Recent runs panel created")
    except Exception as e:
        print(f"   ❌ Recent runs error: {e}")
    
    try:
        print("\n6. Gas Panel:")
        gas = dashboard.get_gas_panel()
        print("   ✅ Gas panel created")
    except Exception as e:
        print(f"   ❌ Gas error: {e}")
    
    try:
        print("\n7. Footer Panel:")
        footer = dashboard.get_footer()
        print("   ✅ Footer panel created")
    except Exception as e:
        print(f"   ❌ Footer error: {e}")
    
    print("\n" + "="*60)
    print("Testing Full Dashboard Update:")
    try:
        layout = dashboard.update_display()
        print("✅ Dashboard update successful!")
        print(f"   Layout sections: {list(layout._children.keys())}")
        
        # Check if liquidations panel is in the layout
        if hasattr(layout, '_children'):
            left_panel = layout['left']
            if hasattr(left_panel, '_children'):
                print(f"   Left panel sections: {list(left_panel._children.keys())}")
                if 'liquidations' in left_panel._children:
                    print("   ✅ Liquidations panel is in the layout!")
                else:
                    print("   ❌ Liquidations panel NOT found in layout")
    except Exception as e:
        print(f"❌ Dashboard update error: {e}")
    
    print("\n" + "="*60)
    print("Dashboard test complete!")

if __name__ == "__main__":
    test_dashboard()