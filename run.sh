#!/bin/bash

# Janitor Bot Runner Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env with your configuration before running.${NC}"
    exit 1
fi

# Create data directory if it doesn't exist
mkdir -p data

# Parse command
case "$1" in
    start)
        echo -e "${GREEN}Starting janitor bot...${NC}"
        python -m janitor.janitor
        ;;
    
    docker)
        echo -e "${GREEN}Starting janitor bot with Docker...${NC}"
        docker compose up -d
        echo -e "${GREEN}Janitor bot started. Check logs with: docker compose logs -f${NC}"
        ;;
    
    stop)
        echo -e "${YELLOW}Stopping janitor bot...${NC}"
        docker compose down
        ;;
    
    logs)
        docker compose logs -f janitor
        ;;
    
    metrics)
        echo -e "${GREEN}Starting metrics server...${NC}"
        python -m janitor.metrics
        ;;
    
    pnl)
        echo -e "${GREEN}Fetching P&L report...${NC}"
        curl -s http://localhost:8000/metrics | python -m json.tool
        ;;
    
    install)
        echo -e "${GREEN}Installing dependencies...${NC}"
        pip install -r requirements.txt
        echo -e "${GREEN}Dependencies installed!${NC}"
        ;;
    
    test)
        echo -e "${GREEN}Running in test mode...${NC}"
        ENV=test LOG_LEVEL=DEBUG python -m janitor.janitor
        ;;
    
    dashboard)
        echo -e "${GREEN}Starting terminal dashboard...${NC}"
        python -m janitor.dashboard
        ;;
    
    log-viewer)
        echo -e "${GREEN}Starting log viewer...${NC}"
        shift
        python -m janitor.log_viewer "$@"
        ;;
    
    log-tail)
        echo -e "${GREEN}Tailing logs...${NC}"
        python -m janitor.log_viewer --tail --follow
        ;;
    
    *)
        echo "Usage: $0 {start|docker|stop|logs|metrics|pnl|dashboard|log-viewer|log-tail|install|test}"
        echo ""
        echo "  start      - Run janitor bot locally"
        echo "  docker     - Run janitor bot with Docker"
        echo "  stop       - Stop Docker containers"
        echo "  logs       - View janitor logs"
        echo "  metrics    - Start metrics server"
        echo "  pnl        - View P&L report"
        echo "  dashboard  - Launch terminal dashboard"
        echo "  log-viewer - Analyze logs (use --help for options)"
        echo "  log-tail   - Tail logs in real-time"
        echo "  install    - Install Python dependencies"
        echo "  test       - Run in test mode with debug logging"
        exit 1
        ;;
esac