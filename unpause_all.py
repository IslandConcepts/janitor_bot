#!/usr/bin/env python3
"""
Unpause all targets - useful for testing
"""

from janitor.storage import Database
import sqlite3

db = Database("data/janitor.db")

print("🔓 Unpausing all targets...")

# Clear all pauses
with db.get_conn() as conn:
    # Check current paused targets
    paused = conn.execute('''
        SELECT target, paused_until FROM state 
        WHERE paused_until > 0
    ''').fetchall()
    
    if paused:
        print(f"Found {len(paused)} paused targets:")
        for row in paused:
            print(f"  - {row['target']}")
        
        # Clear all pauses
        conn.execute('UPDATE state SET paused_until = NULL')
        print("✅ All targets unpaused!")
    else:
        print("No paused targets found")
    
    # Also reset failure counts
    conn.execute('UPDATE state SET consecutive_failures = 0')
    print("✅ Reset all failure counts")

print("\n📊 Current state:")
with db.get_conn() as conn:
    states = conn.execute('SELECT * FROM state').fetchall()
    for state in states:
        print(f"  {state['target']}: failures={state['consecutive_failures']}, paused={state['paused_until']}")

print("\n✅ Ready to run!")