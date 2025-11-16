#!/bin/bash

# Easy start script - auto-activates venv if it exists

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}Telegram Music Bot Starter${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check if venv exists
if [ -d "venv" ]; then
    echo -e "${GREEN}✓ Activating virtual environment...${NC}"
    source venv/bin/activate
else
    echo -e "${YELLOW}⚠ Virtual environment not found${NC}"
    echo "Run: ./setup_venv.sh first"
    echo ""
    echo "Or continue without venv? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# Check if Lavalink is running
echo ""
echo -e "${BLUE}Checking Lavalink...${NC}"
if curl -s http://localhost:2333/version > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Lavalink is running${NC}"
else
    echo -e "${RED}✗ Lavalink is not running${NC}"
    echo ""
    echo "Start Lavalink first!"
    echo "Open new terminal and run:"
    echo -e "${BLUE}  cd lavalink${NC}"
    echo -e "${BLUE}  java -jar Lavalink.jar${NC}"
    echo ""
    echo "Continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 0
    fi
fi

# Check if config exists
if [ ! -f "config.py" ]; then
    echo -e "${RED}✗ config.py not found!${NC}"
    echo ""
    echo "Create config.py with:"
    echo "  API_ID = \"your_api_id\""
    echo "  API_HASH = \"your_api_hash\""
    echo "  BOT_TOKEN = \"your_token\"  # For bot mode"
    echo ""
    exit 1
fi

# Start bot
echo ""
echo -e "${GREEN}Starting music bot...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

python3 music_bot.py
