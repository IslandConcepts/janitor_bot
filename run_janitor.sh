#!/bin/bash

# Janitor Bot Runner Script
# Harvesting Beefy Vaults on Arbitrum

echo "🧹 JANITOR BOT - Beefy Vault Harvester"
echo "======================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found!"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
fi

# Show options
echo "Select mode:"
echo "  1) 📊 Dashboard (monitor only)"
echo "  2) 🧪 Dry Run (test mode)"
echo "  3) 🚀 LIVE (execute harvests)"
echo "  4) 📈 Check harvest status"
echo "  5) 🛑 Exit"
echo ""

read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo ""
        echo "🖥️  Starting Dashboard..."
        echo "Press Ctrl+C to exit"
        echo ""
        python3 launch_dashboard.py
        ;;
    2)
        echo ""
        echo "🧪 Starting Dry Run Mode..."
        echo "No transactions will be executed"
        echo "Press Ctrl+C to stop"
        echo ""
        python3 -m janitor.janitor --dry-run
        ;;
    3)
        echo ""
        echo "⚠️  WARNING: LIVE MODE - Real transactions!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            echo ""
            echo "🚀 Starting LIVE Harvesting..."
            echo "Press Ctrl+C to stop"
            echo ""
            python3 -m janitor.janitor
        else
            echo "Cancelled."
        fi
        ;;
    4)
        echo ""
        echo "📈 Checking Harvest Status..."
        echo ""
        python3 test_janitor.py
        ;;
    5)
        echo "Goodbye! 👋"
        exit 0
        ;;
    *)
        echo "Invalid choice!"
        exit 1
        ;;
esac